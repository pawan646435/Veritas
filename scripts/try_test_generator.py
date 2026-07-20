"""Manual smoke test — run this yourself to see real generated test cases.

Not part of the pytest suite: hits the real Groq API. Use it to see what
kinds of adversarial questions the model actually invents.

Usage: python scripts/try_test_generator.py
"""

from app.services.test_generator import TestGenerator


def main() -> None:
    generator = TestGenerator()
    cases = generator.generate(n=10)

    for case in cases:
        print(f"\n[{case.category.value}] {case.question}")
        print(f"  note: {case.notes}")


if __name__ == "__main__":
    main()
