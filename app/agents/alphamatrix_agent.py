import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import LLMCallError
from app.core.logging import get_logger
from app.schemas.models import AgentResponse, ToolCall

logger = get_logger(__name__)

ALPHAMATRIX_CHAT_URL = "https://alphamatrixbackend.vercel.app/api/v1/stocks/chat"


class AlphaMatrixAgent:
    """Adapter that lets Veritas audit AlphaMatrix's real, deployed chat
    assistant — satisfying the exact same TargetAgent Protocol as
    FinanceAgent (Phase 1). This is the concrete payoff of that design
    decision: TestRunner, the judges, and the reporter need zero changes
    to work against this completely different, real production system.

    AlphaMatrix's API needs a `symbol` (ticker) alongside the natural
    language `message`, unlike our own finance agent, which infers the
    ticker from the question text itself. We accept a symbol at
    construction time — when it's left blank, that itself becomes a
    meaningful test case: does the real assistant handle a missing
    symbol gracefully, or does it break?
    """

    def __init__(self, symbol: str = "") -> None:
        self._symbol = symbol
        self._client = httpx.Client(timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    def _call_api(self, question: str) -> dict:
        try:
            response = self._client.post(
                ALPHAMATRIX_CHAT_URL,
                json={"message": question, "symbol": self._symbol, "history": []},
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error(f"AlphaMatrix API call failed: {exc}")
            raise LLMCallError(str(exc)) from exc

    def answer(self, question: str) -> AgentResponse:
        data = self._call_api(question)

        # AlphaMatrix's "sources" list is the closest analog to our own
        # tool_calls — evidence of what the assistant actually referenced,
        # even though it's a flatter shape (names only, not full
        # tool_name/arguments/result triples). Representing it as one
        # synthetic ToolCall lets the existing judges reason about
        # groundedness without any changes to the judges themselves.
        sources = data.get("sources", [])
        tool_calls = [
            ToolCall(
                tool_name="alphamatrix_lookup",
                arguments={"symbol": self._symbol},
                result=", ".join(sources) if sources else "no sources returned",
            )
        ]

        return AgentResponse(tool_calls=tool_calls, final_answer=data.get("response", ""))
