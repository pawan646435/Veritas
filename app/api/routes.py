from fastapi import APIRouter

from app.agents.finance_agent import FinanceAgent
from app.db.repository import load_recent_audit_results, save_audit_result
from app.db.session import get_session
from app.services.judges import JudgePanel
from app.services.reporter import Reporter
from app.services.test_generator import TestGenerator
from app.services.test_runner import TestRunner

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Liveness check — used by Docker/Cloud Run to know the service is up.
    Deliberately does nothing else: no DB call, no LLM call. A health
    check that depends on external services can report "unhealthy" for
    reasons that have nothing to do with whether the app process itself
    is actually running.
    """
    return {"status": "ok"}


@router.post("/audits/run")
async def run_audit(n: int = 10) -> dict:
    """Generate, run, judge, and persist a real audit batch."""
    test_cases = TestGenerator().generate(n=n)

    runner = TestRunner(target_agent=FinanceAgent())
    transcripts = runner.run_batch(test_cases)

    panel = JudgePanel()
    async with get_session() as session:
        for t in transcripts:
            result = panel.evaluate(t)
            await save_audit_result(session, result)

    return {"generated": len(test_cases), "ran": len(transcripts)}


@router.get("/audits/report")
async def get_report(limit: int = 100) -> dict:
    """Read recent audit results back out of the database and report on
    them — the API version of scripts/report_from_db.py."""
    async with get_session() as session:
        results = await load_recent_audit_results(session, limit=limit)

    reporter = Reporter(results)
    return {
        "audited": len(results),
        "hallucination_rate": reporter.hallucination_rate(),
        "category_breakdown": reporter.category_breakdown().to_dict(),
    }
