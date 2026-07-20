from app.agents.base import TargetAgent
from app.core.exceptions import TargetAgentError, VeritasError
from app.core.logging import get_logger
from app.schemas.models import TestCase, Transcript

logger = get_logger(__name__)


class TestRunner:
    """Executes test cases against a target agent and assembles transcripts.

    This is the connective layer between the test generator (Phase 2) and
    the judges (Phase 4) — it doesn't know how to invent questions or how
    to grade answers, only how to run one question against a TargetAgent
    and faithfully record what happened.

    Notice the constructor takes a `TargetAgent` (the Protocol from Phase
    1), not a `FinanceAgent` specifically. This is where that decision pays
    off directly: `TestRunner(target_agent=finance_agent)` today,
    `TestRunner(target_agent=alphamatrix_assistant)` later — zero changes
    to this class either way.
    """

    def __init__(self, target_agent: TargetAgent) -> None:
        self._target_agent = target_agent

    def run_one(self, test_case: TestCase) -> Transcript:
        """Run a single test case. Raises on failure — callers decide
        whether that's fatal (run_one) or recoverable (run_batch)."""
        try:
            response = self._target_agent.answer(test_case.question)
        except VeritasError:
            # Our own typed errors (e.g. LLMCallError from inside the
            # agent) already carry useful information — let them propagate
            # as-is instead of masking them in a generic wrapper.
            raise
        except Exception as exc:
            raise TargetAgentError(f"Target agent raised an unexpected error: {exc}") from exc

        return Transcript(
            test_case=test_case,
            tool_calls=response.tool_calls,
            final_answer=response.final_answer,
        )

    def run_batch(self, test_cases: list[TestCase]) -> list[Transcript]:
        """Run many test cases. One failing case is logged and skipped —
        it does not abort the rest of the batch."""
        transcripts: list[Transcript] = []
        for test_case in test_cases:
            try:
                transcripts.append(self.run_one(test_case))
            except VeritasError as exc:
                logger.warning(f"Skipping test case {test_case.id} after error: {exc}")

        logger.info(f"Ran {len(transcripts)}/{len(test_cases)} test cases successfully")
        return transcripts
