from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import User
from app.schemas import (
    PaginatedUsers,
    UserActiveUpdate,
    UserCreate,
    UserOut,
    UserRole,
    UserRoleUpdate,
)
from app.security import hash_password


router = APIRouter(prefix="/users", tags=["users"])


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> UserOut:
    user = User(
        username=payload.username,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role=payload.role.value,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        ) from exc
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("", response_model=PaginatedUsers)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: UserRole | None = None,
    active: bool | None = None,
    keyword: str | None = Query(default=None, max_length=64),
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> PaginatedUsers:
    conditions = []
    if role is not None:
        conditions.append(User.role == role.value)
    if active is not None:
        conditions.append(User.is_active == active)
    if keyword:
        pattern = f"%{keyword}%"
        conditions.append(
            or_(User.username.ilike(pattern), User.email.ilike(pattern))
        )

    total = db.scalar(select(func.count(User.id)).where(*conditions)) or 0
    users = db.scalars(
        select(User)
        .where(*conditions)
        .order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PaginatedUsers(
        items=[UserOut.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(_get_user(db, user_id))


@router.patch("/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> UserOut:
    user = _get_user(db, user_id)
    if (
        current_user.id == user.id
        and payload.role != UserRole.admin
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin cannot demote the current account",
        )
    user.role = payload.role.value
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/{user_id}/active", response_model=UserOut)
def update_user_active(
    user_id: int,
    payload: UserActiveUpdate,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> UserOut:
    user = _get_user(db, user_id)
    if current_user.id == user.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin cannot deactivate the current account",
        )
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
