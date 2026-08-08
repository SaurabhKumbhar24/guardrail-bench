"""Microsoft Presidio — the de-facto open-source PII baseline.

Run with its stock recognizers and the `en_core_web_lg` spaCy model, at the
default confidence threshold. No custom recognizers are added: the point is to
measure what a team gets when they `pip install presidio-analyzer` and use it,
which is how it is actually deployed.

Presidio detects PII. It does not claim to detect API keys, injected
instructions, or exfiltration URLs, so it will score zero in those categories.
That is a scope difference, not a defect, and the per-category table is there so
it reads as one.
"""
from .base import Verdict

from presidio_analyzer import AnalyzerEngine

# The entity set the worker cares about, minus the Fluiq-specific custom key
# recognizers — those are ours, not Presidio's, and including them would be
# scoring Presidio on code it does not ship.
ENTITIES = [
    "US_SSN", "CREDIT_CARD", "IBAN_CODE", "CRYPTO", "US_PASSPORT",
    "EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "LOCATION", "IP_ADDRESS",
    "DATE_TIME", "US_DRIVER_LICENSE", "US_BANK_NUMBER", "MEDICAL_LICENSE",
]

# Presidio's own default. Left at the default deliberately — tuning a
# competitor's threshold to our corpus would be exactly the thing that makes a
# vendor benchmark worthless.
THRESHOLD = 0.5

# PERSON / LOCATION / DATE_TIME fire on ordinary prose ("Dana", "Tuesday"), so
# blocking on them alone would give Presidio a false-alarm rate that says more
# about our scoring than about Presidio. They still count when they co-occur
# with a strong identifier. Documented because it is a judgement call.
WEAK = {"PERSON", "LOCATION", "DATE_TIME"}


class PresidioGate:
    name = "presidio"
    version = "2.2"

    def __init__(self) -> None:
        self._engine = AnalyzerEngine()

    def scan(self, text: str) -> Verdict:
        try:
            res = self._engine.analyze(text=text, entities=ENTITIES, language="en")
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"{type(exc).__name__}: {exc}")

        hits = [r for r in res if r.score >= THRESHOLD]
        strong = [r.entity_type for r in hits if r.entity_type not in WEAK]
        weak = [r.entity_type for r in hits if r.entity_type in WEAK]

        blocked = bool(strong) or len(set(weak)) >= 2
        return Verdict(blocked=blocked, findings=sorted(set(strong + weak)))
