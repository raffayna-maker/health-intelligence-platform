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
from app.services.security_service import dual_security_scan, log_security_scan
from app.models.agent_run import AgentRun, AgentStep
from app.agents.tools import TOOL_REGISTRY


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

        # Only nudge toward final_answer after 3+ iterations (give agent time to use multiple tools)
        nudge = ""
        if iteration >= 3:
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

            except Exception as e:
                error_msg = str(e)
                yield {"event": "error", "data": {"message": f"LLM error: {error_msg}", "iteration": iteration}}
                agent_run.status = "failed"
                agent_run.summary = f"LLM error at iteration {iteration}: {error_msg}"
                await db.flush()
                return

            yield {"event": "reasoning", "data": {"iteration": iteration, "reasoning": raw_reasoning}}

            # --- SECURITY SCAN: Reasoning ---
            reasoning_scan = await dual_security_scan(
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
            decision = None
            cleaned = raw_reasoning.strip()

            # Try json.loads first (standard JSON)
            try:
                decision = json.loads(cleaned)
            except json.JSONDecodeError:
                # Try to extract JSON substring
                try:
                    start = cleaned.find("{")
                    end = cleaned.rfind("}") + 1
                    if start >= 0 and end > start:
                        decision = json.loads(cleaned[start:end])
                except Exception:
                    pass

            # Fallback: ast.literal_eval handles Python-style single quotes
            # e.g. {'document_id': 3} mixed with "double quoted" strings
            if not decision:
                import ast
                try:
                    decision = ast.literal_eval(cleaned)
                except Exception:
                    try:
                        start = cleaned.find("{")
                        end = cleaned.rfind("}") + 1
                        if start >= 0 and end > start:
                            decision = ast.literal_eval(cleaned[start:end])
                    except Exception:
                        pass

            # If still no valid decision, try to infer intent
            if not decision or "type" not in decision:
                lower_text = raw_reasoning.lower()
                if "final_answer" in lower_text or (iteration >= self.max_iterations - 2) or self.short_term_memory:
                    # Treat as final answer if near end, explicitly mentioned, or we already have results
                    decision = {
                        "type": "final_answer",
                        "answer": raw_reasoning,
                        "reasoning": "Inferred from non-JSON response"
                    }
                else:
                    # Default to trying first tool only on first iteration
                    decision = {
                        "type": "use_tool",
                        "tool": self.available_tools[0] if self.available_tools else "none",
                        "input": {},
                        "reasoning": "Fallback - retrying with first available tool"
                    }

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
                    # Compile all collected results into a final answer instead of erroring
                    results_summary = "\n".join(
                        m["summary"] for m in self.short_term_memory
                    )
                    answer = results_summary or f"Results from {tool_name} have already been retrieved."

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
                input_scan = await dual_security_scan(
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

                # Security scan tool output
                output_scan = await dual_security_scan(
                    content=json.dumps(tool_result, default=str),
                    scan_type="output",
                    feature_name=f"agent_tool_{tool_name}",
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
