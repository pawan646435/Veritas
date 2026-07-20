"""Manual smoke test — the first end-to-end run: generate cases, run them
against the real finance agent, print each transcript.

Not part of the pytest suite: hits the real Groq API multiple times.

Usage: python scripts/try_full_pipeline.py
"""

from app.agents.finance_agent import FinanceAgent
from app.services.test_generator import TestGenerator
from app.services.test_runner import TestRunner


def main() -> None:
    print("Generating test cases...")
    test_cases = TestGenerator().generate(n=6)

    print(f"Running {len(test_cases)} test cases against the finance agent...\n")
    runner = TestRunner(target_agent=FinanceAgent())
    transcripts = runner.run_batch(test_cases)

    for t in transcripts:
        print(f"[{t.test_case.category.value}] {t.test_case.question}")
        for call in t.tool_calls:
            print(f"  [tool call] {call.tool_name}({call.arguments}) -> {call.result}")
        print(f"  answer: {t.final_answer}\n")


if __name__ == "__main__":
    main()
