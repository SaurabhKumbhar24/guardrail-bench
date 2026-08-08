"""NVIDIA NeMo Guardrails — the `sensitive data detection` output rail.

NeMo ships several output rails. Most of the interesting ones (`self check
output`, fact-checking, moderation) call an LLM, which would make this a model
benchmark rather than a guardrail benchmark and would cost money per case. The
sensitive-data rail is the one that answers our question deterministically, so
that is the one measured.

Worth stating plainly: **this rail is Presidio underneath.** NeMo supplies the
configuration — which entity types, which threshold, which sources — not the
detection engine. So a NeMo score close to the Presidio score is the expected
result, not a bug, and the difference between them is a measure of NeMo's
defaults rather than of two independent detectors.

On the entity list, and why it is not NeMo's documented example verbatim:

PERSON, LOCATION and DATE_TIME fire constantly on ordinary prose. Presidio and
AWS Comprehend are scored here with a rule that those weak entities only count
when two or more co-occur, because blocking on a single "Tuesday" is not a
guardrail anyone ships. NeMo's rail returns one boolean and cannot express that
rule, so including DATE_TIME made it flag "Refunds within 30 days" as sensitive.

Leaving it in would have handed NeMo a false-alarm rate that measured our
configuration rather than NeMo. The weak entities are therefore dropped, which
is the closest available equivalent of the allowance the other PII detectors get.
Everything else is stock.
"""
import asyncio

from .base import Verdict

ENTITIES = [
    "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "CREDIT_CARD",
    "IP_ADDRESS", "IBAN_CODE", "US_PASSPORT", "CRYPTO",
    "US_DRIVER_LICENSE", "US_BANK_NUMBER", "MEDICAL_LICENSE",
]

_CONFIG_YAML = """
models: []
rails:
  config:
    sensitive_data_detection:
      output:
        entities: [%s]
""" % ", ".join(ENTITIES)


class NemoGate:
    name = "nemo-guardrails"
    version = "0.23.0 sensitive_data_detection"

    def __init__(self) -> None:
        from nemoguardrails import RailsConfig
        from nemoguardrails.library.sensitive_data_detection.actions import (
            detect_sensitive_data,
        )

        self._config = RailsConfig.from_content(yaml_content=_CONFIG_YAML)
        self._detect = detect_sensitive_data
        self._loop = asyncio.new_event_loop()
        # Prove the rail actually runs before any case is scored, so a broken
        # config surfaces as "not run" rather than 49 silent misses.
        self._loop.run_until_complete(
            self._detect(source="output", text="ping", config=self._config)
        )

    def scan(self, text: str) -> Verdict:
        try:
            hit = self._loop.run_until_complete(
                self._detect(source="output", text=text, config=self._config)
            )
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"{type(exc).__name__}: {exc}")
        return Verdict(blocked=bool(hit), findings=["sensitive_data"] if hit else [])
