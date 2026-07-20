from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import JudgeVerdictModel, TestCaseModel, ToolCallModel, TranscriptModel
from app.schemas.models import (
    AuditResult,
    JudgeVerdict,
    TestCase,
    TestCategory,
    ToolCall,
    Transcript,
)


async def save_audit_result(session: AsyncSession, result: AuditResult) -> None:
    """Persist one AuditResult. Creates the TestCase row if it doesn't
    already exist — the same test case can legitimately show up across
    multiple runs, so we check rather than blindly inserting a duplicate.
    """
    test_case = result.transcript.test_case
    existing = await session.get(TestCaseModel, test_case.id)
    if existing is None:
        session.add(
            TestCaseModel(
                id=test_case.id,
                category=test_case.category.value,
                question=test_case.question,
                notes=test_case.notes,
            )
        )

    # Passing child ORM objects directly into the parent's relationship
    # list lets SQLAlchemy handle foreign-key wiring automatically at
    # flush time — no need to manually flush the transcript first to get
    # its auto-generated id before creating its tool_calls/verdicts.
    transcript_model = TranscriptModel(
        test_case_id=test_case.id,
        final_answer=result.transcript.final_answer,
        tool_calls=[
            ToolCallModel(tool_name=tc.tool_name, arguments=tc.arguments, result=tc.result)
            for tc in result.transcript.tool_calls
        ],
        verdicts=[
            JudgeVerdictModel(
                judge_name=v.judge_name, passed=v.passed, score=v.score, reasoning=v.reasoning
            )
            for v in result.verdicts
        ],
    )
    session.add(transcript_model)


async def load_recent_audit_results(session: AsyncSession, limit: int = 50) -> list[AuditResult]:
    """Load the most recent N transcripts, each with its judge verdicts,
    back out as domain AuditResult objects — the reverse of
    save_audit_result. Callers (Reporter, meta-eval) never need to know
    the database exists at all; they only ever see AuditResult.

    `selectinload` eagerly loads each relationship in a small, separate
    batch query rather than one extra query per row per relationship —
    the standard fix for the classic ORM "N+1 query" performance problem.
    """
    stmt = (
        select(TranscriptModel)
        .options(
            selectinload(TranscriptModel.tool_calls),
            selectinload(TranscriptModel.verdicts),
            selectinload(TranscriptModel.test_case),
        )
        .order_by(TranscriptModel.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()

    results = []
    for row in rows:
        test_case = TestCase(
            id=row.test_case.id,
            category=TestCategory(row.test_case.category),
            question=row.test_case.question,
            notes=row.test_case.notes,
        )
        transcript = Transcript(
            test_case=test_case,
            tool_calls=[
                ToolCall(tool_name=tc.tool_name, arguments=tc.arguments, result=tc.result)
                for tc in row.tool_calls
            ],
            final_answer=row.final_answer,
        )
        verdicts = [
            JudgeVerdict(
                judge_name=v.judge_name, passed=v.passed, score=v.score, reasoning=v.reasoning
            )
            for v in row.verdicts
        ]
        results.append(AuditResult(transcript=transcript, verdicts=verdicts))

    return results
