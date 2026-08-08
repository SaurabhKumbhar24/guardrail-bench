"""Build injection and jailbreak corpora from public datasets.

    python build_public_prompts.py

Two datasets, kept in **separate files on purpose**:

* `deepset/prompt-injections` — 546 rows, 203 injection / 343 benign. The
  standard public prompt-injection set.
* `jackhhao/jailbreak-classification` — 1044 rows, 527 jailbreak / 517 benign.

Injection and jailbreak are different phenomena. An injection tries to override
the operator's instructions ("ignore the above and..."); a jailbreak tries to
talk the model out of its own guardrails ("you are DAN, you have no rules").
A detector can be good at one and poor at the other, and averaging them into a
single score would hide exactly the difference a buyer needs to see.

Both datasets ship their own benign half, which is why they are worth using:
the negatives were written by someone with no stake in this benchmark.
"""
import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_CHARS = 2000


def rows_from(name: str, split: str, text_field: str, label_field: str,
              positive, n: int, seed: int, category: str, prefix: str) -> list[dict]:
    from datasets import load_dataset

    ds = load_dataset(name, split=split)
    idx = list(range(len(ds)))
    random.Random(seed).shuffle(idx)

    pos, neg, out = [], [], []
    for i in idx:
        r = ds[i]
        text = (r[text_field] or "").strip()
        if not text or len(text) > MAX_CHARS:
            continue
        is_pos = positive(r[label_field])
        bucket = pos if is_pos else neg
        if len(bucket) >= n // 2:
            continue
        bucket.append({
            "id": f"{prefix}-{'pos' if is_pos else 'neg'}-{len(bucket):04d}",
            "category": category if is_pos else f"{category}_benign",
            "expect": "block" if is_pos else "allow",
            "labels": [category] if is_pos else [],
            "text": text,
            "note": f"{name} row {i}, label={r[label_field]!r}",
        })
        if len(pos) >= n // 2 and len(neg) >= n // 2:
            break
    out = pos + neg
    random.Random(seed).shuffle(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300, help="cases per corpus, half positive")
    ap.add_argument("--seed", type=int, default=20260807)
    args = ap.parse_args()

    jobs = [
        ("injection.jsonl", "deepset/prompt-injections", "train", "text", "label",
         lambda v: int(v) == 1, "prompt_injection", "inj"),
        ("jailbreak.jsonl", "jackhhao/jailbreak-classification", "train", "prompt", "type",
         lambda v: str(v).lower() == "jailbreak", "jailbreak", "jb"),
    ]

    for fname, name, split, tf, lf, pos, cat, prefix in jobs:
        rows = rows_from(name, split, tf, lf, pos, args.n, args.seed, cat, prefix)
        out = ROOT / "corpus" / fname
        out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                       encoding="utf-8")
        nb = sum(1 for r in rows if r["expect"] == "block")
        print(f"{out.name}: {len(rows)} cases ({nb} block / {len(rows)-nb} allow)  <- {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
