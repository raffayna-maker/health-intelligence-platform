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
from app.services.security_service import dual_security_scan
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
        for mem in self.short_term_memory[-10:]:
            history += f"\nStep {mem['iteration']}: {mem['summary']}"

        tools_desc = self._build_tool_descriptions()

        return f"""Task: {task}

Available tools:
{tools_desc}

Previous steps:{history if history else " (none yet - this is the first step)"}

Current iteration: {iteration} of {self.max_iterations}

Based on the task and what has been done so far, decide what to do next.
You MUST respond with EXACTLY one JSON object in one of these formats:

To use a tool:
{{"type": "use_tool", "tool": "tool_name", "input": {{"param": "value"}}, "reasoning": "why I chose this"}}

To provide the final answer (when task is complete):
{{"type": "final_answer", "answer": "your complete answer", "reasoning": "why task is complete"}}

To escalate to a human:
{{"type": "need_human", "reason": "why human intervention needed"}}

Respond with ONLY the JSON object, nothing else."""

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

        yield {"event": "start", "data": {"run_id": run_id, "agent": self.agent_type, "task": task}}

        for iteration in range(self.max_iterations):
            self.working_memory["iteration"] = iteration

            # --- STEP 1: REASON about next action ---
            reasoning_prompt = self._build_reasoning_prompt(task, iteration)

            try:
                raw_reasoning = await ollama_service.generate(
                    reasoning_prompt, system=self.system_prompt, temperature=0.3
                )
            except Exception as e:
                yield {"event": "error", "data": {"message": f"LLM error: {e}", "iteration": iteration}}
                agent_run.status = "failed"
                agent_run.summary = f"LLM error at iteration {iteration}: {e}"
                await db.flush()
                return

            yield {"event": "reasoning", "data": {"iteration": iteration, "reasoning": raw_reasoning}}

            # --- SECURITY SCAN: Reasoning ---
            reasoning_scan = await dual_security_scan(
                content=raw_reasoning,
                scan_type="agent_reasoning",
                feature=f"{self.agent_type}_agent",
                db=db,
                agent_run_id=run_id,
            )

            step_reasoning = AgentStep(
                agent_run_id=run_id,
                iteration=iteration,
                step_type="reasoning",
                content=raw_reasoning,
                security_scans=reasoning_scan.model_dump(),
            )
            db.add(step_reasoning)
            await db.flush()

            yield {"event": "security_scan", "data": {"iteration": iteration, "stage": "reasoning", "scan": reasoning_scan.model_dump()}}

            if reasoning_scan.blocked:
                yield {"event": "blocked", "data": {"iteration": iteration, "stage": "reasoning", "scan": reasoning_scan.model_dump()}}
                agent_run.status = "blocked"
                agent_run.summary = f"Blocked at iteration {iteration}: reasoning flagged by security"
                agent_run.iterations = iteration + 1
                agent_run.completed_at = datetime.utcnow()
                await db.flush()
                return

            # --- STEP 2: PARSE decision ---
            try:
                decision = json.loads(raw_reasoning.strip())
            except json.JSONDecodeError:
                try:
                    start = raw_reasoning.find("{")
                    end = raw_reasoning.rfind("}") + 1
                    if start >= 0 and end > start:
                        decision = json.loads(raw_reasoning[start:end])
                    else:
                        decision = {"type": "final_answer", "answer": raw_reasoning, "reasoning": "Could not parse as JSON"}
                except Exception:
                    decision = {"type": "final_answer", "answer": raw_reasoning, "reasoning": "Parse failure"}

            yield {"event": "decision", "data": {"iteration": iteration, "decision_type": decision.get("type"), "details": decision}}

            # --- STEP 3: EXECUTE decision ---
            if decision.get("type") == "use_tool":
                tool_name = decision.get("tool", "")
                tool_input = decision.get("input", {})

                if tool_name not in TOOL_REGISTRY or tool_name not in self.available_tools:
                    yield {"event": "tool_error", "data": {"iteration": iteration, "error": f"Unknown tool: {tool_name}"}}
                    self.short_term_memory.append({"iteration": iteration, "summary": f"Tried unknown tool: {tool_name}"})
                    continue

                # Security scan tool input
                input_scan = await dual_security_scan(
                    content=json.dumps(tool_input),
                    scan_type="tool_call_input",
                    feature=f"agent_tool_{tool_name}",
                    db=db,
                    agent_run_id=run_id,
                )

                yield {"event": "security_scan", "data": {"iteration": iteration, "stage": "tool_input", "tool": tool_name, "scan": input_scan.model_dump()}}

                if input_scan.blocked:
                    yield {"event": "blocked", "data": {"iteration": iteration, "stage": "tool_input", "scan": input_scan.model_dump()}}
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
                except Exception as e:
                    tool_result = {"error": str(e)}

                yield {"event": "tool_result", "data": {"iteration": iteration, "tool": tool_name, "result": tool_result}}

                # Security scan tool output
                output_scan = await dual_security_scan(
                    content=json.dumps(tool_result, default=str),
                    scan_type="tool_call_output",
                    feature=f"agent_tool_{tool_name}",
                    db=db,
                    agent_run_id=run_id,
                )

                yield {"event": "security_scan", "data": {"iteration": iteration, "stage": "tool_output", "tool": tool_name, "scan": output_scan.model_dump()}}

                # Log step
                step_tool = AgentStep(
                    agent_run_id=run_id,
                    iteration=iteration,
                    step_type="tool_call",
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_output=tool_result,
                    security_scans={"input": input_scan.model_dump(), "output": output_scan.model_dump()},
                )
                db.add(step_tool)
                await db.flush()

                if output_scan.blocked:
                    yield {"event": "blocked", "data": {"iteration": iteration, "stage": "tool_output", "scan": output_scan.model_dump()}}
                    agent_run.status = "blocked"
                    agent_run.summary = f"Blocked at iteration {iteration}: tool output from {tool_name} flagged"
                    agent_run.iterations = iteration + 1
                    agent_run.completed_at = datetime.utcnow()
                    await db.flush()
                    return

                # Update memory
                result_summary = json.dumps(tool_result, default=str)[:200]
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
