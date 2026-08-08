"""fluiq.secure() worker `check()` — the fast pre-call path, post-change.

Distinct from `fluiq.secure (worker input)`, which measures the full `scan()`.
This is the cheap path a caller hits on `/secure/check`, and the one the
semantic promotion was aimed at.
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


class FluiqWorkerCheckGate:
    name = "fluiq.secure (worker check)"
    version = "worker check()+semantic_v2@2026-08-07"

    def scan(self, text: str) -> Verdict:
        try:
            r = _w.check(text)
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"{type(exc).__name__}: {exc}")
        return Verdict(blocked=not r.allow, findings=list(r.attack_types))
