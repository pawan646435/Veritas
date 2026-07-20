"""The complete pipeline, live: generate, run, judge, report.

Not part of the pytest suite: hits the real Groq API many times.

Usage: python scripts/try_full_report.py
"""

import os

from app.agents.finance_agent import FinanceAgent
from app.services.judges import JudgePanel
from app.services.reporter import Reporter
from app.services.test_generator import TestGenerator
from app.services.test_runner import TestRunner


def main() -> None:
    print("Generating test cases...")
    test_cases = TestGenerator().generate(n=10)

    print(f"Running {len(test_cases)} test cases against the finance agent...")
    runner = TestRunner(target_agent=FinanceAgent())
    transcripts = runner.run_batch(test_cases)

    print(f"Judging {len(transcripts)} transcripts...")
    panel = JudgePanel()
    results = [panel.evaluate(t) for t in transcripts]

    reporter = Reporter(results)
    print("\n" + reporter.summary())

    print("\nWorst offenders:")
    print(reporter.worst_offenders(n=3).to_string(index=False))

    os.makedirs("reports", exist_ok=True)
    reporter.export_csv("reports/audit_report.csv")
    print("\nFull results saved to reports/audit_report.csv")


if __name__ == "__main__":
    main()
