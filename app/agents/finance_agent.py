import json
from typing import Any, cast

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.mock_stock_data import get_stock_data
from app.core.config import settings
from app.core.exceptions import LLMCallError
from app.core.logging import get_logger
from app.schemas.models import AgentResponse, ToolCall

logger = get_logger(__name__)

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are a financial data assistant. You have access to a get_stock_data "
    "tool that looks up real data for a stock ticker. Only state facts that "
    "came from the tool's output — never invent a number. If the tool returns "
    "no data for a ticker, say clearly that you don't have data for it, "
    "instead of guessing."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_data",
            "description": (
                "Look up price, P/E ratio, market cap, sector, and 52-week "
                "range for a stock ticker."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol, e.g. INFY, TCS, RELIANCE",
                    }
                },
                "required": ["ticker"],
            },
        },
    }
]


class FinanceAgent:
    """A small finance Q&A agent — the first target Veritas audits.

    Deliberately minimal: one tool, no memory across questions, no
    retrieval pipeline. The interesting engineering in this project is the
    auditor, not the thing being audited — this just needs to behave like
    a real tool-using agent, mistakes and all.
    """

    def __init__(self) -> None:
        self._client = Groq(api_key=settings.groq_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    def _call_llm(self, messages: list[dict]):
        try:
            return self._client.chat.completions.create(
                model=MODEL,
                messages=cast(Any, messages),
                tools=cast(Any, TOOLS),
                tool_choice="auto",
            )
        except Exception as exc:
            logger.error(f"Groq call failed: {exc}")
            raise LLMCallError(str(exc)) from exc

    def answer(self, question: str) -> AgentResponse:
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        response = self._call_llm(messages)
        message = response.choices[0].message
        tool_calls: list[ToolCall] = []

        if message.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            )

            for call in message.tool_calls:
                args = json.loads(call.function.arguments)
                ticker = args.get("ticker", "")
                result = get_stock_data(ticker)
                result_str = (
                    json.dumps(result) if result else f"No data found for ticker '{ticker}'"
                )

                tool_calls.append(
                    ToolCall(tool_name=call.function.name, arguments=args, result=result_str)
                )
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result_str}
                )

            final_response = self._call_llm(messages)
            final_answer = final_response.choices[0].message.content
        else:
            final_answer = message.content

        logger.info(f"Answered '{question[:50]}...' with {len(tool_calls)} tool call(s)")
        return AgentResponse(tool_calls=tool_calls, final_answer=final_answer or "")
