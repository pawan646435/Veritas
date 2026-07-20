"""Manual smoke test — run this yourself to see the agent work live.

Not part of the pytest suite: this hits the real Groq API and costs real
(free-tier) tokens, so it shouldn't run automatically on every push. Use it
to sanity-check the agent feels right before moving on.

Usage: python scripts/try_finance_agent.py
"""

from app.agents.finance_agent import FinanceAgent

QUESTIONS = [
    "What is the P/E ratio of Infosys?",
    "What's the 52-week high for Wipro?",  # not in our mock data — watch what it says
    "Compare the market cap of TCS and Reliance.",
]


def main() -> None:
    agent = FinanceAgent()
    for question in QUESTIONS:
        print(f"\nQ: {question}")
        response = agent.answer(question)
        for call in response.tool_calls:
            print(f"  [tool call] {call.tool_name}({call.arguments}) -> {call.result}")
        print(f"A: {response.final_answer}")


if __name__ == "__main__":
    main()
