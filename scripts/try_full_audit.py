"""The full pipeline, live, for the first time: generate test cases, run
them against the finance agent, judge every transcript.

Not part of the pytest suite: hits the real Groq API many times (roughly
4 calls per test case — 1-2 for the agent, 3 for the judges).

Usage: python scripts/try_full_audit.py
"""

from app.agents.finance_agent import FinanceAgent
from app.services.judges import JudgePanel
from app.services.test_generator import TestGenerator
from app.services.test_runner import TestRunner


def main() -> None:
    print("Generating test cases...")
    test_cases = TestGenerator().generate(n=6)

    print(f"Running {len(test_cases)} test cases against the finance agent...")
    runner = TestRunner(target_agent=FinanceAgent())
    transcripts = runner.run_batch(test_cases)

    print(f"Judging {len(transcripts)} transcripts...\n")
    panel = JudgePanel()

    for t in transcripts:
        result = panel.evaluate(t)
        print(f"[{t.test_case.category.value}] {t.test_case.question}")
        print(f"  answer: {t.final_answer}")
        for verdict in result.verdicts:
            status = "PASS" if verdict.passed else "FAIL"
            print(f"  [{verdict.judge_name}] {status} ({verdict.score:.2f}) — {verdict.reasoning}")
        print()


if __name__ == "__main__":
    main()
