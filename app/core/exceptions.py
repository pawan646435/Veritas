class VeritasError(Exception):
    """Base class for every error raised by Veritas itself.

    Catching `VeritasError` in calling code means "something in our own
    pipeline broke" — distinct from catching bare `Exception`, which would
    also swallow real bugs (typos, KeyErrors) you actually want to crash on.
    """


class LLMCallError(VeritasError):
    """Raised when a call to the LLM provider fails even after retries."""


class TargetAgentError(VeritasError):
    """Raised when the target agent fails to produce a usable response."""


class JudgeError(VeritasError):
    """Raised when a judge fails to produce a valid, parseable verdict."""


class TestGenerationError(VeritasError):
    """Raised when the test generator produces JSON that can't be parsed
    into valid TestCase objects at all (not to be confused with a single
    malformed test case, which we skip and log instead of raising)."""
