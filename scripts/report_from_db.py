"""Read recent audit results back out of the database and report on them.

This is the actual payoff of persistence: unlike Phase 5's reporter, which
only ever saw one in-memory batch, this can report on results accumulated
across many separate runs over time.

Usage: python scripts/report_from_db.py
"""

import asyncio

from app.db.repository import load_recent_audit_results
from app.db.session import get_session
from app.services.reporter import Reporter


async def main() -> None:
    async with get_session() as session:
        results = await load_recent_audit_results(session, limit=100)

    print(f"Loaded {len(results)} audit results from the database.\n")

    reporter = Reporter(results)
    print(reporter.summary())


if __name__ == "__main__":
    asyncio.run(main())
