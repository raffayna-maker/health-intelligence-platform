import asyncio
import time
import httpx
from typing import Optional, Dict, Any
from app.config import get_settings

settings = get_settings()


class HiddenLayerClient:
    """Client for Hidden Layer AIDR Prompt Analyzer (SaaS)."""

    def __init__(self):
        self.client_id = settings.hiddenlayer_client_id
        self.client_secret = settings.hiddenlayer_client_secret
        self._token: Optional[str] = None
        self._token_expiry: float = 0

    async def _get_token(self) -> str:
        """Get OAuth2 token from Hidden Layer."""
        if self._token and time.time() < self._token_expiry:
            return self._token

        auth_url = "https://auth.hiddenlayer.ai/oauth2/token?grant_type=client_credentials"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                auth_url,
                auth=(self.client_id, self.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["access_token"]
            self._token_expiry = time.time() + 3240
            return self._token

    async def scan(self, content: str, scan_type: str = "input") -> Dict[str, Any]:
        """Scan content with Hidden Layer Prompt Analyzer SaaS."""
        start = time.time()
        
        try:
            token = await self._get_token()
            api_url = "https://api.hiddenlayer.ai/api/v1/submit/prompt-analyzer"
            
            payload = {"model": "healthcare-platform"}
            if scan_type == "input":
                payload["prompt"] = content
            else:
                payload["output"] = content
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Requester-Id": "healthcare-platform",
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                elapsed = int((time.time() - start) * 1000)
                
                if response.status_code != 200:
                    return {
                        "verdict": "error",
                        "reason": f"Hidden Layer API error: {response.status_code}",
                        "scan_time_ms": elapsed,
                        "details": {},
                    }
                
                data = response.json()
                blocked = data.get("verdict", False)
                
                reason = None
                if blocked:
                    categories = data.get("categories", {})
                    detected = []
                    if categories.get("prompt_injection"):
                        detected.append("prompt injection")
                    if categories.get("unsafe_input"):
                        detected.append("unsafe input")
                    if categories.get("input_pii"):
                        detected.append("PII")
                    if categories.get("output_pii"):
                        detected.append("output PII")
                    reason = ", ".join(detected) if detected else "security violation"
                
                return {
                    "verdict": "block" if blocked else "pass",
                    "reason": reason,
                    "scan_time_ms": elapsed,
                    "details": data,
                }
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return {
                "verdict": "error",
                "reason": f"Hidden Layer error: {str(e)}",
                "scan_time_ms": elapsed,
                "details": {},
            }


class AIMClient:
    """Client for AIM Security via LiteLLM Proxy with proper virtual key."""

    def __init__(self):
        self.litellm_url = settings.litellm_base_url or "http://litellm:4000"
        self.litellm_key = settings.litellm_virtual_key

    async def scan(self, content: str, scan_type: str = "input") -> Dict[str, Any]:
        """Scan content with AIM via LiteLLM proxy using generated virtual key."""
        start = time.time()
        
        try:
            payload = {
                "model": "ollama-llama",
                "messages": [{"role": "user", "content": content}],
                "max_tokens": 1,
                "stream": False,
            }
            
            headers = {
                "Authorization": f"Bearer {self.litellm_key}",
                "Content-Type": "application/json",
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.litellm_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                
                elapsed = int((time.time() - start) * 1000)
                
                if response.status_code == 400:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message", "")
                        return {
                            "verdict": "block",
                            "reason": error_message,
                            "scan_time_ms": elapsed,
                            "details": error_data,
                        }
                    except:
                        return {
                            "verdict": "block",
                            "reason": "Content blocked by AIM",
                            "scan_time_ms": elapsed,
                            "details": {},
                        }
                elif response.status_code == 200:
                    return {
                        "verdict": "pass",
                        "reason": None,
                        "scan_time_ms": elapsed,
                        "details": {},
                    }
                else:
                    return {
                        "verdict": "error",
                        "reason": f"AIM API error: {response.status_code}",
                        "scan_time_ms": elapsed,
                        "details": {},
                    }
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return {
                "verdict": "error",
                "reason": f"AIM error: {str(e)}",
                "scan_time_ms": elapsed,
                "details": {},
            }


async def dual_security_scan(
    content: str,
    scan_type: str = "input",
    feature_name: str = "unknown",
) -> Dict[str, Any]:
    """Perform dual security scan with both Hidden Layer and AIM."""
    hl_client = HiddenLayerClient()
    aim_client = AIMClient()
    
    hl_task = asyncio.create_task(hl_client.scan(content, scan_type))
    aim_task = asyncio.create_task(aim_client.scan(content, scan_type))
    
    hl_result, aim_result = await asyncio.gather(hl_task, aim_task)
    
    hl_blocked = hl_result.get("verdict") == "block"
    aim_blocked = aim_result.get("verdict") == "block"
    
    blocked_by = []
    if hl_blocked:
        blocked_by.append("Hidden Layer")
    if aim_blocked:
        blocked_by.append("AIM")
    
    return {
        "blocked": bool(blocked_by),
        "blocked_by": blocked_by,
        "hidden_layer_result": hl_result,
        "aim_result": aim_result,
        "scan_type": scan_type,
        "feature_name": feature_name,
    }


async def log_security_scan(
    db,
    scan_result: Dict[str, Any],
    content: str,
    agent_run_id: Optional[int] = None,
):
    """
    Log security scan results to database.
    
    Args:
        db: Database session
        scan_result: Result from dual_security_scan()
        content: The content that was scanned
        agent_run_id: Optional agent run ID
    """
    from app.models.security_log import SecurityLog
    
    hl_result = scan_result.get("hidden_layer_result", {})
    aim_result = scan_result.get("aim_result", {})
    
    log = SecurityLog(
        feature=scan_result.get("feature_name", "unknown"),
        scan_type=scan_result.get("scan_type", "input"),
        content_preview=content[:200] if content else "",
        hl_verdict=hl_result.get("verdict"),
        hl_reason=hl_result.get("reason"),
        hl_scan_time_ms=hl_result.get("scan_time_ms"),
        aim_verdict=aim_result.get("verdict"),
        aim_reason=aim_result.get("reason"),
        aim_scan_time_ms=aim_result.get("scan_time_ms"),
        final_verdict="block" if scan_result.get("blocked") else "pass",
        agent_run_id=agent_run_id,
    )
    
    db.add(log)
    await db.commit()
    return log
