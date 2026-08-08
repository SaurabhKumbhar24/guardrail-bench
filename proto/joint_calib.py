"""Joint threshold calibration.

Both scopes score every prompt in production, so a threshold tuned on its own
corpus understates the false alarms it causes on the other. This sweeps the pair
(T_injection, T_jailbreak) against the *combined* dev set and picks the pair with
the best combined recall inside a false-alarm budget.
"""
import importlib.util, json, os, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(os.environ.get("FLUIQ_WORKER_PATH",
              str(ROOT.parent / "source" / "fluiq-workers" / "security")))
sys.path.insert(0, str(WORKER))
from jobs.helper import semantic_v2 as v2  # noqa: E402

BUDGET = float(os.environ.get("FA_BUDGET", "0.05"))


def pattern_gate():
    p = Path(os.environ["FLUIQ_API_PATH"]) / "routes" / "secure" / "scanners.py"
    spec = importlib.util.spec_from_file_location("_pat", p)
    m = importlib.util.module_from_spec(spec); sys.modules["_pat"] = m
    spec.loader.exec_module(m)
    return lambda t: not m.check(t).allow


def load(n):
    return [json.loads(l) for l in
            (ROOT / "corpus" / n).read_text(encoding="utf-8").split(chr(10)) if l.strip()]


pat = pattern_gate()

def prep(names):
    txt, ys = [], []
    for n in names:
        for r in load(n):
            txt.append(r["text"]); ys.append(r["expect"] == "block")
    ys = np.array(ys)
    pp = np.array([pat(t) for t in txt])
    si = np.array([v2.injection_score(t) for t in txt])
    sj = np.array([v2.jailbreak_score(t) for t in txt])
    return pp, si, sj, ys

# The false-positive regression cases go in the DEV set, not just the report.
# Thresholds have to be chosen with them present or nothing stops the semantic
# layer re-flagging exactly the benign phrasings the July audit fixed.
dev  = prep(["injection_dev.jsonl",  "jailbreak_dev.jsonl", "fp_audit.jsonl"])
test = prep(["injection_test.jsonl", "jailbreak_test.jsonl"])

def score(pp, si, sj, ys, ti, tj):
    pred = pp | (si >= ti) | (sj >= tj)
    tp = int((pred & ys).sum()); fp = int((pred & ~ys).sum()); fn = int((~pred & ys).sum())
    p = tp/(tp+fp) if tp+fp else 0.0
    r = tp/(tp+fn) if tp+fn else 0.0
    fa = fp/int((~ys).sum())
    return (2*p*r/(p+r) if p+r else 0.0), r, fa

# Hard constraint: no FP-audit benign case may be blocked, at any recall.
fp = prep(["fp_audit.jsonl"])
fp_benign = ~fp[3]

best = None
for ti in np.arange(0.15, 0.85, 0.01):
    for tj in np.arange(0.15, 0.85, 0.01):
        fpred = fp[0] | (fp[1] >= ti) | (fp[2] >= tj)
        if (fpred & fp_benign).any():
            continue  # would re-break a fixed false positive
        _, r, fa = score(*dev, float(ti), float(tj))
        if fa <= BUDGET and (best is None or r > best[0]):
            best = (r, float(ti), float(tj))

print(f"combined dev FA budget: {BUDGET*100:.0f}%")
if not best:
    print("no threshold pair meets the budget"); raise SystemExit(1)
_, ti, tj = best
print(f"chosen on dev: injection>={ti:.2f}  jailbreak>={tj:.2f}\n")
print(f"{'split':6} {'config':26} {'recall':>8} {'false alarm':>12} {'F1':>8}")
for label, d in (("dev", dev), ("test", test)):
    f1, r, fa = score(*d, 0.0, 0.0) if False else score(d[0], d[1]*0, d[2]*0, d[3], 9, 9)
    print(f"{label:6} {'patterns only':26} {r*100:7.1f}% {fa*100:11.1f}% {f1*100:7.1f}%")
    f1, r, fa = score(*d, ti, tj)
    print(f"{label:6} {'patterns OR semantic_v2':26} {r*100:7.1f}% {fa*100:11.1f}% {f1*100:7.1f}%")
