"""Prove a rebuilt corpus is identical to the one the published numbers used.

`corpus/ai4privacy.jsonl` is not redistributed: the upstream dataset card states
no licence (see corpus/SOURCES.md). So the repository ships digests instead of
text. Rebuild the corpus, run this, and you know whether you are looking at the
same 300 rows the report was computed on.

    python build_ai4privacy.py --n-positive 200 --n-negative 100 --seed 20260807
    python verify_corpus.py

Exits non-zero on any mismatch, so it works as a CI gate.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> dict[str, dict]:
    rows = {}
    # split("\n"), never splitlines(). splitlines() also breaks on U+2028,
    # U+2029, U+0085 and the C0 separators, and jailbreak.jsonl really does
    # carry two U+2028 inside JSON string values. splitlines() cuts those rows
    # in half and the JSON then fails to parse. Attack corpora are full of
    # exactly this kind of character, which is rather the point of them.
    for line in path.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if line:
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def verify(manifest_path: Path) -> int:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    corpus_path = ROOT / "corpus" / f"{manifest['corpus']}.jsonl"

    if not corpus_path.exists():
        print(f"MISSING  {corpus_path.name} has not been built yet.")
        print(f"         Rebuild it with: python {manifest['builder']}")
        return 2

    built = load_jsonl(corpus_path)
    expected = manifest["rows"]

    missing, changed, label_drift = [], [], []
    for row in expected:
        got = built.get(row["id"])
        if got is None:
            missing.append(row["id"])
            continue
        if digest(got["text"]) != row["sha256"]:
            changed.append(row["id"])
        if got.get("expect") != row["expect"]:
            label_drift.append(row["id"])

    extra = sorted(set(built) - {r["id"] for r in expected})
    problems = len(missing) + len(changed) + len(label_drift) + len(extra)

    print(f"{manifest['corpus']}: {len(expected)} rows expected, {len(built)} built")
    for label, ids in (
        ("absent from the rebuild", missing),
        ("text differs from the published corpus", changed),
        ("label differs from the published corpus", label_drift),
        ("present in the rebuild but not the manifest", extra),
    ):
        if ids:
            shown = ", ".join(ids[:8]) + (" ..." if len(ids) > 8 else "")
            print(f"  {len(ids):>4} {label}: {shown}")

    if problems == 0:
        print("  OK: byte-identical to the corpus the published results used.")
        return 0

    print()
    print("  The upstream dataset has almost certainly changed under you.")
    print("  Numbers computed on this rebuild are not comparable to the report.")
    return 1


if __name__ == "__main__":
    manifests = sorted((ROOT / "corpus").glob("*.manifest.json"))
    if not manifests:
        print("No manifests found in corpus/.")
        sys.exit(2)
    sys.exit(max(verify(m) for m in manifests))
