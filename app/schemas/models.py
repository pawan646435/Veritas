from enum import StrEnum

from pydantic import BaseModel, Field


class TestCategory(StrEnum):
    """The kind of test case being run against the target agent."""

    FABRICATED_DATA = "fabricated_data"
    AMBIGUOUS_PHRASING = "ambiguous_phrasing"
    CONFLICTING_INSTRUCTION = "conflicting_instruction"
    OUT_OF_SCOPE = "out_of_scope"
    STRAIGHTFORWARD = "straightforward"


class TestCase(BaseModel):
    """One question (adversarial or control) to run against the target agent."""

    id: str
    category: TestCategory
    question: str
    notes: str = Field(
        description="Why this test case is tricky, and what a correct agent should do"
    )


class ToolCall(BaseModel):
    """A record of one tool the target agent invoked while answering."""

    tool_name: str
    arguments: dict
    result: str


class Transcript(BaseModel):
    """Everything that happened when we ran one TestCase against the target agent."""

    test_case: TestCase
    tool_calls: list[ToolCall] = Field(default_factory=list)
    final_answer: str


class JudgeVerdict(BaseModel):
    """One judge's verdict on one transcript."""

    judge_name: str
    passed: bool
    score: float = Field(ge=0, le=1, description="0 = total failure, 1 = fully correct")
    reasoning: str


class AuditResult(BaseModel):
    """A transcript plus every judge's verdict on it — the unit the reporter works on."""

    transcript: Transcript
    verdicts: list[JudgeVerdict]
