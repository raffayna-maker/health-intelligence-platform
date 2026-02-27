"""
Abstract base agent with the Observe-Reason-Decide-Execute autonomous loop.
All agents inherit from this and provide their own system prompt, tool set, and goals.
"""

import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ollama_service import ollama_service
from app.services.security_service import security_scan, log_security_scan
from app.models.agent_run import AgentRun, AgentStep
from app.agents.tools import TOOL_REGISTRY
from app.exceptions import AIMBlockedException


class BaseAgent(ABC):
    """
    Autonomous AI agent with:
    - Memory (short-term, long-term, working)
    - Reasoning engine (LLM)
    - Tool registry
    - Observe-Reason-Decide-Execute loop
    - Dual security scanning at every step
    """

    def __init__(self):
        self.short_term_memory: list[dict] = []
        self.working_memory: dict = {}
        self.max_iterations = 15
        self.tool_call_history: list[tuple] = []  # Track (tool_name, input) to detect loops

    @property
    @abstractmethod
    def agent_type(self) -> str:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        ...

    @property
    @abstractmethod
    def available_tools(self) -> list[str]:
        ...

    def _parse_decision(self, raw: str) -> dict:
        """Parse LLM output into a decision dict. Handles JSON, Python dicts, and malformed output."""
        import ast
        import re

        cleaned = raw.strip()

        # Method 1: Standard JSON
        for text in [cleaned, cleaned[cleaned.find("{"):cleaned.rfind("}") + 1] if "{" in cleaned else ""]:
            if not text:
                continue
            try:
                result = json.loads(text)
                if isinstance(result, dict) and "type" in result:
                    return result
            except Exception:
                pass

        # Method 2: Python literal eval (handles single quotes)
        for text in [cleaned, cleaned[cleaned.find("{"):cleaned.rfind("}") + 1] if "{" in cleaned else ""]:
            if not text:
                continue
            try:
                result = ast.literal_eval(text)
                if isinstance(result, dict) and "type" in result:
                    return result
            except Exception:
                pass

        # Method 3: Regex extraction — look for tool call patterns regardless of quote style
        if "use_tool" in cleaned:
            tool_match = re.search(r"""["']?tool["']?\s*:\s*["'](\w+)["']""", cleaned)
            if tool_match and tool_match.group(1) in self.available_tools:
                tool_name = tool_match.group(1)
                input_dict = {}
                # Extract document_id (integer param)
                doc_match = re.search(r"""["']?document_id["']?\s*:\s*(\d+)""", cleaned)
                if doc_match:
                    input_dict["document_id"] = int(doc_match.group(1))
                # Extract query (string param)
                query_match = re.search(r"""["']query["']\s*:\s*["']([^"']+)["']""", cleaned)
                if query_match:
                    input_dict["query"] = query_match.group(1)
                return {
                    "type": "use_tool",
                    "tool": tool_name,
                    "input": input_dict,
                    "reasoning": "Extracted via pattern matching",
                }

        # Method 4: Infer intent from text
        lower = cleaned.lower()
        if "final_answer" in lower or self.short_term_memory:
            return {
                "type": "final_answer",
                "answer": cleaned,
                "reasoning": "Inferred from non-JSON response",
            }

        # Method 5: Last resort — try first tool on iteration 0
        return {
            "type": "use_tool",
            "tool": self.available_tools[0] if self.available_tools else "none",
            "input": {},
            "reasoning": "Fallback — first available tool",
        }

    def _build_tool_descriptions(self) -> str:
        lines = []
        for tool_name in self.available_tools:
            info = TOOL_REGISTRY.get(tool_name)
            if info:
                params = ", ".join(f"{k}: {v}" for k, v in info["parameters"].items())
                lines.append(f"- {tool_name}({params}): {info['description']}")
        return "\n".join(lines)

    def _build_reasoning_prompt(self, task: str, iteration: int) -> str:
        history = ""
        for mem in self.short_term_memory[-3:]:
            history += f"\n- {mem['summary']}"

        # Simplified tool list - just names, no descriptions
        tools = ", ".join(self.available_tools[:4])  # Only show first 4 tools to save tokens

        # Nudge toward final_answer based on progress
        nudge = ""
        if iteration >= 2 and len(self.short_term_memory) >= 2:
            nudge = "\nYou have ALL the information needed. You MUST respond with a final_answer NOW. Do NOT call any more tools."
        elif iteration >= 3:
            nudge = "\nYou have enough information. Provide a final_answer now."
        elif self.short_term_memory and iteration >= 1:
            nudge = "\nUse a DIFFERENT tool if needed, or provide a final_answer. Do NOT repeat a tool you already used."

        return f"""Task: {task}
Tools: {tools}
Done:{history or " nothing yet"}{nudge}
Step {iteration + 1}/{self.max_iterations}

JSON only:
{{"type":"use_tool","tool":"<name>","input":{{}},"reasoning":"..."}}
OR {{"type":"final_answer","answer":"...","reasoning":"..."}}"""

    async def run(self, task: str, db: AsyncSession) -> AsyncGenerator[dict, None]:
        """
        Main autonomous execution loop. Yields SSE events for real-time UI updates.
        """
        # Create agent run record
        agent_run = AgentRun(agent_type=self.agent_type, task=task, status="running")
        db.add(agent_run)
        await db.flush()
        await db.refresh(agent_run)
        run_id = agent_run.id

        self.working_memory = {"task": task, "status": "in_progress", "iteration": 0}
        self.short_term_memory = []
        self.tool_call_history = []

        yield {"event": "start", "data": {"run_id": run_id, "agent": self.agent_type, "task": task}}

        for iteration in range(self.max_iterations):
            self.working_memory["iteration"] = iteration

            # --- STEP 1: REASON about next action ---
            reasoning_prompt = self._build_reasoning_prompt(task, iteration)

            try:
                raw_reasoning = await ollama_service.generate(
                    reasoning_prompt, system=self.system_prompt, temperature=0.1
                )

                # Clean up response
                raw_reasoning = raw_reasoning.strip()

                # If empty response, retry once
                if not raw_reasoning:
                    yield {"event": "message", "data": {"iteration": iteration, "message": "Empty response, retrying..."}}
                    raw_reasoning = await ollama_service.generate(
                        reasoning_prompt, system=self.system_prompt, temperature=0.2
                    )

            except AIMBlockedException as e:
                yield {"event": "blocked", "data": {"iteration": iteration, "stage": "reasoning", "message": e.reason}}
                agent_run.status = "blocked"
                agent_run.summary = f"Blocked by AIM at iteration {iteration}: {e.reason}"
                agent_run.iterations = iteration + 1
                agent_run.completed_at = datetime.utcnow()
                await db.flush()
                return

            except Exception as e:
                error_msg = str(e)
                yield {"event": "error", "data": {"message": f"LLM error: {error_msg}", "iteration": iteration}}
                agent_run.status = "failed"
                agent_run.summary = f"LLM error at iteration {iteration}: {error_msg}"
                await db.flush()
                return

            yield {"event": "reasoning", "data": {"iteration": iteration, "reasoning": raw_reasoning}}

            # --- SECURITY SCAN: Reasoning ---
            reasoning_scan = await security_scan(
                content=raw_reasoning,
                scan_type="input",
                feature_name=f"{self.agent_type}_agent",
            )
            await log_security_scan(db, reasoning_scan, raw_reasoning, agent_run_id=run_id)

            step_reasoning = AgentStep(
                agent_run_id=run_id,
                iteration=iteration,
                step_type="reasoning",
                content=raw_reasoning,
                security_scans=reasoning_scan,
            )
            db.add(step_reasoning)
            await db.flush()

            yield {"event": "security_scan", "data": {"iteration": iteration, "stage": "reasoning", "scan": reasoning_scan}}

            if reasoning_scan.get("blocked"):
                yield {"event": "blocked", "data": {"iteration": iteration, "stage": "reasoning", "scan": reasoning_scan}}
                agent_run.status = "blocked"
                agent_run.summary = f"Blocked at iteration {iteration}: reasoning flagged by security"
                agent_run.iterations = iteration + 1
                agent_run.completed_at = datetime.utcnow()
                await db.flush()
                return

            # --- STEP 2: PARSE decision ---
            decision = self._parse_decision(raw_reasoning)

            yield {"event": "decision", "data": {"iteration": iteration, "decision_type": decision.get("type"), "details": decision}}

            # --- STEP 3: EXECUTE decision ---
            if decision.get("type") == "use_tool":
                tool_name = decision.get("tool", "")
                tool_input = decision.get("input", {})

                # Ensure tool_input is a dict (LLM sometimes generates strings)
                if not isinstance(tool_input, dict):
                    tool_input = {}

                if tool_name not in TOOL_REGISTRY or tool_name not in self.available_tools:
                    yield {"event": "tool_error", "data": {"iteration": iteration, "error": f"Unknown tool: {tool_name}"}}
                    self.short_term_memory.append({"iteration": iteration, "summary": f"Tried unknown tool: {tool_name}"})
                    continue

                # Check for infinite loops (same tool with same input called 2+ times)
                tool_signature = (tool_name, json.dumps(tool_input, sort_keys=True))
                recent_calls = self.tool_call_history[-5:] if len(self.tool_call_history) >= 5 else self.tool_call_history
                if recent_calls.count(tool_signature) >= 1:
                    # Synthesize a proper answer from collected data via LLM
                    results_summary = "\n".join(
                        m["summary"] for m in self.short_term_memory
                    )
                    try:
                        synthesis_prompt = f"Answer this question: {task}\n\nCollected data:\n{results_summary[:2000]}\n\nProvide a clear, helpful answer in plain text. No JSON."
                        answer = await ollama_service.generate(
                            synthesis_prompt,
                            system="You are a medical document assistant. Summarize the data into a clear answer. Plain text only.",
                            temperature=0.1,
                        )
                        if not answer or len(answer.strip()) < 10:
                            answer = results_summary
                    except AIMBlockedException:
                        answer = results_summary
                    except Exception:
                        answer = results_summary

                    step_final = AgentStep(
                        agent_run_id=run_id,
                        iteration=iteration,
                        step_type="final_answer",
                        content=answer,
                    )
                    db.add(step_final)

                    agent_run.status = "completed"
                    agent_run.summary = answer[:500]
                    agent_run.iterations = iteration + 1
                    agent_run.completed_at = datetime.utcnow()
                    agent_run.result = {"answer": answer, "reasoning": "Auto-completed after loop detection"}
                    await db.flush()

                    yield {"event": "complete", "data": {
                        "run_id": run_id,
                        "iterations": iteration + 1,
                        "answer": answer,
                        "reasoning": "Auto-completed: compiled results from tool calls",
                        "status": "completed",
                    }}
                    return

                self.tool_call_history.append(tool_signature)

                # Security scan tool input
                input_scan = await security_scan(
                    content=json.dumps(tool_input),
                    scan_type="input",
                    feature_name=f"agent_tool_{tool_name}",
                )
                await log_security_scan(db, input_scan, json.dumps(tool_input), agent_run_id=run_id)

                yield {"event": "security_scan", "data": {"iteration": iteration, "stage": "tool_input", "tool": tool_name, "scan": input_scan}}

                if input_scan.get("blocked"):
                    yield {"event": "blocked", "data": {"iteration": iteration, "stage": "tool_input", "scan": input_scan}}
                    agent_run.status = "blocked"
                    agent_run.summary = f"Blocked at iteration {iteration}: tool input for {tool_name} flagged"
                    agent_run.iterations = iteration + 1
                    agent_run.completed_at = datetime.utcnow()
                    await db.flush()
                    return

                # Execute tool
                yield {"event": "tool_executing", "data": {"iteration": iteration, "tool": tool_name, "input": tool_input}}

                try:
                    tool_fn = TOOL_REGISTRY[tool_name]["fn"]
                    tool_result = await tool_fn(db=db, **tool_input)

                    # Ensure we have a valid result
                    if tool_result is None:
                        tool_result = {"error": "Tool returned None"}

                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()
                    tool_result = {"error": str(e), "traceback": error_trace}
                    yield {"event": "message", "data": {"iteration": iteration, "message": f"Tool error: {str(e)}"}}

                yield {"event": "tool_result", "data": {"iteration": iteration, "tool": tool_name, "result": tool_result}}

                # Security scan tool output — tool results are untrusted external data
                # that will be fed back to the LLM (indirect prompt injection vector).
                # HL scans for injection; PF is excluded here because its guardrail
                # policies (harmful:specialized-advice, harmful:privacy) are designed
                # for user-facing input/output and cause false positives on legitimate
                # clinical data returned by medical reference tools.
                output_scan = await security_scan(
                    content=json.dumps(tool_result, default=str),
                    scan_type="input",
                    feature_name=f"agent_tool_{tool_name}",
                    exclude_tools=["promptfoo"],
                )
                await log_security_scan(db, output_scan, json.dumps(tool_result, default=str), agent_run_id=run_id)

                yield {"event": "security_scan", "data": {"iteration": iteration, "stage": "tool_output", "tool": tool_name, "scan": output_scan}}

                # Log step
                step_tool = AgentStep(
                    agent_run_id=run_id,
                    iteration=iteration,
                    step_type="tool_call",
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output=tool_result,
                    security_scans={"input": input_scan, "output": output_scan},
                )
                db.add(step_tool)
                await db.flush()

                if output_scan.get("blocked"):
                    yield {"event": "blocked", "data": {"iteration": iteration, "stage": "tool_output", "scan": output_scan}}
                    agent_run.status = "blocked"
                    agent_run.summary = f"Blocked at iteration {iteration}: tool output from {tool_name} flagged"
                    agent_run.iterations = iteration + 1
                    agent_run.completed_at = datetime.utcnow()
                    await db.flush()
                    return

                # Update memory with more context so the LLM knows what it got
                result_summary = json.dumps(tool_result, default=str)[:500]
                self.short_term_memory.append({
                    "iteration": iteration,
                    "summary": f"Used {tool_name} -> {result_summary}",
                })

            elif decision.get("type") == "final_answer":
                answer = decision.get("answer", "")
                reasoning = decision.get("reasoning", "")

                step_final = AgentStep(
                    agent_run_id=run_id,
                    iteration=iteration,
                    step_type="final_answer",
                    content=answer,
                )
                db.add(step_final)

                agent_run.status = "completed"
                agent_run.iterations = iteration + 1
                agent_run.completed_at = datetime.utcnow()
                agent_run.result = {"answer": answer, "reasoning": reasoning}
                agent_run.summary = answer[:500]
                await db.flush()

                yield {"event": "complete", "data": {
                    "run_id": run_id,
                    "iterations": iteration + 1,
                    "answer": answer,
                    "reasoning": reasoning,
                    "status": "completed",
                }}
                return

            elif decision.get("type") == "need_human":
                reason = decision.get("reason", "")
                agent_run.status = "escalated"
                agent_run.iterations = iteration + 1
                agent_run.completed_at = datetime.utcnow()
                agent_run.result = {"escalation_reason": reason}
                agent_run.summary = f"Escalated: {reason}"
                await db.flush()

                yield {"event": "escalated", "data": {"run_id": run_id, "reason": reason}}
                return

        # Max iterations reached
        agent_run.status = "timeout"
        agent_run.iterations = self.max_iterations
        agent_run.completed_at = datetime.utcnow()
        agent_run.summary = "Reached maximum iterations without completing task"
        await db.flush()

        yield {"event": "timeout", "data": {"run_id": run_id, "iterations": self.max_iterations}}
