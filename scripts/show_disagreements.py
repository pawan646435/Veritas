"""Show exactly which transcripts a judge disagreed with your human
labels on, including the judge's own stated reasoning — the concrete,
actionable output behind the aggregate agreement_rate number.

Usage: python scripts/show_disagreements.py
"""

import pandas as pd

from app.services.meta_eval import load_labels, load_results


def main() -> None:
    results = load_results("reports/meta_eval_results.json")
    labels = load_labels("reports/labels_to_fill.csv")

    judge_rows = [
        {
            "test_case_id": r.transcript.test_case.id,
            "judge_name": v.judge_name,
            "judge_passed": v.passed,
            "judge_reasoning": v.reasoning,
        }
        for r in results
        for v in r.verdicts
    ]
    judges_df = pd.DataFrame(judge_rows)

    merged = labels.merge(judges_df, on=["test_case_id", "judge_name"], how="inner")
    merged = merged.dropna(subset=["human_passed"])

    disagreements = merged[merged["human_passed"] != merged["judge_passed"]]

    if disagreements.empty:
        print("No disagreements found — judges matched your labels on every row.")
        return

    print(f"{len(disagreements)} disagreement(s) found:\n")
    for _, row in disagreements.iterrows():
        print(f"[{row['judge_name']}] {row['question']}")
        print(f"  you said: {row['human_passed']}   judge said: {row['judge_passed']}")
        print(f"  judge's reasoning: {row['judge_reasoning']}\n")


if __name__ == "__main__":
    main()
