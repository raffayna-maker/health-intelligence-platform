"""
Auth module: JWT creation/validation and the get_current_user FastAPI dependency.

Design: auth is OPTIONAL. If no Authorization header is present (or the token is
invalid), the dependency returns ANONYMOUS_ADMIN — a synthetic admin principal that
gives full access. This preserves backward compatibility for all existing curl
commands and PromptFoo red team scans that don't send auth headers.
"""

import time
from dataclasses import dataclass, field
from typing import Optional
from jose import jwt, JWTError
from fastapi import Request
from app.config import get_settings

ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 86400  # 24 hours


@dataclass
class UserPrincipal:
    """Resolved identity attached to each request."""
    username: str
    display_name: str
    role: str                     # "admin" | "doctor" | "nurse"
    assigned_patients: list = field(default_factory=list)
    is_anonymous: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def can_write(self) -> bool:
        return self.role in ("admin", "doctor")

    @property
    def can_see_ssn(self) -> bool:
        return self.role in ("admin", "doctor")

    def has_access_to_patient(self, patient_id: str) -> bool:
        if self.is_admin:
            return True
        return patient_id in self.assigned_patients

    def get_allowed_patient_ids(self) -> Optional[list]:
        """Returns None for admin (unrestricted), list for restricted roles."""
        if self.is_admin:
            return None
        return self.assigned_patients


# The anonymous principal — returned when no Authorization header is present.
# Always admin so existing curl/PromptFoo traffic is completely unaffected.
ANONYMOUS_ADMIN = UserPrincipal(
    username="anonymous",
    display_name="Admin (Anonymous)",
    role="admin",
    assigned_patients=[],
    is_anonymous=True,
)


def create_token(user) -> str:
    """Create a signed JWT for the given User model instance."""
    settings = get_settings()
    payload = {
        "sub": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "assigned_patients": user.assigned_patients or [],
        "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[UserPrincipal]:
    """Decode and validate a JWT. Returns None if invalid/expired."""
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        return UserPrincipal(
            username=payload["sub"],
            display_name=payload.get("display_name", payload["sub"]),
            role=payload.get("role", "admin"),
            assigned_patients=payload.get("assigned_patients", []),
        )
    except JWTError:
        return None


async def get_current_user(request: Request) -> UserPrincipal:
    """
    FastAPI dependency. Extracts JWT from Authorization header.
    Returns ANONYMOUS_ADMIN if header is absent or token is invalid —
    never raises 401 so unauthenticated requests still work as admin.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return ANONYMOUS_ADMIN
    token = auth_header[7:]
    principal = decode_token(token)
    return principal if principal else ANONYMOUS_ADMIN
