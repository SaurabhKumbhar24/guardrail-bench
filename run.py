"""Run the corpus against every available guardrail and print the scores.

    python run.py                 # everything importable
    python run.py --only fluiq.secure regex-baseline
    python run.py --json results.json

Scoring is fixed before any contestant is run, and is deliberately boring:

    expect=block, blocked  -> caught       (true positive)
    expect=block, allowed  -> MISS         (false negative)
    expect=allow,  blocked -> FALSE ALARM  (false positive)
    expect=allow,  allowed -> quiet        (true negative)

Recall alone is a bad metric here: a guardrail that blocks everything scores
100%. So the headline number is F1 over both, and the false-alarm rate is
printed next to recall so neither can be read on its own.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def load_cases(name: str = "cases.jsonl") -> list[dict]:
    path = ROOT / "corpus" / name
    cases = []
    # Split on a literal newline rather than str.splitlines(). splitlines() also
    # breaks on vertical tab, form feed, the file/group/record separators, NEL,
    # and the Unicode line/paragraph separators - all of which are legal raw
    # characters inside a JSON string. Jailbreak prompts contain them, and a line
    # torn at one of those looks like corrupt JSON.
    for line in path.read_text(encoding="utf-8").split(chr(10)):
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def discover():
    """Import every adapter that can be imported. A contestant whose SDK or key
    is missing is skipped and reported, never silently scored as zero."""
    found, skipped = [], []
    specs = [
        ("adapters.fluiq_worker", "FluiqWorkerGate"),
        ("adapters.fluiq_input", "FluiqInputGate"),
        ("adapters.fluiq_worker_input", "FluiqWorkerInputGate"),
        ("adapters.fluiq_worker_check", "FluiqWorkerCheckGate"),
        ("adapters.fluiq_gate", "FluiqGate"),
        ("adapters.regex_baseline", "RegexBaseline"),
        ("adapters.presidio_gate", "PresidioGate"),
        ("adapters.llm_guard_gate", "LLMGuardGate"),
        ("adapters.llm_guard_injection", "LLMGuardInjectionGate"),
        ("adapters.nemo_gate", "NemoGate"),
        ("adapters.aws_comprehend", "ComprehendGate"),
        ("adapters.gcp_dlp", "DlpGate"),
        ("adapters.azure_content_safety", "AzureGate"),
        ("adapters.lakera", "LakeraGate"),
        ("adapters.nightfall", "NightfallGate"),
        ("adapters.nightfall_injection", "NightfallInjectionGate"),
        ("adapters.llama_guard", "LlamaGuardGate"),
    ]
    for mod_name, cls_name in specs:
        try:
            mod = __import__(mod_name, fromlist=[cls_name])
            found.append(getattr(mod, cls_name)())
        except Exception as exc:  # noqa: BLE001
            skipped.append((mod_name.split(".")[-1], f"{type(exc).__name__}: {exc}"[:90]))
    return found, skipped


@dataclass
class Score:
    caught: int = 0
    missed: int = 0
    false_alarm: int = 0
    quiet: int = 0
    errors: int = 0

    @property
    def recall(self) -> float:
        d = self.caught + self.missed
        return self.caught / d if d else 0.0

    @property
    def false_alarm_rate(self) -> float:
        d = self.false_alarm + self.quiet
        return self.false_alarm / d if d else 0.0

    @property
    def precision(self) -> float:
        d = self.caught + self.false_alarm
        return self.caught / d if d else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--corpus", default="cases.jsonl",
                    help="Corpus file under corpus/. The hand-written suite and the "
                         "public ai4privacy sample are kept separate on purpose: "
                         "mixing them would blur two different claims.")
    ap.add_argument("--json", default=None)
    ap.add_argument("--merge", nargs="*", default=None,
                    help="Merge previously written results files instead of running. "
                         "Contestants can need incompatible environments (LLM Guard "
                         "needs <=3.12; torch needs its own), so each env writes a "
                         "file and they are combined here.")
    args = ap.parse_args()

    if args.merge:
        merged = {"cases": None, "guardrails": {}}
        for f in args.merge:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            if merged["cases"] is None:
                merged["cases"] = d["cases"]
            elif merged["cases"] != d["cases"]:
                raise SystemExit(
                    f"refusing to merge: {f} scored {d['cases']} cases, "
                    f"expected {merged['cases']}. Results from different corpus "
                    f"versions are not comparable."
                )
            merged["guardrails"].update(d["guardrails"])
        print(f"merged {len(args.merge)} files -> {len(merged['guardrails'])} contestants "
              f"over {merged['cases']} cases\n")
        w2 = max(len(n) for n in merged["guardrails"])
        print(f"{'guardrail'.ljust(w2)}  {'recall':>7} {'false alarm':>12} {'F1':>7}")
        print("-" * (w2 + 32))
        for name, r in sorted(merged["guardrails"].items(), key=lambda kv: -kv[1]["f1"]):
            print(f"{name.ljust(w2)}  {r['recall']*100:6.1f}% "
                  f"{r['false_alarm_rate']*100:11.1f}% {r['f1']*100:6.1f}%")
        if args.json:
            Path(args.json).write_text(json.dumps(merged, indent=2), encoding="utf-8")
            print(f"\nwrote {args.json}")
        return 0

    cases = load_cases(args.corpus)
    rails, skipped = discover()
    if args.only:
        rails = [g for g in rails if g.name in args.only]

    categories = sorted({c["category"] for c in cases})
    n_block = sum(1 for c in cases if c["expect"] == "block")
    print(f"corpus: {len(cases)} cases ({n_block} should block, {len(cases) - n_block} should pass)")
    print(f"contestants: {', '.join(g.name for g in rails) or 'none'}\n")

    results: dict = {"cases": len(cases), "guardrails": {}}
    per_cat: dict = {}

    for g in rails:
        total = Score()
        cat_scores = {c: Score() for c in categories}
        misses: list[str] = []
        alarms: list[str] = []

        for case in cases:
            v = g.scan(case["text"])
            s = cat_scores[case["category"]]
            if v.error:
                total.errors += 1
                s.errors += 1
                continue
            if case["expect"] == "block":
                if v.blocked:
                    total.caught += 1; s.caught += 1
                else:
                    total.missed += 1; s.missed += 1
                    misses.append(case["id"])
            else:
                if v.blocked:
                    total.false_alarm += 1; s.false_alarm += 1
                    alarms.append(case["id"])
                else:
                    total.quiet += 1; s.quiet += 1

        results["guardrails"][g.name] = {
            "version": getattr(g, "version", "?"),
            "recall": round(total.recall, 4),
            "false_alarm_rate": round(total.false_alarm_rate, 4),
            "precision": round(total.precision, 4),
            "f1": round(total.f1, 4),
            "errors": total.errors,
            "missed": misses,
            "false_alarms": alarms,
            "by_category": {
                c: {"caught": sc.caught, "missed": sc.missed,
                    "false_alarm": sc.false_alarm, "quiet": sc.quiet}
                for c, sc in cat_scores.items()
            },
        }
        per_cat[g.name] = cat_scores

    # ── Headline table ────────────────────────────────────────────────────────
    w = max((len(g.name) for g in rails), default=10)
    print(f"{'guardrail'.ljust(w)}  {'recall':>7} {'false alarm':>12} {'F1':>7}  errors")
    print("-" * (w + 42))
    for name, r in sorted(results["guardrails"].items(), key=lambda kv: -kv[1]["f1"]):
        # An error is a case the contestant never actually judged. Past a few
        # percent the remaining score is drawn from a subset it did not choose,
        # so it is not a comparable number and is not presented as one.
        unreliable = r["errors"] > max(3, 0.02 * len(cases))
        flag = "  << UNRELIABLE, errors exceed 2% of corpus" if unreliable else ""
        r["unreliable"] = unreliable
        print(f"{name.ljust(w)}  {r['recall']*100:6.1f}% {r['false_alarm_rate']*100:11.1f}% "
              f"{r['f1']*100:6.1f}%  {r['errors']}{flag}")

    # ── Per-category recall, where the interesting differences live ───────────
    print(f"\nrecall by category")
    print(f"{'category'.ljust(20)}  " + "  ".join(n[:14].rjust(14) for n in per_cat))
    for cat in categories:
        if all(per_cat[n][cat].caught + per_cat[n][cat].missed == 0 for n in per_cat):
            continue  # an allow-only category has no recall to report
        row = []
        for n in per_cat:
            s = per_cat[n][cat]
            d = s.caught + s.missed
            row.append((f"{s.caught}/{d}").rjust(14) if d else "".rjust(14))
        print(f"{cat.ljust(20)}  " + "  ".join(row))

    print(f"\nfalse alarms on benign text")
    for n in per_cat:
        fa = results["guardrails"][n]["false_alarms"]
        print(f"  {n.ljust(w)}  {len(fa)}  {' '.join(fa) if fa else '-'}")

    if skipped:
        print(f"\nnot run ({len(skipped)}) — missing dependency or credentials:")
        for name, why in skipped:
            print(f"  {name.ljust(24)} {why}")

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
