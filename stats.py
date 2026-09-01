"""Confidence intervals and pairwise significance for the benchmark results.

A ranked table invites the reader to believe the order means something. On a
49-case corpus, the gap between first and second place is three cases, which is
well inside the noise. This module computes how much of each ranking survives
contact with the sample size.

    python stats.py

Two choices worth arguing with:

**McNemar's exact test, not a two-proportion z-test.** Every guardrail is handed
the identical case list, so the outcomes are paired. A z-test assumes
independent samples and would throw away the pairing, which is the most
informative thing in the design: what matters is not how many each side got
right, but the cases where the two disagree. McNemar looks only at those
discordant pairs. Exact binomial rather than the chi-square approximation
because the discordant counts here are frequently under 25.

**Wilson intervals, not normal approximation.** At n=49 with proportions near
0.9 the normal approximation produces upper bounds above 100%, which is not a
confidence interval so much as an advertisement.

Correctness is scored per case as "the guardrail did the right thing": it
blocked what should be blocked and allowed what should be allowed. That single
per-case boolean is what the pairing needs, and it is the same quantity the F1
column summarises.
"""
import json
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent

Z_95 = 1.96
ALPHA = 0.05


def wilson(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials, as percentages."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (max(0.0, centre - half) * 100, min(1.0, centre + half) * 100)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact binomial p-value on the discordant pairs.

    `b` is the count of cases the first guardrail got right and the second got
    wrong, `c` the reverse. Concordant cases carry no information about which is
    better and are deliberately not counted.
    """
    n = b + c
    if n == 0:
        return 1.0
    lo = min(b, c)
    tail = sum(comb(n, i) for i in range(lo + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def load_expect(corpus_name: str) -> dict[str, str]:
    """Case ID to expected verdict.

    Falls back to the manifest when the corpus itself is absent, so this works
    on a fresh clone where a corpus we cannot redistribute has not been rebuilt
    yet (see corpus/SOURCES.md). The manifest carries the label for exactly this
    reason.
    """
    p = ROOT / "corpus" / corpus_name
    if p.exists():
        # split("\n"), never splitlines(): see the comment in verify_corpus.py.
        return {
            r["id"]: r["expect"]
            for r in (json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip())
        }
    m = p.with_suffix(".manifest.json")
    if m.exists():
        return {r["id"]: r["expect"] for r in json.loads(m.read_text(encoding="utf-8"))["rows"]}
    return {}


def case_correct(guardrail: dict, expect: dict[str, str]) -> dict[str, bool]:
    """Per-case "did the right thing", from the missed and false-alarm lists."""
    wrong = set(guardrail["missed"]) | set(guardrail["false_alarms"])
    return {case_id: case_id not in wrong for case_id in expect}


def intervals(guardrail: dict, expect: dict[str, str]) -> dict:
    """Wilson intervals for recall and false-alarm rate."""
    pos = [i for i, e in expect.items() if e == "block"]
    neg = [i for i, e in expect.items() if e == "allow"]
    caught = len(pos) - len(set(guardrail["missed"]) & set(pos))
    alarms = len(set(guardrail["false_alarms"]) & set(neg))
    return {
        "recall_ci": wilson(caught, len(pos)),
        "fa_ci": wilson(alarms, len(neg)),
        "n_block": len(pos),
        "n_allow": len(neg),
    }


def pairwise(guardrails: dict[str, dict], expect: dict[str, str], order: list[str]) -> list[dict]:
    """Every pair, in ranked order, with its McNemar result."""
    correct = {n: case_correct(guardrails[n], expect) for n in order}
    out = []
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            a, b_name = order[i], order[j]
            b = sum(1 for k in expect if correct[a][k] and not correct[b_name][k])
            c = sum(1 for k in expect if not correct[a][k] and correct[b_name][k])
            p = mcnemar_exact(b, c)
            out.append({
                "a": a, "b": b_name, "b_count": b, "c_count": c,
                "p": p, "distinguishable": p < ALPHA,
            })
    return out


def indistinguishable(pairs: list[dict]) -> list[dict]:
    return [p for p in pairs if not p["distinguishable"]]


def main() -> int:
    from make_report import CORPORA, DISPLAY, SECONDARY, load_results

    for c in CORPORA:
        res = load_results(c["results"])
        expect = load_expect(c["corpus"])
        if not res or not expect:
            print(f"\n### {c['title']}: skipped, no results or corpus labels available")
            continue

        g = {k: v for k, v in res["guardrails"].items() if k not in SECONDARY}
        order = [k for k, _ in sorted(g.items(), key=lambda kv: -kv[1]["f1"])]
        n_block = sum(1 for e in expect.values() if e == "block")

        print(f"\n{'=' * 74}")
        print(f"{c['title']}  (n={len(expect)}: {n_block} block / {len(expect) - n_block} allow)")
        print('=' * 74)
        print(f"{'guardrail':<24}{'recall':>8} {'95% CI':>15}  {'false alarm':>12} {'95% CI':>15}")
        for name in order:
            iv = intervals(g[name], expect)
            print(f"{DISPLAY.get(name, name):<24}{g[name]['recall'] * 100:7.1f}% "
                  f"[{iv['recall_ci'][0]:5.1f},{iv['recall_ci'][1]:5.1f}]  "
                  f"{g[name]['false_alarm_rate'] * 100:11.1f}% "
                  f"[{iv['fa_ci'][0]:5.1f},{iv['fa_ci'][1]:5.1f}]")

        pairs = pairwise(g, expect, order)
        same = indistinguishable(pairs)
        print(f"\n  McNemar exact: {len(pairs) - len(same)} of {len(pairs)} pairs separable "
              f"at p < {ALPHA}.")
        if same:
            print("  The data cannot separate:")
            for p in same:
                print(f"    {DISPLAY.get(p['a'], p['a'])} vs {DISPLAY.get(p['b'], p['b'])}"
                      f"  (b={p['b_count']}, c={p['c_count']}, p={p['p']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
