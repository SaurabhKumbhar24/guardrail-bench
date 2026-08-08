"""LLM Guard — the `PromptInjection` input scanner.

A fine-tuned DeBERTa classifier rather than a pattern list, which makes it the
most interesting contestant on these corpora: the injection and jailbreak sets
are exactly the kind of paraphrase-heavy material patterns struggle with.

Entered separately from the `Sensitive`/`Secrets` combination used in the output
benchmark, because it is a different scanner answering a different question, and
merging them into one "llm-guard" score would hide which half was doing the work.

Stock threshold. First construction downloads the model (~700MB).
"""
from .base import Verdict


class LLMGuardInjectionGate:
    name = "llm-guard (injection)"
    version = "PromptInjection v2"

    def __init__(self) -> None:
        from llm_guard.input_scanners import PromptInjection

        self._scanner = PromptInjection()
        # Prove it runs before scoring; a model download failure otherwise looks
        # like a contestant that misses everything.
        self._scanner.scan("ping")

    def scan(self, text: str) -> Verdict:
        try:
            _, valid, score = self._scanner.scan(text)
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"{type(exc).__name__}: {exc}")
        return Verdict(blocked=not valid, findings=[f"injection:{score:.2f}"] if not valid else [])
