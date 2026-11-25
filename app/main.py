from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routers import auth, tickets, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Service Desk API",
    version="1.0.0",
    description="A small IT service desk API used as a controllable test target.",
    lifespan=lifespan,
)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tickets.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
