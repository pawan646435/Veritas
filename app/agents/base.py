from typing import Protocol

from app.schemas.models import AgentResponse


class TargetAgent(Protocol):
    """The structural contract any agent must satisfy to be auditable.

    This is a typing.Protocol, not an abstract base class — deliberately.
    An ABC would require every target agent to inherit from a Veritas base
    class. A Protocol just requires the right *shape*: any object with an
    `answer(question: str) -> AgentResponse` method satisfies this
    interface automatically, with no inheritance at all.

    Why this matters concretely: later, you'll want to point Veritas at
    AlphaMatrix's real assistant class. That class already exists, already
    has its own responsibilities, and shouldn't need to inherit from a
    Veritas-specific base just to become testable. Structural typing means
    it just needs to expose the right method signature.
    """

    def answer(self, question: str) -> AgentResponse: ...
