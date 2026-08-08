# Output Guardrails: A Measured Comparison

*Fluiq · 2026-08-07*

## Summary

Most LLM safety benchmarks ask whether the model misbehaves. This one asks a different question: **given something a model is about to say, or something a user just sent, would your guardrail stop it?**

Nine guardrails across four independent products, a control, and two Fluiq configurations, measured on four corpora — two of them public datasets that neither we nor any vendor curated.


## Output leakage — adversarial suite

Hand-built cases covering leak shapes a PII corpus does not contain: obfuscated identifiers, credential formats, injected instructions echoed into output, and model refusals that leak while refusing.

**Corpus** — 49 cases (32 should block, 17 should pass). **Source** — Written for this benchmark. **Licence** — MIT (published with this repository).

| Guardrail | Category | Recall | False alarm | F1 |
|---|---|---:|---:|---:|
| `llm-guard` | Open source | 87.5% | 17.6% | **88.9%** |
| `fluiq.secure` | Fluiq | 81.2% | 11.8% | **86.7%** |
| `aws-comprehend` | Commercial | 84.4% | 23.5% | **85.7%** |
| `nightfall` | Commercial | 71.9% | 5.9% | **82.1%** |
| `fluiq.secure (lite)` | Fluiq | 68.8% | 5.9% | **80.0%** |
| `regex-baseline` | Control | 62.5% | 11.8% | **74.1%** |
| `lakera-guard` | Commercial | 46.9% | 5.9% | **62.5%** |
| `presidio` | Open source | 43.8% | 5.9% | **59.6%** |
| `nemo-guardrails` | Open source | 43.8% | 17.6% | **57.1%** |

## Output leakage — public PII corpus

Sampled from the most widely used public PII dataset. Positives are rows containing at least one strong identifier; negatives are the same rows with PII replaced by placeholders, so both halves share a distribution.

**Corpus** — 300 cases (200 should block, 100 should pass). **Source** — ai4privacy/pii-masking-200k. **Licence** — Not stated on the dataset card.

| Guardrail | Category | Recall | False alarm | F1 |
|---|---|---:|---:|---:|
| `aws-comprehend` | Commercial | 92.5% | 0.0% | **96.1%** |
| `fluiq.secure` | Fluiq | 81.0% | 0.0% | **89.5%** |
| `llm-guard` | Open source | 80.0% | 3.0% | **88.1%** |
| `presidio` | Open source | 69.0% | 0.0% | **81.7%** |
| `nightfall` | Commercial | 68.0% | 0.0% | **81.0%** |
| `nemo-guardrails` | Open source | 67.5% | 0.0% | **80.6%** |
| `lakera-guard` | Commercial | 63.0% | 5.0% | **76.1%** |
| `regex-baseline` | Control | 42.0% | 0.0% | **59.2%** |
| `fluiq.secure (lite)` | Fluiq | 39.0% | 0.0% | **56.1%** |

## Prompt injection

The standard public prompt-injection set, balanced 150/150. Roughly a third of the attacks are not in English, which turns out to matter a great deal.

**Corpus** — 300 cases (150 should block, 150 should pass). **Source** — deepset/prompt-injections. **Licence** — Apache-2.0.

| Guardrail | Category | Recall | False alarm | F1 |
|---|---|---:|---:|---:|
| `lakera-guard` | Commercial | 94.7% | 16.7% | **89.6%** |
| `llm-guard (injection)` | Open source | 38.0% | 1.3% | **54.5%** |
| `fluiq.secure (input)` | Fluiq | 13.3% | 0.0% | **23.5%** |
| `regex-baseline` | Control | 0.0% | 0.0% | **0.0%** |

## Jailbreak

Balanced 150/150. The benign half contains a large amount of persona and roleplay prompts, which is the source of a labelling disagreement discussed under Limitations.

**Corpus** — 300 cases (150 should block, 150 should pass). **Source** — jackhhao/jailbreak-classification. **Licence** — Apache-2.0.

| Guardrail | Category | Recall | False alarm | F1 |
|---|---|---:|---:|---:|
| `llm-guard (injection)` | Open source | 68.7% | 0.7% | **81.1%** |
| `lakera-guard` | Commercial | 97.3% | 83.3% | **69.4%** |
| `fluiq.secure (input)` | Fluiq | 42.0% | 5.3% | **57.0%** |

## Method

Every guardrail receives the same string and answers one question: block or allow. Scoring was fixed before any contestant ran.

| Corpus says | Guardrail says | Counted as |
|---|---|---|
| block | blocked | caught |
| block | allowed | miss |
| allow | blocked | false alarm |
| allow | allowed | quiet |

Recall alone is a useless metric here — a guardrail that blocks everything scores 100%. The headline is F1 across both, and the false-alarm rate is always printed beside recall so neither can be quoted alone.
