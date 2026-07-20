from unittest.mock import MagicMock, patch

from app.schemas.models import TestCase, TestCategory, ToolCall, Transcript
from app.services.judges import GroundednessJudge, JudgePanel


def _make_transcript() -> Transcript:
    test_case = TestCase(
        id="t1",
        category=TestCategory.STRAIGHTFORWARD,
        question="What is the P/E ratio of Infosys?",
        notes="control case",
    )
    return Transcript(
        test_case=test_case,
        tool_calls=[
            ToolCall(
                tool_name="get_stock_data",
                arguments={"ticker": "INFY"},
                result='{"pe_ratio": 27.3}',
            )
        ],
        final_answer="The P/E ratio of Infosys is 27.3.",
    )


def _fake_verdict_response(content: str):
    return MagicMock(choices=[MagicMock(message=MagicMock(content=content))])


@patch("app.services.judges.Groq")
def test_groundedness_judge_parses_verdict(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _fake_verdict_response(
        '{"passed": true, "score": 1.0, "reasoning": "27.3 matches the tool result exactly."}'
    )
    mock_groq_cls.return_value = mock_client

    judge = GroundednessJudge()
    verdict = judge.evaluate(_make_transcript())

    assert verdict.passed is True
    assert verdict.score == 1.0
    assert verdict.judge_name == "groundedness"


@patch("app.services.judges.Groq")
def test_judge_panel_skips_one_failing_judge_but_keeps_others(mock_groq_cls):
    mock_client = MagicMock()
    # Panel default order: groundedness, tool_use, task_completion.
    # First response is malformed (simulating a judge that fails to
    # produce parseable JSON); the other two are valid.
    mock_client.chat.completions.create.side_effect = [
        _fake_verdict_response("not valid json at all"),
        _fake_verdict_response(
            '{"passed": true, "score": 0.9, "reasoning": "correct tool called"}'
        ),
        _fake_verdict_response(
            '{"passed": false, "score": 0.3, "reasoning": "dodged the question"}'
        ),
    ]
    mock_groq_cls.return_value = mock_client

    panel = JudgePanel()
    result = panel.evaluate(_make_transcript())

    # One judge failed to parse and was skipped; the other two succeeded —
    # the panel did not crash on the first failure.
    assert len(result.verdicts) == 2
    assert result.transcript.test_case.id == "t1"
