"""
Initialize the database: create all tables.
Run with: python -m scripts.init_db
"""

import asyncio
from app.database import engine, Base
from app.models import Patient, Document, SecurityLog, AgentRun, AgentStep, Report


async def init():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init())
