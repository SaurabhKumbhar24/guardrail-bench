"""fluiq.secure() — the input-side scanner.

A different component from the one entered in the output benchmark. This is
`routes/secure/scanners.py:check()`, the tiered pattern matcher that runs on the
fast path of `/secure/check`: STRONG phrases block on their own, WEAK ones need
corroboration, and everything is boundary-anchored so "guidance" does not match
"dan".

Blocks when the verdict says block. Note that `check()` deliberately allows
MEDIUM and LOW risk through on the fast path, because the fuller worker scan
weighs in afterwards in production. On this benchmark there is no second stage,
so a MEDIUM the route layer would have escalated is scored as a miss. That is
the honest reading of a single-shot question and it costs us recall.
"""
import importlib.util
import os
import sys
from pathlib import Path

from .base import Verdict

_CANDIDATES = [
    Path(os.environ.get("FLUIQ_API_PATH", "")) / "routes" / "secure" / "scanners.py",
    Path(__file__).resolve().parents[2] / "source" / "fluiq-api" / "routes" / "secure" / "scanners.py",
]


def _load():
    for p in _CANDIDATES:
        try:
            if p and p.is_file():
                spec = importlib.util.spec_from_file_location("_fluiq_in_scanners", p)
                mod = importlib.util.module_from_spec(spec)
                sys.modules["_fluiq_in_scanners"] = mod
                spec.loader.exec_module(mod)
                return mod
        except Exception:
            continue
    raise RuntimeError("Could not locate routes/secure/scanners.py; set FLUIQ_API_PATH")


class FluiqInputGate:
    name = "fluiq.secure (input)"
    version = "scanners.check@2026-08-07"

    def __init__(self) -> None:
        self._mod = _load()

    def scan(self, text: str) -> Verdict:
        try:
            r = self._mod.check(text)
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"{type(exc).__name__}: {exc}")
        return Verdict(blocked=not r.allow, findings=list(r.attack_types))
