from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Ticket, TicketEvent, User
from app.schemas import (
    PaginatedTickets,
    TicketAssign,
    TicketCreate,
    TicketDetail,
    TicketOut,
    TicketPriority,
    TicketStatus,
    TicketStatusUpdate,
    TicketUpdate,
)


router = APIRouter(prefix="/tickets", tags=["tickets"])

ALLOWED_TRANSITIONS = {
    ("assigned", "in_progress"),
    ("in_progress", "resolved"),
    ("resolved", "closed"),
}


def _add_event(
    db: Session,
    ticket: Ticket,
    actor_id: int,
    event_type: str,
    from_status: str | None,
    to_status: str,
) -> None:
    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            actor_id=actor_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
        )
    )


def _get_ticket(db: Session, ticket_id: int) -> Ticket:
    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(selectinload(Ticket.events))
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def _can_view(user: User, ticket: Ticket) -> bool:
    if user.role == "admin":
        return True
    if user.role == "employee":
        return ticket.created_by == user.id
    return ticket.assignee_id == user.id


def _get_visible_ticket(db: Session, user: User, ticket_id: int) -> Ticket:
    ticket = _get_ticket(db, ticket_id)
    if not _can_view(user, ticket):
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def _visibility_conditions(user: User) -> list:
    if user.role == "admin":
        return []
    if user.role == "employee":
        return [Ticket.created_by == user.id]
    return [Ticket.assignee_id == user.id]


@router.post("", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetail:
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        priority=payload.priority.value,
        status=TicketStatus.open.value,
        created_by=current_user.id,
    )
    db.add(ticket)
    db.flush()
    _add_event(
        db,
        ticket,
        current_user.id,
        event_type="created",
        from_status=None,
        to_status=TicketStatus.open.value,
    )
    db.commit()
    return TicketDetail.model_validate(_get_ticket(db, ticket.id))


@router.get("", response_model=PaginatedTickets)
def list_tickets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ticket_status: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    assignee_id: int | None = Query(default=None, gt=0),
    keyword: str | None = Query(default=None, max_length=64),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedTickets:
    conditions = _visibility_conditions(current_user)
    if ticket_status is not None:
        conditions.append(Ticket.status == ticket_status.value)
    if priority is not None:
        conditions.append(Ticket.priority == priority.value)
    if assignee_id is not None:
        conditions.append(Ticket.assignee_id == assignee_id)
    if keyword:
        pattern = f"%{keyword}%"
        conditions.append(
            or_(Ticket.title.ilike(pattern), Ticket.description.ilike(pattern))
        )

    total = db.scalar(select(func.count(Ticket.id)).where(*conditions)) or 0
    tickets = db.scalars(
        select(Ticket)
        .where(*conditions)
        .order_by(Ticket.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PaginatedTickets(
        items=[TicketOut.model_validate(ticket) for ticket in tickets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetail:
    return TicketDetail.model_validate(
        _get_visible_ticket(db, current_user, ticket_id)
    )


@router.patch("/{ticket_id}", response_model=TicketDetail)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetail:
    ticket = _get_visible_ticket(db, current_user, ticket_id)
    if current_user.role != "admin":
        if ticket.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        if ticket.status != TicketStatus.open.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only open tickets can be edited by the creator",
            )

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field == "priority" and value is not None:
            value = value.value
        setattr(ticket, field, value)
    db.commit()
    return TicketDetail.model_validate(_get_ticket(db, ticket.id))


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Response:
    ticket = _get_ticket(db, ticket_id)
    db.delete(ticket)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{ticket_id}/assign", response_model=TicketDetail)
def assign_ticket(
    ticket_id: int,
    payload: TicketAssign,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> TicketDetail:
    ticket = _get_ticket(db, ticket_id)
    technician = db.get(User, payload.assignee_id)
    if technician is None:
        raise HTTPException(status_code=404, detail="Assignee not found")
    if technician.role != "technician" or not technician.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assignee must be an active technician",
        )
    if ticket.status not in {TicketStatus.open.value, TicketStatus.assigned.value}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only open or assigned tickets can be assigned",
        )
    if ticket.assignee_id == technician.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket is already assigned to this technician",
        )

    previous_status = ticket.status
    event_type = (
        "assigned" if previous_status == TicketStatus.open.value else "reassigned"
    )
    ticket.assignee_id = technician.id
    ticket.status = TicketStatus.assigned.value
    _add_event(
        db,
        ticket,
        current_user.id,
        event_type=event_type,
        from_status=previous_status,
        to_status=TicketStatus.assigned.value,
    )
    db.commit()
    return TicketDetail.model_validate(_get_ticket(db, ticket.id))


@router.patch("/{ticket_id}/status", response_model=TicketDetail)
def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetail:
    ticket = _get_visible_ticket(db, current_user, ticket_id)
    target = payload.status.value
    current = ticket.status

    if target == current:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket already has the requested status",
        )
    if target == TicketStatus.assigned.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Use the assignment endpoint to assign a ticket",
        )
    if (current, target) not in ALLOWED_TRANSITIONS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid status transition: {current} -> {target}",
        )

    if target in {
        TicketStatus.in_progress.value,
        TicketStatus.resolved.value,
    } and current_user.role != "admin":
        if ticket.assignee_id != current_user.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    if target == TicketStatus.closed.value and current_user.role != "admin":
        if ticket.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    ticket.status = target
    _add_event(
        db,
        ticket,
        current_user.id,
        event_type="status_changed",
        from_status=current,
        to_status=target,
    )
    db.commit()
    return TicketDetail.model_validate(_get_ticket(db, ticket.id))
