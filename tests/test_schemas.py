import pytest
from pydantic import ValidationError

from app.schemas.models import JudgeVerdict, TestCase, TestCategory


def test_test_case_creation():
    tc = TestCase(
        id="t1",
        category=TestCategory.STRAIGHTFORWARD,
        question="What is the P/E ratio of Infosys?",
        notes="Control case — should answer normally",
    )
    assert tc.category == TestCategory.STRAIGHTFORWARD
    assert tc.id == "t1"


def test_judge_verdict_score_out_of_range_rejected():
    """Scores must stay within 0-1 — Pydantic should reject anything outside that."""
    with pytest.raises(ValidationError):
        JudgeVerdict(
            judge_name="groundedness",
            passed=False,
            score=1.5,
            reasoning="invalid score to trigger validation error",
        )
