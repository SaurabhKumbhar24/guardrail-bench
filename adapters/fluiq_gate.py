"""fluiq.secure() — the response-side scanner.

This is our own entry. It is vendored here as a single file, at a pinned commit,
so the benchmark stays runnable by anyone without installing Fluiq or holding an
account. Keeping it verbatim rather than reimplementing it also means we cannot
quietly tune our contestant to the corpus.

Source: fluiq-api/routes/demo/output_scan.py
"""
import importlib.util
import os
import sys
from pathlib import Path

from .base import Verdict

# Resolve against the API repo when it is present, so the vendored copy and the
# shipping code cannot silently drift. Falls back to the vendored file.
_CANDIDATES = [
    Path(os.environ.get("FLUIQ_API_PATH", "")) / "routes" / "demo" / "output_scan.py",
    Path(__file__).resolve().parents[2] / "source" / "fluiq-api" / "routes" / "demo" / "output_scan.py",
    Path(__file__).with_name("_vendored_output_scan.py"),
]


def _load():
    for p in _CANDIDATES:
        try:
            if p and p.is_file():
                spec = importlib.util.spec_from_file_location("_fluiq_output_scan", p)
                mod = importlib.util.module_from_spec(spec)
                sys.modules["_fluiq_output_scan"] = mod
                spec.loader.exec_module(mod)
                return mod, str(p)
        except Exception:
            continue
    raise RuntimeError(
        "Could not locate output_scan.py. Set FLUIQ_API_PATH to the fluiq-api checkout."
    )


class FluiqGate:
    name = "fluiq.secure (lite)"
    version = "2026-08-07"

    def __init__(self) -> None:
        self._mod, self.source_path = _load()

    def scan(self, text: str) -> Verdict:
        try:
            # No canaries: every contestant sees the same text and nothing else.
            # Passing our planted secrets would hand us an unfair oracle.
            r = self._mod.scan_output(text, [])
            return Verdict(blocked=r.blocked, findings=[f.label for f in r.findings])
        except Exception as exc:  # noqa: BLE001
            return Verdict(blocked=False, findings=[], error=f"{type(exc).__name__}: {exc}")
