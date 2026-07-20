import json

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import JudgeError, LLMCallError, VeritasError
from app.core.logging import get_logger
from app.schemas.models import AuditResult, JudgeVerdict, Transcript

logger = get_logger(__name__)

MODEL = "llama-3.3-70b-versatile"


def _format_transcript(transcript: Transcript) -> str:
    """Render a transcript as plain text a judge LLM can reason about.

    This is the single place every judge gets its view of "what happened" —
    every judge reads the exact same rendering of the same facts, which
    matters because it's what makes their verdicts comparable to each other.
    """
    lines = [f"Question asked: {transcript.test_case.question}"]

    if transcript.tool_calls:
        for call in transcript.tool_calls:
            lines.append(f"Tool call: {call.tool_name}({call.arguments}) -> {call.result}")
    else:
        lines.append("Tool calls: none")

    lines.append(f"Agent's final answer: {transcript.final_answer}")
    return "\n".join(lines)


class BaseJudge:
    """Shared machinery for every LLM-as-judge: one Groq call in JSON mode,
    parsed into a JudgeVerdict. Subclasses supply only a `name` and a
    `system_prompt` — none of them reimplement the call/parse logic, which
    keeps every judge narrow, comparable, and easy to add to later.
    """

    name: str = "base_judge"
    system_prompt: str = ""

    def __init__(self) -> None:
        self._client = Groq(api_key=settings.groq_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    def _call_llm(self, transcript: Transcript) -> str:
        try:
            response = self._client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": _format_transcript(transcript)},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.error(f"{self.name} judge LLM call failed: {exc}")
            raise LLMCallError(str(exc)) from exc

    def evaluate(self, transcript: Transcript) -> JudgeVerdict:
        raw = self._call_llm(transcript)
        try:
            parsed = json.loads(raw)
            return JudgeVerdict(
                judge_name=self.name,
                passed=bool(parsed["passed"]),
                score=float(parsed["score"]),
                reasoning=str(parsed["reasoning"]),
            )
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            raise JudgeError(f"{self.name} returned an unparseable verdict: {exc}") from exc


class GroundednessJudge(BaseJudge):
    """Does every specific fact in the answer trace back to real tool
    output? Correctly admitting 'I don't have that data' counts as
    passing — this judge penalizes fabrication, not honest uncertainty."""

    name = "groundedness"
    system_prompt = (
        "You audit an AI agent's answer for factual grounding. You will see "
        "the question, every tool call the agent made along with the real "
        "data returned, and the agent's final answer.\n\n"
        "Check: does every specific number or fact in the final answer "
        "trace back to the tool results shown? Flag the answer if it states "
        "a number or fact that did not come from a tool result, if it "
        "answers confidently without having called a needed tool, or if it "
        "contradicts the tool data.\n\n"
        "If the agent correctly admitted it lacked the data instead of "
        "inventing an answer, that counts as PASSING, not failing — honest "
        "uncertainty is correct behavior, not a violation.\n\n"
        'Return ONLY JSON: {"passed": bool, "score": float between 0 and 1, '
        '"reasoning": "one or two sentences"}'
    )


class ToolUseJudge(BaseJudge):
    """Did the agent call the right tool, with the right arguments, for
    this question — or fail to call one when it needed to?"""

    name = "tool_use"
    system_prompt = (
        "You audit an AI agent's tool usage. You will see the question, "
        "every tool call the agent made, and its final answer.\n\n"
        "Check: if the question required looking up data, did the agent "
        "call the tool with the correct arguments (e.g. the right ticker)? "
        "If the question did not require a tool (out of scope or purely "
        "conversational), was correctly NOT calling a tool the right "
        "choice? Flag missing calls, wrong arguments, or unnecessary calls.\n\n"
        'Return ONLY JSON: {"passed": bool, "score": float between 0 and 1, '
        '"reasoning": "one or two sentences"}'
    )


class TaskCompletionJudge(BaseJudge):
    """Did the final answer actually address what was asked — separate
    from whether the underlying facts were correct?"""

    name = "task_completion"
    system_prompt = (
        "You audit whether an AI agent's final answer actually addresses "
        "the question asked — independent of whether the facts in it are "
        "correct (a different judge checks that).\n\n"
        "Check: did the agent answer the question, appropriately decline "
        "an out-of-scope request, or ask for clarification on a genuinely "
        "ambiguous question? Flag it if the agent dodged a legitimate "
        "question, answered something else, or gave a non-answer.\n\n"
        'Return ONLY JSON: {"passed": bool, "score": float between 0 and 1, '
        '"reasoning": "one or two sentences"}'
    )


class JudgePanel:
    """Runs every judge against a transcript and assembles the AuditResult.

    A judge failing (malformed JSON even after retries) does not abort the
    whole evaluation — same partial-failure philosophy as the test
    generator and test runner. A transcript with 2 of 3 verdicts is still
    useful; one bad LLM response should not crash an unattended run over
    dozens of test cases.
    """

    def __init__(self, judges: list[BaseJudge] | None = None) -> None:
        self._judges = judges or [GroundednessJudge(), ToolUseJudge(), TaskCompletionJudge()]

    def evaluate(self, transcript: Transcript) -> AuditResult:
        verdicts: list[JudgeVerdict] = []
        for judge in self._judges:
            try:
                verdicts.append(judge.evaluate(transcript))
            except VeritasError as exc:
                logger.warning(
                    f"Judge '{judge.name}' failed on test case "
                    f"{transcript.test_case.id}: {exc}"
                )

        return AuditResult(transcript=transcript, verdicts=verdicts)
