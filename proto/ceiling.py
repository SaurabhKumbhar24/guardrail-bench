"""How high can this actually go, and what would it cost?

Reconstructs each guardrail's per-case predictions from the committed results
(they record every miss and every false alarm by case ID), then asks three
questions the roadmap depends on:

1. **Union ceiling** — if a perfect router picked the right detector for every
   case, what recall is on the table? That bounds any ensemble built from these
   parts. If the ceiling is below target, no amount of combining gets there and
   the answer has to be a better detector, not a cleverer combination.

2. **Pairwise ensembles** — which combinations are actually complementary rather
   than redundant, and what false-alarm rate does each cost?

3. **Oracle vs achievable** — the gap between the two is what a learned
   combiner could theoretically recover.

    python proto/ceiling.py
"""
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CORPORA = [
    ("prompt injection", "results_injection.json", "injection.jsonl"),
    ("prompt injection (english only)", "results_injection_en.json", "injection_en.jsonl"),
    ("jailbreak", "results_jailbreak.json", "jailbreak.jsonl"),
]

TARGET = {"prompt injection": 0.85, "prompt injection (english only)": 0.85, "jailbreak": 0.80}


def load(corpus_file, results_file):
    rows = [json.loads(l) for l in
            (ROOT / "corpus" / corpus_file).read_text(encoding="utf-8").split(chr(10)) if l.strip()]
    res = json.loads((ROOT / results_file).read_text(encoding="utf-8"))
    ids = [r["id"] for r in rows]
    truth = {r["id"]: r["expect"] == "block" for r in rows}

    preds = {}
    for name, g in res["guardrails"].items():
        missed, alarms = set(g["missed"]), set(g["false_alarms"])
        # A blockable case is predicted blocked unless it is in `missed`; a
        # benign case is predicted blocked only if it is in `false_alarms`.
        preds[name] = {
            i: (i not in missed) if truth[i] else (i in alarms) for i in ids
        }
    return ids, truth, preds


def score(pred, truth, ids):
    tp = sum(1 for i in ids if pred[i] and truth[i])
    fp = sum(1 for i in ids if pred[i] and not truth[i])
    fn = sum(1 for i in ids if not pred[i] and truth[i])
    tn = sum(1 for i in ids if not pred[i] and not truth[i])
    r = tp / (tp + fn) if tp + fn else 0.0
    fa = fp / (fp + tn) if fp + tn else 0.0
    p = tp / (tp + fp) if tp + fp else 0.0
    return r, fa, (2 * p * r / (p + r) if p + r else 0.0)


def main() -> int:
    for label, rf, cf in CORPORA:
        ids, truth, preds = load(cf, rf)
        names = list(preds)
        tgt = TARGET[label]
        print(f"\n{'='*74}\n{label}  ({len(ids)} cases, target {tgt*100:.0f}% recall)\n{'='*74}")

        print(f"\n{'detector':28} {'recall':>8} {'false alarm':>12} {'F1':>8}")
        for n in sorted(names, key=lambda n: -score(preds[n], truth, ids)[0]):
            r, fa, f1 = score(preds[n], truth, ids)
            print(f"{n:28} {r*100:7.1f}% {fa*100:11.1f}% {f1*100:7.1f}%")

        # Union of everything: the ceiling for any OR-combination.
        allunion = {i: any(preds[n][i] for n in names) for i in ids}
        r, fa, f1 = score(allunion, truth, ids)
        print(f"\n{'UNION of all detectors':28} {r*100:7.1f}% {fa*100:11.1f}% {f1*100:7.1f}%   <- ceiling")

        # What no detector catches at all.
        never = [i for i in ids if truth[i] and not allunion[i]]
        print(f"{'caught by nothing':28} {len(never)} of {sum(truth.values())} attacks")

        # Pairwise, ranked by recall, showing the false-alarm cost.
        print(f"\npairs (OR), best recall first:")
        pairs = []
        for a, b in itertools.combinations(names, 2):
            u = {i: preds[a][i] or preds[b][i] for i in ids}
            pairs.append((score(u, truth, ids), a, b))
        for (r, fa, f1), a, b in sorted(pairs, key=lambda t: -t[0][0])[:6]:
            hit = "  meets target" if r >= tgt else ""
            print(f"  {a} + {b}")
            print(f"      recall {r*100:5.1f}%   false alarm {fa*100:5.1f}%   F1 {f1*100:5.1f}%{hit}")

        # Fluiq-anchored: what does adding one other detector to ours buy?
        ours = next((n for n in names if n.startswith("fluiq")), None)
        if ours:
            print(f"\nadding one detector to {ours}:")
            base_r, base_fa, _ = score(preds[ours], truth, ids)
            print(f"  {'(alone)':34} recall {base_r*100:5.1f}%   false alarm {base_fa*100:5.1f}%")
            for n in names:
                if n == ours:
                    continue
                u = {i: preds[ours][i] or preds[n][i] for i in ids}
                r, fa, f1 = score(u, truth, ids)
                print(f"  + {n:32} recall {r*100:5.1f}% (+{(r-base_r)*100:4.1f})   "
                      f"false alarm {fa*100:5.1f}% (+{(fa-base_fa)*100:4.1f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
