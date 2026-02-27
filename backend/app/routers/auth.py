from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.auth import create_token

router = APIRouter()


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """Return all demo users for the UI dropdown (no secrets exposed)."""
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return {
        "users": [
            {
                "username": u.username,
                "display_name": u.display_name,
                "role": u.role,
                "assigned_patients": u.assigned_patients or [],
            }
            for u in users
        ]
    }


@router.post("/token")
async def get_token(body: dict, db: AsyncSession = Depends(get_db)):
    """
    Exchange a username for a JWT token. No password — demo lab only.
    Body: {"username": "dr.smith"}
    """
    username = (body.get("username") or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    token = create_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "assigned_patients": user.assigned_patients or [],
    }
