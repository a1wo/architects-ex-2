"""Strategy interface: every chatbot strategy answers a question and reports
its evidence. The UI and the /ask contract endpoint are strategy-agnostic —
they only speak these types.
"""

from dataclasses import dataclass, field


@dataclass
class Citation:
    file: str
    page: int | None = None
    quote: str | None = None


@dataclass
class Context:
    """A retrieved chunk, for the UI debug panel."""
    file: str
    page: int | None
    domain: str
    text: str
    distance: float


@dataclass
class StrategyResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    contexts: list[Context] = field(default_factory=list)
    domain: str | None = None
    model: str | None = None
    cost_usd: float | None = None
    latency_ms: float | None = None


class Strategy:
    """Subclass and register in strategies/__init__.py.

    name:        stable id (used by the UI and API)
    description: one-liner shown in the UI picker
    params:      {param_name: {"default": v, "min": ..., "max": ..., "label": ...}}
                 — rendered generically as UI controls, passed to ask() as kwargs.
                 Optional "type": "select" (+ "options": [...]) or "bool";
                 default is a number input.

    ask() may accept an optional progress=callable kwarg; call it with a short
    stage name ("retrieve", "generate", ...) when entering each stage — the
    streaming endpoint forwards these to the UI debug panel. Each mark closes
    the previous stage, so no explicit "done" calls are needed.
    """

    name: str = "base"
    description: str = ""
    params: dict = {}

    def ask(self, question: str, history: list[dict] | None = None,
            **params) -> StrategyResult:
        raise NotImplementedError
