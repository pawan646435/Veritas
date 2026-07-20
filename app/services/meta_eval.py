import json
import random

import pandas as pd

from app.schemas.models import AuditResult, Transcript


def _format_tool_calls(transcript: Transcript) -> str:
    if not transcript.tool_calls:
        return "none"
    return "; ".join(f"{c.tool_name}({c.arguments}) -> {c.result}" for c in transcript.tool_calls)


def export_labeling_sheet(
    results: list[AuditResult], path: str, sample_size: int = 25, seed: int = 42
) -> None:
    """Write a CSV for a human to hand-label, one row per (transcript,
    judge) pair.

    Deliberately excludes the judge's own passed/score/reasoning — only
    the raw transcript facts (question, tool calls, final answer) are
    shown. This is not an oversight: if the reviewer can see what the
    judge already decided, their own label tends to anchor toward
    agreeing with it, which would make the judges look more reliable than
    they actually are. A meta-eval that leaks the answer isn't measuring
    anything.
    """
    rng = random.Random(seed)
    sampled = results if len(results) <= sample_size else rng.sample(results, sample_size)

    rows = []
    for result in sampled:
        t = result.transcript
        for verdict in result.verdicts:
            rows.append(
                {
                    "test_case_id": t.test_case.id,
                    "category": t.test_case.category.value,
                    "question": t.test_case.question,
                    "tool_calls": _format_tool_calls(t),
                    "final_answer": t.final_answer,
                    "judge_name": verdict.judge_name,
                    "human_passed": "",  # fill in TRUE or FALSE by hand
                    "human_notes": "",  # optional — why you decided this
                }
            )

    pd.DataFrame(rows).to_csv(path, index=False)


def load_labels(path: str) -> pd.DataFrame:
    """Read a filled-in labeling sheet back, converting the human_passed
    column from text (TRUE/FALSE/1/0) into real booleans."""
    df = pd.read_csv(path)
    df["human_passed"] = (
        df["human_passed"]
        .astype(str)
        .str.strip()
        .str.upper()
        .map({"TRUE": True, "FALSE": False, "1": True, "0": False})
    )
    return df


def save_results(results: list[AuditResult], path: str) -> None:
    """Persist the actual judge verdicts so they can be compared against
    human labels later, in a separate run, after you've filled in the
    labeling sheet by hand."""
    with open(path, "w") as f:
        json.dump([r.model_dump(mode="json") for r in results], f, indent=2)


def load_results(path: str) -> list[AuditResult]:
    with open(path) as f:
        data = json.load(f)
    return [AuditResult.model_validate(d) for d in data]


def _cohens_kappa(human: pd.Series, judge: pd.Series) -> float:
    """Agreement between two raters, corrected for the agreement you'd
    expect by pure chance alone.

    Raw agreement rate is misleading on its own: if 90% of cases are
    genuinely easy passes, two raters could agree 90% of the time by pure
    chance, without either of them doing any real discriminating work.
    Kappa subtracts out that chance-agreement baseline: 1.0 is perfect
    agreement, 0.0 is no better than chance, negative means worse than
    chance (rare, but it happens with a truly unreliable judge).

    IMPORTANT DEGENERATE CASE: if either rater shows zero variance (e.g.
    the human labeled every single row the same way), kappa is
    mathematically undefined as a meaningful statistic — there's no
    variability to check for chance-agreement against. We return NaN
    explicitly in that case rather than letting the formula silently
    collapse to 0.0, which would look like "no agreement" when the truth
    is "not computable from this data at all." When this happens, fall
    back to reading the raw agreement_rate instead.
    """
    n = len(human)
    if n == 0:
        return float("nan")

    p_human_pass = human.mean()
    p_judge_pass = judge.mean()

    if p_human_pass in (0.0, 1.0) or p_judge_pass in (0.0, 1.0):
        return float("nan")

    po = (human == judge).mean()
    pe = p_human_pass * p_judge_pass + (1 - p_human_pass) * (1 - p_judge_pass)
    return (po - pe) / (1 - pe)


def compute_agreement(results: list[AuditResult], labels_df: pd.DataFrame) -> pd.DataFrame:
    """Join human labels back to the actual judge verdicts and compute,
    per judge: how many rows were labeled, the raw agreement rate, and
    Cohen's kappa."""
    judge_rows = []
    for result in results:
        for verdict in result.verdicts:
            judge_rows.append(
                {
                    "test_case_id": result.transcript.test_case.id,
                    "judge_name": verdict.judge_name,
                    "judge_passed": verdict.passed,
                }
            )
    judges_df = pd.DataFrame(judge_rows)

    merged = labels_df.merge(judges_df, on=["test_case_id", "judge_name"], how="inner")
    merged = merged.dropna(subset=["human_passed"])

    summary = []
    for judge_name, group in merged.groupby("judge_name"):
        agreement_rate = (group["human_passed"] == group["judge_passed"]).mean()
        kappa = _cohens_kappa(group["human_passed"], group["judge_passed"])
        summary.append(
            {
                "judge_name": judge_name,
                "n_labeled": len(group),
                "agreement_rate": agreement_rate,
                "cohens_kappa": kappa,
            }
        )

    return pd.DataFrame(summary)
