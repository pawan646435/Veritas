import pandas as pd

from app.schemas.models import AuditResult, JudgeVerdict, TestCase, TestCategory, Transcript
from app.services.meta_eval import compute_agreement, export_labeling_sheet


def _make_result(id_: str, judge_passed: bool) -> AuditResult:
    test_case = TestCase(
        id=id_, category=TestCategory.STRAIGHTFORWARD, question=f"question {id_}", notes="n"
    )
    transcript = Transcript(test_case=test_case, tool_calls=[], final_answer="answer")
    verdict = JudgeVerdict(
        judge_name="groundedness",
        passed=judge_passed,
        score=1.0 if judge_passed else 0.0,
        reasoning="r",
    )
    return AuditResult(transcript=transcript, verdicts=[verdict])


def test_perfect_agreement_gives_kappa_of_one():
    results = [
        _make_result("t1", True),
        _make_result("t2", False),
        _make_result("t3", True),
        _make_result("t4", False),
    ]
    labels = pd.DataFrame(
        {
            "test_case_id": ["t1", "t2", "t3", "t4"],
            "judge_name": ["groundedness"] * 4,
            "human_passed": [True, False, True, False],
        }
    )

    summary = compute_agreement(results, labels)
    row = summary[summary["judge_name"] == "groundedness"].iloc[0]

    assert row["agreement_rate"] == 1.0
    assert row["cohens_kappa"] == 1.0


def test_partial_disagreement_gives_kappa_below_agreement_rate():
    # human disagrees with the judge on exactly one of four cases (t2)
    results = [
        _make_result("t1", True),
        _make_result("t2", True),
        _make_result("t3", False),
        _make_result("t4", False),
    ]
    labels = pd.DataFrame(
        {
            "test_case_id": ["t1", "t2", "t3", "t4"],
            "judge_name": ["groundedness"] * 4,
            "human_passed": [True, False, False, False],
        }
    )

    summary = compute_agreement(results, labels)
    row = summary[summary["judge_name"] == "groundedness"].iloc[0]

    # Hand-calculated: po = 0.75, p_human_pass = 0.25, p_judge_pass = 0.5,
    # pe = 0.25*0.5 + 0.75*0.5 = 0.5, kappa = (0.75-0.5)/(1-0.5) = 0.5
    assert row["agreement_rate"] == 0.75
    assert abs(row["cohens_kappa"] - 0.5) < 1e-9


def test_export_labeling_sheet_hides_judge_verdict(tmp_path):
    results = [_make_result("t1", True)]
    path = tmp_path / "labels.csv"

    export_labeling_sheet(results, str(path), sample_size=5)

    df = pd.read_csv(path)
    assert "judge_passed" not in df.columns
    assert "score" not in df.columns
    assert "reasoning" not in df.columns
    assert "human_passed" in df.columns
    assert df.iloc[0]["test_case_id"] == "t1"
