# Corpus sources and licensing

Four corpora, three different provenances. This file records where each one came
from and what may be done with it, because a benchmark that will not say where
its data came from is not worth reading.

## Written for this benchmark

| File | Cases | Licence |
|---|---:|---|
| `cases.jsonl` | 49 | MIT, published here |
| `fp_audit.jsonl` | 21 | MIT, published here |

Every value in both files is synthetic. The people, addresses, card numbers, SSNs
and keys are invented, the domains are all `example.com` or `example.org`, and the
two recognisable strings are vendor documentation examples published for exactly
this purpose: `AKIAIOSFODNN7EXAMPLE` from the AWS docs and the GitHub token
example from the GitHub docs. Nothing here belongs to anyone and nothing unlocks
anything.

`fp_audit.jsonl` is derived from Fluiq's own regression test file
`tests/test_pattern_tiering.py`. It is not customer data. No traffic, prompt or
completion belonging to any Fluiq user appears in any corpus in this repository.

**Note for anyone cloning this:** the synthetic secrets in `cases.jsonl` are
realistic by design, because a corpus full of unrealistically short keys rewards
sloppy detectors. That means automated secret scanners will flag this file. They
are correct to flag the shape and wrong about the risk.

## Redistributed under Apache-2.0

| File | Cases | Upstream | Licence |
|---|---:|---|---|
| `injection.jsonl` and its dev/test splits | 300 | [`deepset/prompt-injections`](https://huggingface.co/datasets/deepset/prompt-injections) | Apache-2.0 |
| `jailbreak.jsonl` and its dev/test splits | 300 | [`jackhhao/jailbreak-classification`](https://huggingface.co/datasets/jackhhao/jailbreak-classification) | Apache-2.0 |

Both permit redistribution with attribution, which is what this section is.
Sampled by `build_public_prompts.py` at seed 20260807. The `_en` variants are the
English-only subset of the injection corpus, kept separate because roughly a
third of that dataset is not in English and that turns out to change the ranking.

## Not redistributed

| File | Cases | Upstream | Licence |
|---|---:|---|---|
| `ai4privacy.jsonl` | 300 | [`ai4privacy/pii-masking-200k`](https://huggingface.co/datasets/ai4privacy/pii-masking-200k) | **Not stated on the dataset card** |

The dataset card states no licence, so the default position is that we have no
right to redistribute it and we do not. The sampled rows are absent from this
repository and the results computed from them are published anyway.

To reproduce that corpus:

```bash
python build_ai4privacy.py --n-positive 200 --n-negative 100 --seed 20260807
```

Then verify you rebuilt the identical corpus:

```bash
python verify_corpus.py
```

`ai4privacy.manifest.json` carries the case ID, the expected label and the
SHA-256 of the UTF-8 text for all 300 rows. That is enough to prove a rebuild is
byte-identical to the corpus the published numbers were computed on, without
redistributing a single row of text.

One caveat worth stating: the sampler is seeded but the upstream dataset is not
revision-pinned, because the dataset card does not publish a stable revision to
pin to. If upstream changes, the manifest will tell you, which is the point of
having it.
