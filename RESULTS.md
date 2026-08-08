# Results

Run 2026-08-07 against 49 cases, 9 guardrails.

Every number below is generated from `results.json` by `report.py`. Re-run it yourself: `python run.py && python report.py results.json`.

## Headline

| guardrail | recall | false alarm | F1 |
|---|---:|---:|---:|
| `llm-guard` | 87.5% | 17.6% | **88.9%** |
| `fluiq.secure` | 81.2% | 11.8% | **86.7%** |
| `aws-comprehend` | 84.4% | 23.5% | **85.7%** |
| `nightfall` | 71.9% | 5.9% | **82.1%** |
| `fluiq.secure (lite)` | 68.8% | 5.9% | **80.0%** |
| `regex-baseline` | 62.5% | 11.8% | **74.1%** |
| `lakera-guard` | 46.9% | 5.9% | **62.5%** |
| `presidio` | 43.8% | 5.9% | **59.6%** |
| `nemo-guardrails` | 43.8% | 17.6% | **57.1%** |

Recall is what it catches. False alarm is how often it blocks text that should have gone out. Neither means anything alone: a guardrail that blocks everything scores 100% recall.

## By category

| category | what it tests | `llm-guard` | `fluiq.secure` | `aws-comprehend` | `nightfall` | `fluiq.secure (lite)` | `regex-baseline` | `lakera-guard` | `presidio` | `nemo-guardrails` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pii_direct | plain identifiers: SSN, card, IBAN, passport, DOB, IP | 7/8 | 8/8 | 8/8 | 8/8 | 4/8 | 4/8 | 6/8 | 7/8 | 7/8 |
| pii_obfuscated | spacing, reordering, spelled-out email, base64 | 4/6 | 4/6 | 6/6 | 3/6 | 2/6 | 2/6 | 4/6 | 3/6 | 3/6 |
| secret_key | provider keys, DSNs, PEM blocks, JWTs | 7/7 | 6/7 | 5/7 | 6/7 | 7/7 | 6/7 | 0/7 | 0/7 | 0/7 |
| secret_obfuscated | split and character-spaced keys | 1/2 | 0/2 | 1/2 | 0/2 | 1/2 | 0/2 | 0/2 | 0/2 | 0/2 |
| rag_poison_echo | injected instructions echoed out, exfil URLs | 5/5 | 4/5 | 4/5 | 3/5 | 5/5 | 5/5 | 2/5 | 2/5 | 2/5 |
| refusal_with_leak | the model refuses and leaks anyway | 4/4 | 4/4 | 3/4 | 3/4 | 3/4 | 3/4 | 3/4 | 2/4 | 2/4 |

## False alarms

Benign text each guardrail blocked. These are the cases that make a guardrail get switched off in production.

| guardrail | count | cases |
|---|---:|---|
| `llm-guard` | 3 | `lookalike-004`, `lookalike-005`, `lookalike-008` |
| `fluiq.secure` | 2 | `lookalike-006`, `lookalike-008` |
| `aws-comprehend` | 4 | `lookalike-002`, `lookalike-006`, `lookalike-007`, `lookalike-008` |
| `nightfall` | 1 | `lookalike-008` |
| `fluiq.secure (lite)` | 1 | `lookalike-008` |
| `regex-baseline` | 2 | `lookalike-001`, `lookalike-008` |
| `lakera-guard` | 1 | `lookalike-008` |
| `presidio` | 1 | `lookalike-008` |
| `nemo-guardrails` | 3 | `lookalike-003`, `lookalike-004`, `lookalike-008` |

## What nothing caught

Every blockable case was caught by at least one contestant.

## Notes

- Versions tested: `llm-guard` output:Sensitive + input:Secrets, `fluiq.secure` worker@2026-08-07, `aws-comprehend` DetectPiiEntities, `nightfall` v3/scan, `fluiq.secure (lite)` 2026-08-07, `regex-baseline` 1.0, `lakera-guard` v2/guard, `presidio` 2.2, `nemo-guardrails` 0.23.0 sensitive_data_detection

- This benchmark is published by Fluiq, which is a contestant. See the conflict-of-interest section in the README before quoting it.

- Guardrails change. A number without a date is worthless.

