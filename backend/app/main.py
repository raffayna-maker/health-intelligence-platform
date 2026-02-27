from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from app.database import engine, Base, async_session
from app.routers import dashboard, patients, documents, analytics, assistant, agents, reports, security
from app.routers import auth as auth_router


async def seed_demo_users():
    """Create the 3 demo users if they don't exist. Idempotent."""
    from app.models.user import User
    pt_001_to_050 = [f"PT-{str(i).zfill(3)}" for i in range(1, 51)]
    pt_001_to_010 = [f"PT-{str(i).zfill(3)}" for i in range(1, 11)]

    demo_users = [
        {"username": "admin",       "display_name": "Admin",       "role": "admin",  "assigned_patients": []},
        {"username": "dr.smith",    "display_name": "Dr. Smith",   "role": "doctor", "assigned_patients": pt_001_to_050},
        {"username": "nurse.jones", "display_name": "Nurse Jones", "role": "nurse",  "assigned_patients": pt_001_to_010},
    ]

    async with async_session() as session:
        for u in demo_users:
            existing = await session.scalar(select(User).where(User.username == u["username"]))
            if not existing:
                session.add(User(**u))
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables then seed demo users
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_demo_users()
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Healthcare Intelligence Platform",
    description="Enterprise AI application with autonomous agents and dual security",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Middleware to add no-cache headers to prevent browser caching."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"
        response.headers["Expires"] = "0"
        response.headers["Pragma"] = "no-cache"
        return response


app.add_middleware(NoCacheMiddleware)

app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["Assistant"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(security.router, prefix="/api/security", tags=["Security"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "healthcare-ai-platform"}
