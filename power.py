"""How many cases would a guardrail benchmark need to resolve its own ranking?

stats.py reports that most pairs in this benchmark are not separable. That is a
complaint unless it comes with a number, so this estimates the number: given the
disagreement pattern actually observed between two guardrails, how many cases
would be needed before McNemar's exact test detects the difference at 80% power?

Method: Monte Carlo over the observed joint outcome distribution. For a pair, the
four cells (both right, only A right, only B right, both wrong) are estimated
from the measured per-case outcomes. Cases are then resampled with replacement at
various N and the test re-run, and power is the fraction of simulations reaching
p < 0.05.

    python power.py

The obvious objection, stated here rather than left for a reader: the cell
probabilities are themselves estimated from a small sample, so these numbers
carry their own uncertainty, and at n=49 that uncertainty is substantial. They
are order-of-magnitude guidance for designing a corpus, not a precise
requirement. The direction of the answer is robust even if the exact figure is
not: the honest reading is that separating two competent guardrails takes
hundreds to thousands of cases, not dozens.
"""
import random
from math import erfc

import stats

SIMS = 2000
GRID = [50, 100, 200, 400, 800, 1600, 3200, 6400]
TARGET = 0.80
SEED = 20260807


def power_at(p_b: float, p_c: float, n: int, sims: int, rng: random.Random) -> float:
    """Fraction of simulated corpora of size n where McNemar reaches p < 0.05.

    Only the two discordant cells matter to the test, so the counts are drawn
    straight from the multinomial rather than case by case: b ~ Bin(n, p_b),
    then c ~ Bin(n - b, p_c / (1 - p_b)). Drawing per case is the obvious
    implementation and is thousands of times slower at n = 6400.
    """
    hits = 0
    cond = p_c / (1 - p_b) if p_b < 1 else 0.0
    for _ in range(sims):
        b = rng.binomialvariate(n, p_b)
        c = rng.binomialvariate(n - b, cond) if n > b else 0
        if mcnemar_p(b, c) < stats.ALPHA:
            hits += 1
    return hits / sims


def mcnemar_p(b: int, c: int) -> float:
    """Exact where it matters, normal approximation where it cannot.

    The exact binomial sums binomial coefficients, which is fine at the counts
    this benchmark actually produced and far too slow once a simulated corpus
    pushes the discordant total into the thousands. The two agree closely well
    before the switch, and the approximation is the standard McNemar statistic.
    """
    n = b + c
    if n == 0:
        return 1.0
    if n <= 200:
        return stats.mcnemar_exact(b, c)
    z = abs(b - c) / (n ** 0.5)
    return erfc(z / (2 ** 0.5))


def cases_needed(p_b: float, p_c: float, rng: random.Random) -> tuple[int | None, dict]:
    curve = {}
    needed = None
    for n in GRID:
        pw = power_at(p_b, p_c, n, SIMS, rng)
        curve[n] = pw
        if needed is None and pw >= TARGET:
            needed = n
    return needed, curve


def main() -> int:
    from make_report import CORPORA, DISPLAY, SECONDARY, load_results

    rng = random.Random(SEED)
    print(f"Monte Carlo power, {SIMS} simulations per point, target {int(TARGET*100)}% "
          f"at p < {stats.ALPHA}.")
    print("Cells estimated from the observed per-case outcomes.\n")

    for c in CORPORA:
        res = load_results(c["results"])
        expect = stats.load_expect(c["corpus"])
        if not res or not expect:
            continue
        g = {k: v for k, v in res["guardrails"].items() if k not in SECONDARY}
        order = [k for k, _ in sorted(g.items(), key=lambda kv: -kv[1]["f1"])]
        pairs = stats.pairwise(g, expect, order)
        same = stats.indistinguishable(pairs)
        if not same:
            continue

        print("=" * 78)
        print(f"{c['title']}  (measured at n={len(expect)})")
        print("=" * 78)
        print(f"{'pair':<44}{'observed':>10}{'cases for 80%':>15}")
        # Only the closest few matter: a pair with near-zero discordance would
        # need an unbounded corpus and saying "6400+" eight times is noise.
        for p in sorted(same, key=lambda x: -(x["b_count"] + x["c_count"]))[:5]:
            n = len(expect)
            p_b, p_c = p["b_count"] / n, p["c_count"] / n
            needed, _ = cases_needed(p_b, p_c, rng)
            label = f"{DISPLAY.get(p['a'], p['a'])} vs {DISPLAY.get(p['b'], p['b'])}"
            obs = f"{p['b_count']}/{p['c_count']}"
            req = f"{needed:,}" if needed else f">{GRID[-1]:,}"
            print(f"{label:<44}{obs:>10}{req:>15}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
