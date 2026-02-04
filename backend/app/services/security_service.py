import asyncio
import time
import httpx
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models.security_log import SecurityLog
from app.schemas.security import DualScanResult

settings = get_settings()


class HiddenLayerClient:
    """Client for Hidden Layer AI security scanning API."""

    def __init__(self):
        self.api_url = settings.hiddenlayer_api_url
        self.client_id = settings.hiddenlayer_client_id
        self.client_secret = settings.hiddenlayer_client_secret
        self._token: Optional[str] = None
        self._token_expiry: float = 0

    async def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.api_url}/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["access_token"]
            self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
            return self._token

    async def scan(self, content: str) -> dict:
        start = time.time()
        try:
            token = await self._get_token()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/v2/submit/text",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"text": content},
                )
                response.raise_for_status()
                data = response.json()
                elapsed = int((time.time() - start) * 1000)
                is_malicious = data.get("is_malicious", False)
                return {
                    "verdict": "block" if is_malicious else "pass",
                    "reason": data.get("risk_category", None) if is_malicious else None,
                    "scan_time_ms": elapsed,
                    "details": data,
                }
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return {
                "verdict": "error",
                "reason": str(e),
                "scan_time_ms": elapsed,
                "details": {},
            }


class AIMClient:
    """Client for AIM security scanning API."""

    def __init__(self):
        self.api_url = settings.aim_api_url
        self.api_key = settings.aim_api_key

    async def scan(self, content: str) -> dict:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/v1/safety/scan",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"content": content, "scan_type": "full"},
                )
                response.raise_for_status()
                data = response.json()
                elapsed = int((time.time() - start) * 1000)
                is_blocked = data.get("blocked", False)
                return {
                    "verdict": "block" if is_blocked else "pass",
                    "reason": data.get("reason", None) if is_blocked else None,
                    "scan_time_ms": elapsed,
                    "details": data,
                }
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return {
                "verdict": "error",
                "reason": str(e),
                "scan_time_ms": elapsed,
                "details": {},
            }


hl_client = HiddenLayerClient()
aim_client = AIMClient()


async def dual_security_scan(
    content: str,
    scan_type: str,
    feature: str,
    db: Optional[AsyncSession] = None,
    agent_run_id: Optional[int] = None,
) -> DualScanResult:
    """
    Run both Hidden Layer and AIM scans in parallel.
    Either tool can independently block the request.
    """
    hl_result, aim_result = await asyncio.gather(
        hl_client.scan(content),
        aim_client.scan(content),
        return_exceptions=True,
    )

    if isinstance(hl_result, Exception):
        hl_result = {"verdict": "error", "reason": str(hl_result), "scan_time_ms": 0}
    if isinstance(aim_result, Exception):
        aim_result = {"verdict": "error", "reason": str(aim_result), "scan_time_ms": 0}

    hl_blocked = hl_result["verdict"] == "block"
    aim_blocked = aim_result["verdict"] == "block"
    final_blocked = hl_blocked or aim_blocked
    final_verdict = "block" if final_blocked else "pass"

    # Log to database if session provided
    if db:
        log = SecurityLog(
            feature=feature,
            scan_type=scan_type,
            content_preview=content[:200],
            hl_verdict=hl_result["verdict"],
            hl_reason=hl_result.get("reason"),
            hl_scan_time_ms=hl_result["scan_time_ms"],
            aim_verdict=aim_result["verdict"],
            aim_reason=aim_result.get("reason"),
            aim_scan_time_ms=aim_result["scan_time_ms"],
            final_verdict=final_verdict,
            agent_run_id=agent_run_id,
        )
        db.add(log)
        await db.flush()

    return DualScanResult(
        hl_verdict=hl_result["verdict"],
        hl_reason=hl_result.get("reason"),
        hl_scan_time_ms=hl_result["scan_time_ms"],
        aim_verdict=aim_result["verdict"],
        aim_reason=aim_result.get("reason"),
        aim_scan_time_ms=aim_result["scan_time_ms"],
        final_verdict=final_verdict,
        blocked=final_blocked,
    )
