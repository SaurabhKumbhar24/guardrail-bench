"""Measure semantic_v2 as it would actually run: patterns OR semantic_verdict().

Uses the shipping pattern scanner and the prototype module's own default
thresholds - no tuning here at all, so this is the number a deployment would
get on day one.
"""
import importlib.util, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(os.environ.get("FLUIQ_WORKER_PATH",
              str(ROOT.parent / "source" / "fluiq-workers" / "security")))
sys.path.insert(0, str(WORKER))

from jobs.helper import semantic_v2 as v2  # noqa: E402


def pattern_gate():
    p = Path(os.environ["FLUIQ_API_PATH"]) / "routes" / "secure" / "scanners.py"
    spec = importlib.util.spec_from_file_location("_pat", p)
    m = importlib.util.module_from_spec(spec)
    sys.modules["_pat"] = m
    spec.loader.exec_module(m)
    return lambda t: not m.check(t).allow


def load(name):
    return [json.loads(l) for l in
            (ROOT / "corpus" / name).read_text(encoding="utf-8").split(chr(10)) if l.strip()]


def stats(pred, ys):
    tp = sum(1 for p, y in zip(pred, ys) if p and y)
    fp = sum(1 for p, y in zip(pred, ys) if p and not y)
    fn = sum(1 for p, y in zip(pred, ys) if not p and y)
    tn = sum(1 for p, y in zip(pred, ys) if not p and not y)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    fa = fp / (fp + tn) if fp + tn else 0.0
    return (2 * prec * rec / (prec + rec) if prec + rec else 0.0), rec, fa


pat = pattern_gate()
print(f"injection model : {v2.MODEL_INJECTION} @ {v2.THRESHOLD_INJECTION}")
print(f"jailbreak model : {v2.MODEL_JAILBREAK} @ {v2.THRESHOLD_JAILBREAK}\n")
print(f"{'corpus':16} {'config':28} {'recall':>8} {'false alarm':>12} {'F1':>8}")

for corpus in ("injection_test.jsonl", "jailbreak_test.jsonl"):
    rows = load(corpus)
    ys = [r["expect"] == "block" for r in rows]
    pp = [pat(r["text"]) for r in rows]
    vv = [v2.semantic_verdict(r["text"])[0] for r in rows]
    name = corpus.replace("_test.jsonl", "")
    for label, pred in (("patterns only (shipping)", pp),
                        ("patterns OR semantic_v2", [a or b for a, b in zip(pp, vv)])):
        f1, r, fa = stats(pred, ys)
        print(f"{name:16} {label:28} {r*100:7.1f}% {fa*100:11.1f}% {f1*100:7.1f}%")
