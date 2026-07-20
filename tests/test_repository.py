import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, TestCaseModel
from app.db.repository import load_recent_audit_results, save_audit_result
from app.schemas.models import (
    AuditResult,
    JudgeVerdict,
    TestCase,
    TestCategory,
    ToolCall,
    Transcript,
)


@pytest_asyncio.fixture
async def session_factory():
    """A fresh in-memory SQLite database per test — fast, isolated, and
    needs no external Postgres connection to run in CI."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _make_result(test_case: TestCase, answer: str) -> AuditResult:
    transcript = Transcript(
        test_case=test_case,
        tool_calls=[
            ToolCall(
                tool_name="get_stock_data",
                arguments={"ticker": "INFY"},
                result='{"price": 100}',
            )
        ],
        final_answer=answer,
    )
    verdict = JudgeVerdict(judge_name="groundedness", passed=True, score=1.0, reasoning="matches")
    return AuditResult(transcript=transcript, verdicts=[verdict])


@pytest.mark.asyncio
async def test_save_and_load_round_trip(session_factory):
    test_case = TestCase(id="t1", category=TestCategory.STRAIGHTFORWARD, question="q", notes="n")
    result = _make_result(test_case, "The price is 100")

    async with session_factory() as session:
        await save_audit_result(session, result)
        await session.commit()

    async with session_factory() as session:
        loaded = await load_recent_audit_results(session, limit=10)

    assert len(loaded) == 1
    assert loaded[0].transcript.test_case.id == "t1"
    assert loaded[0].transcript.final_answer == "The price is 100"
    assert loaded[0].transcript.tool_calls[0].tool_name == "get_stock_data"
    assert loaded[0].verdicts[0].judge_name == "groundedness"
    assert loaded[0].verdicts[0].passed is True


@pytest.mark.asyncio
async def test_save_reuses_existing_test_case_row(session_factory):
    """Running the same test case twice (e.g. across two audit runs)
    should not create a duplicate TestCase row — but should create two
    separate Transcript rows, since each run is its own record."""
    test_case = TestCase(id="t1", category=TestCategory.STRAIGHTFORWARD, question="q", notes="n")

    async with session_factory() as session:
        await save_audit_result(session, _make_result(test_case, "first run"))
        await session.commit()

    async with session_factory() as session:
        await save_audit_result(session, _make_result(test_case, "second run"))
        await session.commit()

    async with session_factory() as session:
        rows = (
            await session.execute(select(TestCaseModel).where(TestCaseModel.id == "t1"))
        ).scalars().all()
        assert len(rows) == 1  # one TestCase row, despite two saves

    async with session_factory() as session:
        loaded = await load_recent_audit_results(session, limit=10)
        assert len(loaded) == 2  # but two distinct transcripts
