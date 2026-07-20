from app.schemas.models import AgentResponse, TestCase, TestCategory
from app.services.test_runner import TestRunner


class ScriptedAgent:
    """A fake TargetAgent whose behavior per-question is pre-scripted.

    Satisfies the TargetAgent Protocol from Phase 1 with a plain object —
    no Groq client, no unittest.mock needed, just the right method shape.
    This is the direct payoff of using a Protocol instead of an ABC: any
    object shaped correctly is testable, real or fake, with no inheritance
    and no patching required.
    """

    def __init__(self, script: dict):
        self._script = script

    def answer(self, question: str) -> AgentResponse:
        outcome = self._script[question]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _make_test_case(id_: str, question: str) -> TestCase:
    return TestCase(
        id=id_,
        category=TestCategory.STRAIGHTFORWARD,
        question=question,
        notes="control case",
    )


def test_run_one_builds_transcript_from_agent_response():
    agent = ScriptedAgent({"what is X": AgentResponse(tool_calls=[], final_answer="27.3")})
    runner = TestRunner(target_agent=agent)

    transcript = runner.run_one(_make_test_case("t1", "what is X"))

    assert transcript.final_answer == "27.3"
    assert transcript.test_case.id == "t1"


def test_run_batch_skips_failing_case_but_keeps_others():
    agent = ScriptedAgent(
        {
            "good question": AgentResponse(tool_calls=[], final_answer="ok"),
            "bad question": RuntimeError("simulated crash"),
        }
    )
    runner = TestRunner(target_agent=agent)

    transcripts = runner.run_batch(
        [
            _make_test_case("t1", "good question"),
            _make_test_case("t2", "bad question"),
        ]
    )

    # Only the good case survives — the batch kept going instead of aborting.
    assert len(transcripts) == 1
    assert transcripts[0].test_case.id == "t1"
