"""fluiq.secure() worker scan, with the corpus text as the *prompt*.

The `fluiq.secure (input)` entry measures the API fast path (`routes/secure/
scanners.py:check`). This one measures the full worker scan on the same text,
which additionally runs the semantic attack-similarity score. The difference
between the two is how much the semantic layer is actually buying.
"""
import os
import sys
from pathlib import Path

from .base import Verdict

_DEFAULT = Path(__file__).resolve().parents[2] / "source" / "fluiq-workers" / "security"
_ROOT = Path(os.environ.get("FLUIQ_WORKER_PATH", str(_DEFAULT)))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from jobs.helper import scanners as _w  # noqa: E402


class FluiqWorkerInputGate:
    name = "fluiq.secure (worker input)"
    version = "worker scan(prompt=)@2026-08-07"

    def scan(self, text: str) -> Verdict:
        try:
            r = _w.scan(prompt=text, response="")
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"{type(exc).__name__}: {exc}")
        f = []
        for a in ("injection_patterns", "jailbreak_patterns", "skeleton_key_patterns"):
            v = getattr(r, a, None)
            if v:
                f.extend(v)
        blocked = bool(
            getattr(r, "injection_detected", False)
            or getattr(r, "jailbreak_detected", False)
            or getattr(r, "skeleton_key_detected", False)
            or getattr(r, "should_block", False)
        )
        return Verdict(blocked=blocked, findings=[str(x) for x in f][:6])
