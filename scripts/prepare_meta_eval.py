"""Meta-eval step 1: generate, run, and judge a real batch of test cases,
then produce two files:

  reports/meta_eval_results.json  — the actual judge verdicts (hidden from you for now)
  reports/labels_to_fill.csv      — open this, fill in human_passed by hand

Usage: python scripts/prepare_meta_eval.py
"""

import os

from app.agents.finance_agent import FinanceAgent
from app.services.judges import JudgePanel
from app.services.meta_eval import export_labeling_sheet, save_results
from app.services.test_generator import TestGenerator
from app.services.test_runner import TestRunner


def main() -> None:
    print("Generating test cases...")
    test_cases = TestGenerator().generate(n=25)

    print(f"Running {len(test_cases)} test cases against the finance agent...")
    runner = TestRunner(target_agent=FinanceAgent())
    transcripts = runner.run_batch(test_cases)

    print(f"Judging {len(transcripts)} transcripts...")
    panel = JudgePanel()
    results = [panel.evaluate(t) for t in transcripts]

    os.makedirs("reports", exist_ok=True)
    save_results(results, "reports/meta_eval_results.json")
    export_labeling_sheet(results, "reports/labels_to_fill.csv", sample_size=25)

    print("\nSaved reports/meta_eval_results.json (the judges' actual verdicts)")
    print("Saved reports/labels_to_fill.csv — open this next.")
    print(
        "\nFor each row: read the question, tool calls, and final answer, "
        "then fill human_passed with TRUE or FALSE based on YOUR OWN "
        "judgment for that judge's specific dimension (groundedness, "
        "tool_use, or task_completion). Don't peek at the JSON file first."
    )


if __name__ == "__main__":
    main()
