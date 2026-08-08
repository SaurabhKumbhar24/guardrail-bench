"""fluiq.secure() — the production response gate.

This is the path that actually runs in Fluiq: the security worker's full
post-call scan (Presidio-backed PII, secret scanning, injection/jailbreak
tiering, and a semantic RAG-poisoning score). It is a heavier and more capable
thing than the lightweight inline scanner the marketing demo uses, which is
entered separately as `fluiq.secure (lite)` so the two are never confused.

Needs the fluiq-workers checkout. Point FLUIQ_WORKER_PATH at it, or leave it and
the sibling layout is assumed.
"""
import os
import sys
from pathlib import Path

from .base import Verdict

_DEFAULT = Path(__file__).resolve().parents[2] / "source" / "fluiq-workers" / "security"
_ROOT = Path(os.environ.get("FLUIQ_WORKER_PATH", str(_DEFAULT)))

# The worker's modules import each other as `jobs.helper.*`, so its own root has
# to be on the path rather than importing files individually.
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from jobs.helper import scanners as _worker_scanners  # noqa: E402


class FluiqWorkerGate:
    name = "fluiq.secure"
    version = "worker@2026-08-07"

    def __init__(self) -> None:
        self.semantic = getattr(
            __import__("jobs.helper.semantic", fromlist=["_ST_OK"]), "_ST_OK", False
        )

    def scan(self, text: str) -> Verdict:
        """Scan a model *response*.

        The worker's `scan()` takes a prompt/response pair; the benchmark only
        judges output, so the prompt is left empty. Every contestant sees the
        same single string.
        """
        try:
            r = _worker_scanners.scan(prompt="", response=text)
        except TypeError:
            # Signature drift between worker versions — surface it rather than
            # guessing, so a wrong call can never be scored as a clean miss.
            try:
                r = _worker_scanners.scan("", text)
            except Exception as exc:  # noqa: BLE001
                return Verdict(False, [], f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"{type(exc).__name__}: {exc}")

        findings: list[str] = []
        for attr in (
            "pii_entities_response", "pii_entities_prompt", "secret_types",
            "injection_patterns", "jailbreak_patterns", "tool_exfiltration_types",
        ):
            v = getattr(r, attr, None)
            if v:
                findings.extend(v if isinstance(v, (list, tuple)) else [str(v)])

        blocked = bool(getattr(r, "should_block", False)) or bool(findings)
        return Verdict(blocked=blocked, findings=[str(f) for f in findings][:8])
