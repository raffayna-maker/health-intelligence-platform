import asyncio
import time
import httpx
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from app.config import get_settings

settings = get_settings()


class SecurityTool(ABC):
    """Base class for all security scanning tools."""

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Short identifier for results dicts and DB, e.g. 'hidden_layer'."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for UI badges, e.g. 'Hidden Layer'."""
        ...

    @abstractmethod
    async def scan(self, content: str, scan_type: str = "input", prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Scan content and return result dict.
        verdict: "pass", "block", "detected", "error", or "skip"
        """
        ...


class HiddenLayerClient(SecurityTool):
    """Client for Hidden Layer AIDR Prompt Analyzer (SaaS)."""

    tool_name = "hidden_layer"
    display_name = "Hidden Layer"

    def __init__(self):
        self.client_id = settings.hiddenlayer_client_id
        self.client_secret = settings.hiddenlayer_client_secret
        self.api_url = settings.hiddenlayer_api_url
        self.project_id = settings.hiddenlayer_project_id
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

    async def scan(self, content: str, scan_type: str = "input", prompt: Optional[str] = None) -> Dict[str, Any]:
        """Scan content with Hidden Layer Prompt Analyzer SaaS."""
        start = time.time()

        try:
            token = await self._get_token()
            api_url = f"{self.api_url}/api/v1/submit/prompt-analyzer"

            payload = {"model": "healthcare-platform"}
            if scan_type == "input":
                payload["prompt"] = content
            else:
                if not prompt:
                    elapsed = int((time.time() - start) * 1000)
                    return {
                        "verdict": "error",
                        "reason": "Output scan requires prompt parameter",
                        "scan_time_ms": elapsed,
                        "details": {},
                    }
                payload["prompt"] = prompt
                payload["output"] = content

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Requester-Id": "healthcare-platform",
            }
            if self.project_id:
                headers["HL-Project-ID"] = self.project_id

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
                has_detection = data.get("verdict", False)

                reason = None
                verdict = "pass"

                if has_detection:
                    categories = data.get("categories", {})
                    policy = data.get("policy", {})

                    category_block_map = {
                        "prompt_injection": "block_prompt_injection",
                        "unsafe_input": "block_unsafe_input",
                        "unsafe_output": "block_unsafe_output",
                        "input_pii": "block_input_pii",
                        "output_pii": "block_output_pii",
                        "input_code": "block_input_code_detection",
                        "output_code": "block_output_code_detection",
                        "input_dos": "block_input_dos_detection",
                        "guardrail": "block_guardrail_detection",
                    }

                    should_block = False
                    for cat_key, block_key in category_block_map.items():
                        if categories.get(cat_key):
                            if policy.get(block_key) or policy.get("block_unsafe"):
                                should_block = True

                    if should_block:
                        verdict = "block"
                        # Use HL's own response message as the block reason
                        reason = data.get("response", {}).get("output", "Blocked by Hidden Layer policy")

                return {
                    "verdict": verdict,
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


class PromptFooClient(SecurityTool):
    """Client for PromptFoo Adaptive Guardrails API. INPUT scanning only."""

    tool_name = "promptfoo"
    display_name = "PromptFoo"

    def __init__(self):
        self.api_key = settings.promptfoo_api_key
        self.target_id = settings.promptfoo_target_id
        self.base_url = settings.promptfoo_api_url

    async def scan(self, content: str, scan_type: str = "input", prompt: Optional[str] = None) -> Dict[str, Any]:
        """Scan content with PromptFoo Guardrails. Input only — output scans are skipped."""
        start = time.time()

        # PromptFoo only handles input scanning
        if scan_type != "input":
            elapsed = int((time.time() - start) * 1000)
            return {
                "verdict": "skip",
                "reason": "PromptFoo only scans input",
                "scan_time_ms": elapsed,
                "details": {},
            }

        if not self.api_key or not self.target_id:
            elapsed = int((time.time() - start) * 1000)
            return {
                "verdict": "error",
                "reason": "PromptFoo not configured (missing API key or target ID)",
                "scan_time_ms": elapsed,
                "details": {},
            }

        try:
            url = f"{self.base_url}/api/v1/guardrails/{self.target_id}/evaluate"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "placement": "INPUT",
                "messages": [{"role": "user", "content": content}],
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                elapsed = int((time.time() - start) * 1000)

                if response.status_code != 200:
                    return {
                        "verdict": "error",
                        "reason": f"PromptFoo API error: {response.status_code}",
                        "scan_time_ms": elapsed,
                        "details": {},
                    }

                data = response.json()
                action = data.get("action", "allow")
                severity = data.get("severity", 0)

                # Extract reason from PF response — try multiple fields
                reason = None
                triggering_policies = []
                for gr in data.get("guardrailResults", []):
                    for pr in gr.get("policyResults", []):
                        if pr.get("action") in ("block", "warn"):
                            triggering_policies.append(pr)
                            if not reason and pr.get("reason"):
                                reason = pr["reason"]

                # Fall back to policy name if no reason text
                if not reason and triggering_policies:
                    policy = triggering_policies[0]
                    policy_name = policy.get("policyName", policy.get("policy", "Unknown policy"))
                    policy_score = policy.get("score")
                    # Use policy-level score if available, otherwise top-level severity
                    display_score = policy_score if policy_score is not None else severity
                    reason = f"{policy_name} (score: {display_score})" if display_score else policy_name

                # Last resort: use top-level action + severity from PF
                if not reason and action == "block":
                    reason = f"Blocked by PromptFoo (severity: {severity})"

                return {
                    "verdict": "block" if action == "block" else "pass",
                    "reason": reason,
                    "scan_time_ms": elapsed,
                    "details": {
                        "action": action,
                        "severity": severity,
                        "guardrailResults": data.get("guardrailResults", []),
                        "requestId": data.get("requestId"),
                    },
                }
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return {
                "verdict": "error",
                "reason": f"PromptFoo error: {str(e)}",
                "scan_time_ms": elapsed,
                "details": {},
            }


def get_active_tools() -> List[SecurityTool]:
    """Return list of enabled security tools based on config."""
    tools: List[SecurityTool] = []

    if settings.hiddenlayer_client_id and settings.hiddenlayer_client_secret:
        tools.append(HiddenLayerClient())

    if settings.promptfoo_api_key and settings.promptfoo_target_id:
        tools.append(PromptFooClient())

    return tools


def get_block_reason(scan_result: Dict[str, Any]) -> str:
    """Extract the first block reason from any tool in the scan result."""
    # Priority 1: reason from the tool that actually blocked
    for tool_name, result in scan_result.get("tool_results", {}).items():
        if result.get("verdict") == "block" and result.get("reason"):
            return result["reason"]
    # Priority 2: any reason from any tool
    for tool_name, result in scan_result.get("tool_results", {}).items():
        if result.get("reason"):
            return result["reason"]
    # Priority 3: name the blocking tools
    blocked_by = scan_result.get("blocked_by", [])
    if blocked_by:
        return f"Blocked by {', '.join(blocked_by)}"
    return "Security violation detected"


async def security_scan(
    content: str,
    scan_type: str = "input",
    feature_name: str = "unknown",
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform security scan with all active tools in parallel."""
    tools = get_active_tools()

    if not tools:
        return {
            "blocked": False,
            "blocked_by": [],
            "tool_results": {},
            "scan_type": scan_type,
            "feature_name": feature_name,
        }

    tasks = [asyncio.create_task(tool.scan(content, scan_type, prompt)) for tool in tools]
    results = await asyncio.gather(*tasks)

    tool_results = {}
    blocked_by = []

    for tool, result in zip(tools, results):
        tool_results[tool.tool_name] = result
        if result.get("verdict") == "block":
            blocked_by.append(tool.display_name)

    return {
        "blocked": bool(blocked_by),
        "blocked_by": blocked_by,
        "tool_results": tool_results,
        "scan_type": scan_type,
        "feature_name": feature_name,
    }


# Backward compatibility alias
dual_security_scan = security_scan


async def log_security_scan(
    db,
    scan_result: Dict[str, Any],
    content: str,
    agent_run_id: Optional[int] = None,
):
    """Log security scan results to database."""
    from app.models.security_log import SecurityLog

    tool_results = scan_result.get("tool_results", {})
    hl = tool_results.get("hidden_layer", {})

    log = SecurityLog(
        feature=scan_result.get("feature_name", "unknown"),
        scan_type=scan_result.get("scan_type", "input"),
        content_preview=content[:200] if content else "",
        tool_results=tool_results,
        # Legacy columns populated from HL results for backward compat
        hl_verdict=hl.get("verdict"),
        hl_reason=hl.get("reason"),
        hl_scan_time_ms=hl.get("scan_time_ms"),
        aim_verdict=None,
        aim_reason=None,
        aim_scan_time_ms=None,
        final_verdict="block" if scan_result.get("blocked") else "pass",
        agent_run_id=agent_run_id,
    )

    db.add(log)
    await db.commit()
    return log
