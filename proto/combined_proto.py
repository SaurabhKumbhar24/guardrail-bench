"""What production would actually do: patterns OR semantic, measured together.

The semantic-only numbers in semantic_proto.py are not deployable on their own —
every variant false-alarms on a quarter to three quarters of benign prompts.
Production's near-zero false-alarm rate comes from the pattern layer. So the real
question is not "which seed set scores best" but "what does the pattern layer
gain from a semantic second opinion, and at what cost".

Blocks when the existing pattern scanner blocks, OR when the semantic score
clears a threshold chosen on dev. Reported against the held-out test split.

    python proto/combined_proto.py [embedding-model]
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from proto.semantic_proto import CURRENT, EXPANDED, FAMILIES, load  # noqa: E402


def pattern_gate():
    """The shipping fast-path scanner, loaded from the API repo."""
    p = Path(os.environ.get("FLUIQ_API_PATH", "")) / "routes" / "secure" / "scanners.py"
    if not p.is_file():
        p = ROOT.parent / "source" / "fluiq-api" / "routes" / "secure" / "scanners.py"
    spec = importlib.util.spec_from_file_location("_pat", p)
    m = importlib.util.module_from_spec(spec)
    # Register before exec: @dataclass resolves annotations via sys.modules, and
    # a module loaded standalone without this fails on the decorator.
    sys.modules["_pat"] = m
    spec.loader.exec_module(m)
    return lambda t: not m.check(t).allow


def centroid(model, seeds):
    e = model.encode(seeds, normalize_embeddings=True, show_progress_bar=False)
    c = np.mean(e, axis=0)
    return c / np.linalg.norm(c)


def stats(pred, ys):
    tp = int((pred & ys).sum()); fp = int((pred & ~ys).sum()); fn = int((~pred & ys).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    fa = fp / int((~ys).sum()) if int((~ys).sum()) else 0.0
    return (2 * p * r / (p + r) if p + r else 0.0), r, fa


def main() -> int:
    model_name = sys.argv[1] if len(sys.argv) > 1 else "all-MiniLM-L6-v2"
    model = SentenceTransformer(model_name)
    pat = pattern_gate()
    print(f"embedding model: {model_name}\n")

    corpora = os.environ.get("BENCH_CORPORA", "injection_en,jailbreak").split(",")
    for corpus in corpora:
        dev, test = load(f"{corpus}_dev.jsonl"), load(f"{corpus}_test.jsonl")
        dt = [r["text"] for r in dev]; tt = [r["text"] for r in test]
        dy = np.array([r["expect"] == "block" for r in dev])
        ty = np.array([r["expect"] == "block" for r in test])
        dp = np.array([pat(t) for t in dt]); tp_ = np.array([pat(t) for t in tt])
        dv = model.encode(dt, normalize_embeddings=True, show_progress_bar=False)
        tv = model.encode(tt, normalize_embeddings=True, show_progress_bar=False)

        print(f"=== {corpus} (test {len(test)}) ===")
        f1, r, fa = stats(tp_, ty)
        print(f"{'patterns only (shipping)':38} {'':>5} {r*100:7.1f}% {fa*100:11.1f}% {f1*100:7.1f}%")

        for label, seeds in (("patterns OR semantic [current seeds]", CURRENT),
                             ("patterns OR semantic [expanded seeds]", EXPANDED)):
            c = centroid(model, seeds)
            ds, ts = dv @ c, tv @ c
            # Threshold on dev. Chosen to maximise F1, but a deployment that
            # cares about false alarms above all would pick the highest
            # threshold that keeps FA under its own budget instead.
            best_t, best = 0.0, -1.0
            for t in np.arange(0.10, 0.90, 0.01):
                f1d, _, _ = stats(dp | (ds >= t), dy)
                if f1d > best:
                    best, best_t = f1d, float(t)
            f1, r, fa = stats(tp_ | (ts >= best_t), ty)
            print(f"{label:38} {best_t:5.2f} {r*100:7.1f}% {fa*100:11.1f}% {f1*100:7.1f}%")

        # Conservative variant: keep false alarms at or below the pattern layer's
        # own rate on dev, then take whatever recall that buys. This is the shape
        # a team that has already done a false-positive audit would actually ship.
        c = centroid(model, EXPANDED)
        ds, ts = dv @ c, tv @ c
        _, _, pat_fa_dev = stats(dp, dy)
        budget = max(pat_fa_dev, 0.02)
        pick = None
        for t in np.arange(0.90, 0.10, -0.01):
            _, _, fad = stats(dp | (ds >= t), dy)
            if fad <= budget:
                pick = float(t)
            else:
                break
        if pick is not None:
            f1, r, fa = stats(tp_ | (ts >= pick), ty)
            print(f"{'  ^ same, FA-budgeted (<=%.0f%% on dev)' % (budget*100):38} "
                  f"{pick:5.2f} {r*100:7.1f}% {fa*100:11.1f}% {f1*100:7.1f}%")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
