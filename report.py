"""Render RESULTS.md from a merged results file.

Generated rather than hand-written so the published tables cannot drift from the
numbers, and so nobody has to trust that a vendor transcribed its own benchmark
honestly.

    python report.py results.json > RESULTS.md
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CATEGORY_BLURB = {
    "pii_direct":        "plain identifiers: SSN, card, IBAN, passport, DOB, IP",
    "pii_obfuscated":    "spacing, reordering, spelled-out email, base64",
    "secret_key":        "provider keys, DSNs, PEM blocks, JWTs",
    "secret_obfuscated": "split and character-spaced keys",
    "rag_poison_echo":   "injected instructions echoed out, exfil URLs",
    "refusal_with_leak": "the model refuses and leaks anyway",
}


def main(path: str) -> int:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    rails = d["guardrails"]
    cases = {}
    for line in (ROOT / "corpus" / "cases.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = json.loads(line)
            cases[c["id"]] = c

    order = sorted(rails, key=lambda n: -rails[n]["f1"])
    cats = [c for c in CATEGORY_BLURB if any(
        rails[n]["by_category"].get(c, {}).get("caught", 0)
        + rails[n]["by_category"].get(c, {}).get("missed", 0) for n in rails)]

    o: list[str] = []
    w = o.append

    w(f"# Results\n")
    w(f"Run {date.today().isoformat()} against {d['cases']} cases, {len(rails)} guardrails.\n")
    w("Every number below is generated from `results.json` by `report.py`. "
      "Re-run it yourself: `python run.py && python report.py results.json`.\n")

    w("## Headline\n")
    w("| guardrail | recall | false alarm | F1 |")
    w("|---|---:|---:|---:|")
    for n in order:
        r = rails[n]
        w(f"| `{n}` | {r['recall']*100:.1f}% | {r['false_alarm_rate']*100:.1f}% | **{r['f1']*100:.1f}%** |")
    w("")
    w("Recall is what it catches. False alarm is how often it blocks text that "
      "should have gone out. Neither means anything alone: a guardrail that "
      "blocks everything scores 100% recall.\n")

    w("## By category\n")
    hdr = "| category | what it tests | " + " | ".join(f"`{n}`" for n in order) + " |"
    w(hdr)
    w("|---|---|" + "---:|" * len(order))
    for c in cats:
        row = [c, CATEGORY_BLURB[c]]
        for n in order:
            b = rails[n]["by_category"].get(c, {})
            tot = b.get("caught", 0) + b.get("missed", 0)
            row.append(f"{b.get('caught', 0)}/{tot}" if tot else "—")
        w("| " + " | ".join(row) + " |")
    w("")

    w("## False alarms\n")
    w("Benign text each guardrail blocked. These are the cases that make a "
      "guardrail get switched off in production.\n")
    w("| guardrail | count | cases |")
    w("|---|---:|---|")
    for n in order:
        fa = rails[n]["false_alarms"]
        w(f"| `{n}` | {len(fa)} | {', '.join(f'`{i}`' for i in fa) if fa else '—'} |")
    w("")

    w("## What nothing caught\n")
    universal = [i for i in cases
                 if cases[i]["expect"] == "block"
                 and all(i in rails[n]["missed"] for n in rails)]
    if universal:
        w("Missed by every single contestant:\n")
        for i in universal:
            w(f"- **`{i}`** ({cases[i]['category']}) — {cases[i]['note']}")
            w(f"  > {cases[i]['text'][:150]}")
        w("")
    else:
        w("Every blockable case was caught by at least one contestant.\n")

    w("## Notes\n")
    w("- Versions tested: " + ", ".join(f"`{n}` {rails[n]['version']}" for n in order) + "\n")
    w("- This benchmark is published by Fluiq, which is a contestant. "
      "See the conflict-of-interest section in the README before quoting it.\n")
    w("- Guardrails change. A number without a date is worthless.\n")

    print("\n".join(o))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "results.json"))
