# Output Guardrails: A Measured Comparison

*Fluiq · measured 2026-08-07 · <https://github.com/SaurabhKumbhar24/guardrail-bench>*

## Summary

Most LLM safety benchmarks ask whether the model misbehaves. This one asks a different question: **given something a model is about to say, or something a user just sent, would your guardrail stop it?**

Eight guardrails, measured on four corpora. Six are independent products, one is a thirty-line regex control, and one is ours. Two of the corpora are public datasets that neither we nor any vendor curated.

**Most of the ordering below is not statistically significant, including the part that flatters us.** Every guardrail sees the identical case list, so the outcomes are paired and McNemar's exact test applies. On the 49-case adversarial suite it separates only 11 of 28 pairs: the top four finishers are mutually indistinguishable, and the leader is not distinguishable from the thirty-line regex control (p = 0.065). On the jailbreak corpus, Lakera's 97.3% recall is not distinguishable from that same control (p = 0.25), because an 83.3% false-alarm rate cancels the advantage. Every table now carries Wilson intervals and the pairs the data cannot separate, because a ranked list with no interval invites a reader to believe an order the sample size does not support.


## Output leakage: adversarial suite

Hand-built cases covering leak shapes a PII corpus does not contain: obfuscated identifiers, credential formats, injected instructions echoed into output, and model refusals that leak while refusing.

**Corpus** — 49 cases (32 should block, 17 should pass). **Source** — Written for this benchmark. **Licence** — MIT (published with this repository).

| Guardrail | Category | Recall | 95% CI | False alarm | 95% CI | F1 |
|---|---|---:|---:|---:|---:|---:|
| `llm-guard` | Open source | 87.5% | [71.9, 95.0] | 17.6% | [6.2, 41.0] | **88.9%** |
| `fluiq` | Fluiq | 81.2% | [64.7, 91.1] | 11.8% | [3.3, 34.3] | **86.7%** |
| `aws-comprehend` | Commercial | 84.4% | [68.2, 93.1] | 23.5% | [9.6, 47.3] | **85.7%** |
| `nightfall` | Commercial | 71.9% | [54.6, 84.4] | 5.9% | [1.0, 27.0] | **82.1%** |
| `regex-baseline` | Control | 62.5% | [45.3, 77.1] | 11.8% | [3.3, 34.3] | **74.1%** |
| `lakera-guard` | Commercial | 46.9% | [30.9, 63.6] | 5.9% | [1.0, 27.0] | **62.5%** |
| `presidio` | Open source | 43.8% | [28.2, 60.7] | 5.9% | [1.0, 27.0] | **59.6%** |
| `nemo-guardrails` | Open source | 43.8% | [28.2, 60.7] | 17.6% | [6.2, 41.0] | **57.1%** |

**How much of this order is real?** McNemar's exact test on the paired per-case outcomes separates 11 of 28 pairs at p < 0.05.

The data cannot separate these pairs:

| Pair | Discordant | p |
|---|---:|---:|
| `llm-guard` vs `fluiq` | 4/3 | 1.000 |
| `llm-guard` vs `aws-comprehend` | 8/6 | 0.791 |
| `llm-guard` vs `nightfall` | 6/3 | 0.508 |
| `llm-guard` vs `regex-baseline` | 9/2 | 0.065 |
| `fluiq` vs `aws-comprehend` | 6/5 | 1.000 |
| `fluiq` vs `nightfall` | 5/3 | 0.727 |
| `fluiq` vs `regex-baseline` | 9/3 | 0.146 |
| `aws-comprehend` vs `nightfall` | 7/6 | 1.000 |
| `aws-comprehend` vs `regex-baseline` | 10/5 | 0.302 |
| `nightfall` vs `regex-baseline` | 7/3 | 0.344 |
| `nightfall` vs `lakera-guard` | 11/3 | 0.057 |
| `regex-baseline` vs `lakera-guard` | 10/6 | 0.454 |
| `regex-baseline` vs `presidio` | 10/5 | 0.302 |
| `regex-baseline` vs `nemo-guardrails` | 12/5 | 0.143 |
| `lakera-guard` vs `presidio` | 2/1 | 1.000 |
| `lakera-guard` vs `nemo-guardrails` | 5/2 | 0.453 |
| `presidio` vs `nemo-guardrails` | 3/1 | 0.625 |

## Output leakage: public PII corpus

Sampled from the most widely used public PII dataset. Positives are rows containing at least one strong identifier; negatives are the same rows with PII replaced by placeholders, so both halves share a distribution.

**Corpus** — 300 cases (200 should block, 100 should pass). **Source** — ai4privacy/pii-masking-200k. **Licence** — Not stated on the dataset card.

| Guardrail | Category | Recall | 95% CI | False alarm | 95% CI | F1 |
|---|---|---:|---:|---:|---:|---:|
| `aws-comprehend` | Commercial | 92.5% | [88.0, 95.4] | 0.0% | [0.0, 3.7] | **96.1%** |
| `fluiq` | Fluiq | 81.0% | [75.0, 85.8] | 0.0% | [0.0, 3.7] | **89.5%** |
| `llm-guard` | Open source | 80.0% | [73.9, 85.0] | 3.0% | [1.0, 8.5] | **88.1%** |
| `presidio` | Open source | 69.0% | [62.3, 75.0] | 0.0% | [0.0, 3.7] | **81.7%** |
| `nightfall` | Commercial | 68.0% | [61.2, 74.1] | 0.0% | [0.0, 3.7] | **81.0%** |
| `nemo-guardrails` | Open source | 67.5% | [60.7, 73.6] | 0.0% | [0.0, 3.7] | **80.6%** |
| `lakera-guard` | Commercial | 63.0% | [56.1, 69.4] | 5.0% | [2.2, 11.2] | **76.1%** |
| `regex-baseline` | Control | 42.0% | [35.4, 48.9] | 0.0% | [0.0, 3.7] | **59.2%** |

**How much of this order is real?** McNemar's exact test on the paired per-case outcomes separates 24 of 28 pairs at p < 0.05.

The data cannot separate these pairs:

| Pair | Discordant | p |
|---|---:|---:|
| `fluiq` vs `llm-guard` | 18/13 | 0.473 |
| `presidio` vs `nightfall` | 22/20 | 0.878 |
| `presidio` vs `nemo-guardrails` | 20/17 | 0.743 |
| `nightfall` vs `nemo-guardrails` | 16/15 | 1.000 |

## Prompt injection

The standard public prompt-injection set, balanced 150/150. Roughly a third of the attacks are not in English, which turns out to matter a great deal.

**Corpus** — 300 cases (150 should block, 150 should pass). **Source** — deepset/prompt-injections. **Licence** — Apache-2.0.

| Guardrail | Category | Recall | 95% CI | False alarm | 95% CI | F1 |
|---|---|---:|---:|---:|---:|---:|
| `lakera-guard` | Commercial | 94.7% | [89.8, 97.3] | 16.7% | [11.6, 23.4] | **89.6%** |
| `llm-guard` | Open source | 38.0% | [30.6, 46.0] | 1.3% | [0.4, 4.7] | **54.5%** |
| `fluiq` | Fluiq | 35.3% | [28.1, 43.3] | 0.7% | [0.1, 3.7] | **52.0%** |
| `regex-baseline` | Control | 0.0% | [0.0, 2.5] | 0.0% | [0.0, 2.5] | **0.0%** |

**How much of this order is real?** McNemar's exact test on the paired per-case outcomes separates 5 of 6 pairs at p < 0.05.

The data cannot separate these pairs:

| Pair | Discordant | p |
|---|---:|---:|
| `llm-guard` vs `fluiq` | 20/17 | 0.743 |

## Jailbreak

Balanced 150/150. The benign half contains a large amount of persona and roleplay prompts, which is the source of a labelling disagreement discussed under Limitations.

**Corpus** — 300 cases (150 should block, 150 should pass). **Source** — jackhhao/jailbreak-classification. **Licence** — Apache-2.0.

| Guardrail | Category | Recall | 95% CI | False alarm | 95% CI | F1 |
|---|---|---:|---:|---:|---:|---:|
| `llm-guard` | Open source | 68.7% | [60.9, 75.5] | 0.7% | [0.1, 3.7] | **81.1%** |
| `lakera-guard` | Commercial | 97.3% | [93.3, 99.0] | 83.3% | [76.6, 88.4] | **69.4%** |
| `fluiq` | Fluiq | 53.3% | [45.4, 61.1] | 6.0% | [3.2, 11.0] | **67.0%** |
| `regex-baseline` | Control | 0.7% | [0.1, 3.7] | 0.0% | [0.0, 2.5] | **1.3%** |

**How much of this order is real?** McNemar's exact test on the paired per-case outcomes separates 5 of 6 pairs at p < 0.05.

The data cannot separate these pairs:

| Pair | Discordant | p |
|---|---:|---:|
| `lakera-guard` vs `regex-baseline` | 145/125 | 0.248 |

## Other Fluiq configurations

The tables above give every contestant one row, ours included. We measured more than one configuration of our own gate, and the one that ships as `fluiq.secure()` is the one that competes. The rest are below, with their numbers, because every one of them scores lower and leaving them out would be the convenient thing to do.

| Configuration | Corpus | Recall | False alarm | F1 |
|---|---|---:|---:|---:|
| `fluiq (inline scanner)` | Output leakage: adversarial suite | 68.8% | 5.9% | 80.0% |
| `fluiq (inline scanner)` | Output leakage: public PII corpus | 39.0% | 0.0% | 56.1% |
| `fluiq (API fast path)` | Prompt injection | 13.3% | 0.0% | 23.5% |
| `fluiq (API fast path)` | Jailbreak | 42.0% | 5.3% | 57.0% |

`fluiq (API fast path)` is the synchronous pattern-only check served by the API, which has no semantic layer. `fluiq (inline scanner)` is the trimmed scanner behind the public demo page. Both are real code paths, neither is the product.


## Method

Every guardrail receives the same string and answers one question: block or allow. Scoring was fixed before any contestant ran.

| Corpus says | Guardrail says | Counted as |
|---|---|---|
| block | blocked | caught |
| block | allowed | miss |
| allow | blocked | false alarm |
| allow | allowed | quiet |

Recall alone is a useless metric here — a guardrail that blocks everything scores 100%. The headline is F1 across both, and the false-alarm rate is always printed beside recall so neither can be quoted alone.
