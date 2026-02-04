import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sse_starlette.sse import EventSourceResponse
from app.database import get_db
from app.models.agent_run import AgentRun, AgentStep
from app.schemas.agent import AgentInfo, AgentRunRequest, AgentChatRequest, AgentRunResponse, AgentStepResponse
from app.agents.patient_monitor_agent import patient_monitor_agent
from app.agents.research_agent import clinical_research_agent

router = APIRouter()

AGENTS = {
    "patient_monitor": patient_monitor_agent,
    "clinical_research": clinical_research_agent,
}


@router.get("")
async def list_agents(db: AsyncSession = Depends(get_db)):
    agents_info = []
    for key, agent in AGENTS.items():
        last_run_result = await db.execute(
            select(AgentRun)
            .where(AgentRun.agent_type == key)
            .order_by(AgentRun.started_at.desc())
            .limit(1)
        )
        last_run = last_run_result.scalar_one_or_none()

        agents_info.append({
            "agent_type": agent.agent_type,
            "name": agent.name,
            "description": agent.description,
            "tools": agent.available_tools,
            "last_run": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
            "last_status": last_run.status if last_run else None,
        })
    return {"agents": agents_info}


@router.post("/{agent_type}/run")
async def run_agent(agent_type: str, req: AgentRunRequest, db: AsyncSession = Depends(get_db)):
    agent = AGENTS.get(agent_type)
    if not agent:
        return {"error": f"Unknown agent type: {agent_type}"}

    task = req.task or (
        "Monitor all patients for health risks and alert the clinical team if any high-risk patients are found."
        if agent_type == "patient_monitor"
        else "Provide a general health overview of the patient population."
    )

    async def event_generator():
        async for event in agent.run(task, db):
            event_type = event.get("event", "message")
            event_data = event.get("data", {})
            yield {"event": event_type, "data": json.dumps(event_data, default=str)}
        await db.commit()

    return EventSourceResponse(event_generator())


@router.post("/research/chat")
async def chat_with_research_agent(req: AgentChatRequest, db: AsyncSession = Depends(get_db)):
    agent = clinical_research_agent
    task = req.message

    async def event_generator():
        async for event in agent.run(task, db):
            event_type = event.get("event", "message")
            event_data = event.get("data", {})
            yield {"event": event_type, "data": json.dumps(event_data, default=str)}
        await db.commit()

    return EventSourceResponse(event_generator())


@router.get("/runs")
async def list_agent_runs(
    agent_type: str = "",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = select(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit)
    if agent_type:
        query = query.where(AgentRun.agent_type == agent_type)

    result = await db.execute(query)
    runs = result.scalars().all()

    total = await db.scalar(select(func.count(AgentRun.id))) or 0

    return {
        "runs": [
            {
                "id": r.id,
                "agent_type": r.agent_type,
                "task": r.task,
                "status": r.status,
                "iterations": r.iterations,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "summary": r.summary,
            }
            for r in runs
        ],
        "total": total,
    }


@router.get("/runs/{run_id}")
async def get_agent_run(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        return {"error": "Agent run not found"}

    steps_result = await db.execute(
        select(AgentStep)
        .where(AgentStep.agent_run_id == run_id)
        .order_by(AgentStep.iteration, AgentStep.id)
    )
    steps = steps_result.scalars().all()

    return {
        "id": run.id,
        "agent_type": run.agent_type,
        "task": run.task,
        "status": run.status,
        "iterations": run.iterations,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "result": run.result,
        "summary": run.summary,
        "steps": [
            {
                "id": s.id,
                "iteration": s.iteration,
                "step_type": s.step_type,
                "content": s.content,
                "tool_name": s.tool_name,
                "tool_input": s.tool_input,
                "tool_output": s.tool_output,
                "security_scans": s.security_scans,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            }
            for s in steps
        ],
    }
