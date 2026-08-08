"""Can the classifier be salvaged by requiring corroboration?

Standalone it re-breaks 6 of 16 false-positive regression cases at p>0.99, so it
cannot be a blocker on its own. This tests three combination rules against both
the public corpora and the FP-audit cases, which are the ones that look like
real support traffic.
"""
import importlib.util, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "source" / "fluiq-workers" / "security"))
from jobs.helper import classifier as cl        # noqa: E402
from jobs.helper import semantic_v2 as v2       # noqa: E402


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
RULES = {
    "patterns + semantic (today)":      lambda P, S, C: P or S,
    "  + classifier standalone":        lambda P, S, C: P or S or C,
    "  + classifier AND semantic":      lambda P, S, C: P or S or (C and S),
    "  + classifier corroborated":      lambda P, S, C: P or S or (C and (P or S)),
    "  + classifier, semantic-assisted": lambda P, S, C: P or S or (C and v2.injection_score.__self__ is None),
}
# The 4th rule reduces to "P or S"; the interesting question is a *lower*
# semantic bar when the classifier agrees. Model that explicitly.
LOW = 0.30


def evaluate(name, rows):
    out = []
    for r in rows:
        t = r["text"]
        P = pat(t)
        si, sj = v2.injection_score(t), v2.jailbreak_score(t)
        S = si >= v2.THRESHOLD_INJECTION or sj >= v2.THRESHOLD_JAILBREAK
        Slow = si >= LOW or sj >= LOW
        C = cl.injection_probability(t) >= 0.90
        out.append((r["expect"] == "block", P, S, Slow, C))

    def stats(pred):
        tp = sum(1 for (y, *_), p in zip(out, pred) if p and y)
        fp = sum(1 for (y, *_), p in zip(out, pred) if p and not y)
        fn = sum(1 for (y, *_), p in zip(out, pred) if not p and y)
        tn = sum(1 for (y, *_), p in zip(out, pred) if not p and not y)
        r = tp / (tp + fn) if tp + fn else 0.0
        fa = fp / (fp + tn) if fp + tn else 0.0
        pr = tp / (tp + fp) if tp + fp else 0.0
        return r, fa, (2 * pr * r / (pr + r) if pr + r else 0.0)

    rules = [
        ("patterns + semantic (today)", [P or S for (_, P, S, Sl, C) in out]),
        ("+ classifier standalone",     [P or S or C for (_, P, S, Sl, C) in out]),
        ("+ classifier AND low semantic", [P or S or (C and Sl) for (_, P, S, Sl, C) in out]),
        ("+ classifier AND pattern",     [P or S or (C and P) for (_, P, S, Sl, C) in out]),
    ]
    print(f"\n=== {name} ({len(rows)} cases) ===")
    print(f"{'rule':34} {'recall':>8} {'false alarm':>12} {'F1':>8}")
    for label, pred in rules:
        r, fa, f1 = stats(pred)
        print(f"{label:34} {r*100:7.1f}% {fa*100:11.1f}% {f1*100:7.1f}%")


evaluate("FP-audit (production-like benign)", load("fp_audit.jsonl"))
evaluate("prompt injection (test split)", load("injection_test.jsonl"))
evaluate("jailbreak (test split)", load("jailbreak_test.jsonl"))
