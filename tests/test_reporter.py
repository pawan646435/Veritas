from app.schemas.models import AuditResult, JudgeVerdict, TestCase, TestCategory, Transcript
from app.services.reporter import Reporter


def _make_result(
    id_: str,
    category: TestCategory,
    groundedness_passed: bool,
    groundedness_score: float,
    tool_use_passed: bool = True,
    tool_use_score: float = 1.0,
) -> AuditResult:
    test_case = TestCase(id=id_, category=category, question=f"question {id_}", notes="n")
    transcript = Transcript(test_case=test_case, tool_calls=[], final_answer="answer")
    verdicts = [
        JudgeVerdict(
            judge_name="groundedness",
            passed=groundedness_passed,
            score=groundedness_score,
            reasoning="r",
        ),
        JudgeVerdict(
            judge_name="tool_use", passed=tool_use_passed, score=tool_use_score, reasoning="r"
        ),
    ]
    return AuditResult(transcript=transcript, verdicts=verdicts)


def test_hallucination_rate_computes_correctly():
    results = [
        _make_result("t1", TestCategory.STRAIGHTFORWARD, True, 1.0),
        _make_result("t2", TestCategory.FABRICATED_DATA, False, 0.1),
        _make_result("t3", TestCategory.FABRICATED_DATA, True, 0.9),
        _make_result("t4", TestCategory.FABRICATED_DATA, False, 0.0),
    ]
    reporter = Reporter(results)

    # 2 of 4 transcripts failed groundedness -> 50% hallucination rate
    assert reporter.hallucination_rate() == 0.5


def test_category_breakdown_groups_correctly():
    results = [
        _make_result("t1", TestCategory.STRAIGHTFORWARD, True, 1.0),
        _make_result("t2", TestCategory.FABRICATED_DATA, False, 0.1),
        _make_result("t3", TestCategory.FABRICATED_DATA, True, 0.9),
    ]
    reporter = Reporter(results)
    breakdown = reporter.category_breakdown()

    assert breakdown.loc["straightforward", "groundedness_passed"] == 1.0
    assert breakdown.loc["fabricated_data", "groundedness_passed"] == 0.5


def test_worst_offenders_sorted_ascending_by_avg_score():
    results = [
        _make_result("t1", TestCategory.STRAIGHTFORWARD, True, 1.0, tool_use_score=1.0),
        _make_result("t2", TestCategory.FABRICATED_DATA, False, 0.0, tool_use_score=0.0),
    ]
    reporter = Reporter(results)
    worst = reporter.worst_offenders(n=1)

    assert worst.iloc[0]["test_case_id"] == "t2"


def test_empty_results_do_not_crash():
    reporter = Reporter([])
    assert reporter.hallucination_rate() == 0.0
    assert reporter.category_breakdown().empty
    assert reporter.worst_offenders().empty
    assert reporter.summary() == "No results to report."
