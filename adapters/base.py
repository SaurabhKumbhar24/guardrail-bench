"""Adapter interface.

A guardrail adapter is any object with a ``name``, a ``version`` and a
``scan(text) -> Verdict``. That is the whole contract — if you want to add a
contestant, copy the regex baseline and change one method.

Adapters are asked a single question: *would you let this model output reach a
user?* Not "is this toxic", not "is the prompt an attack". Output side only.
"""
from dataclasses import dataclass, field
from typing import List, Protocol


@dataclass
class Verdict:
    blocked: bool
    # Free-form detector names, for the per-finding breakdown. Never scored —
    # different products name the same thing differently and normalising them
    # would mean us deciding what a competitor "meant".
    findings: List[str] = field(default_factory=list)
    error: str | None = None


class Guardrail(Protocol):
    name: str
    version: str

    def scan(self, text: str) -> Verdict: ...
