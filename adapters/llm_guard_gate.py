"""LLM Guard (ProtectAI / Palo Alto) — the most widely used OSS guardrail toolkit.

Config note, because it affects the score: LLM Guard splits scanners into input
and output sets. `Sensitive` is the documented output scanner and covers PII.
`Secrets` is classified as an *input* scanner, but it runs fine on arbitrary
text, and a team trying to stop key leakage would obviously point it at
responses too. Both are enabled here.

That is a deliberately generous reading. Scoring LLM Guard on `Sensitive` alone
would zero it out on every secret case on a technicality about which list a
scanner is filed under, and a vendor-published benchmark should not win that way.
Both run at stock thresholds; nothing is tuned to this corpus.
"""
from .base import Verdict


class LLMGuardGate:
    name = "llm-guard"
    version = "output:Sensitive + input:Secrets"

    def __init__(self) -> None:
        from llm_guard.input_scanners import Secrets
        from llm_guard.output_scanners import Sensitive

        self._secrets = Secrets()
        self._sensitive = Sensitive()

    def scan(self, text: str) -> Verdict:
        findings: list[str] = []
        blocked = False
        try:
            _, ok, _ = self._secrets.scan(text)
            if not ok:
                blocked = True
                findings.append("secrets")
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"secrets: {type(exc).__name__}: {exc}")

        try:
            # Sensitive is an output scanner: (prompt, output). Prompt is empty
            # so every contestant sees exactly the same single string.
            _, ok, _ = self._sensitive.scan("", text)
            if not ok:
                blocked = True
                findings.append("sensitive")
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"sensitive: {type(exc).__name__}: {exc}")

        return Verdict(blocked=blocked, findings=findings)
