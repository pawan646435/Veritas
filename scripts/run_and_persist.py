"""Generate, run, judge, and persist a real batch to the database.

Not part of the pytest suite: hits the real Groq API and writes to your
real Postgres database (Neon). Make sure DATABASE_URL in .env points at
your real database and you've run `alembic upgrade head` against it first.

Usage: python scripts/run_and_persist.py
"""

import asyncio

from app.agents.finance_agent import FinanceAgent
from app.db.repository import save_audit_result
from app.db.session import get_session
from app.services.judges import JudgePanel
from app.services.test_generator import TestGenerator
from app.services.test_runner import TestRunner


async def main() -> None:
    print("Generating test cases...")
    test_cases = TestGenerator().generate(n=10)

    print(f"Running {len(test_cases)} test cases...")
    runner = TestRunner(target_agent=FinanceAgent())
    transcripts = runner.run_batch(test_cases)

    print(f"Judging {len(transcripts)} transcripts and saving to the database...")
    panel = JudgePanel()

    async with get_session() as session:
        for t in transcripts:
            result = panel.evaluate(t)
            await save_audit_result(session, result)

    print(f"Saved {len(transcripts)} audit results to the database.")


if __name__ == "__main__":
    asyncio.run(main())
