"""AWS Comprehend — `DetectPiiEntities`.

A commercial, managed PII detector from a hyperscaler. Included because "just use
the cloud provider's PII API" is a real and common alternative to buying a
guardrail, and it deserves to be measured rather than assumed inadequate.

Like Presidio, it detects PII and does not claim to detect API keys or injected
instructions, so it will score zero in those categories. Scope difference, not
defect.

Costs a fraction of a cent for the whole corpus. Needs working AWS credentials
and `boto3`; skipped and reported if either is missing.
"""
import os

from .base import Verdict

# Comprehend's own default. Not tuned to this corpus.
THRESHOLD = 0.5

# Entity types that on their own justify blocking a response. NAME / ADDRESS /
# DATE_TIME fire on ordinary prose, so they count only in combination — the same
# rule applied to Presidio's PERSON / LOCATION / DATE_TIME, so the two managed
# and OSS PII detectors are treated identically.
WEAK = {"NAME", "ADDRESS", "DATE_TIME", "AGE"}


class ComprehendGate:
    name = "aws-comprehend"
    version = "DetectPiiEntities"

    def __init__(self) -> None:
        import boto3

        self._client = boto3.client(
            "comprehend", region_name=os.environ.get("AWS_REGION", "us-east-2")
        )
        # Fail fast at construction so a credentials problem is reported as
        # "not run" rather than scored as 49 clean misses.
        self._client.detect_pii_entities(Text="ping", LanguageCode="en")

    def scan(self, text: str) -> Verdict:
        try:
            r = self._client.detect_pii_entities(Text=text, LanguageCode="en")
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"{type(exc).__name__}: {exc}")

        hits = [e for e in r.get("Entities", []) if e.get("Score", 0) >= THRESHOLD]
        strong = [e["Type"] for e in hits if e["Type"] not in WEAK]
        weak = [e["Type"] for e in hits if e["Type"] in WEAK]

        blocked = bool(strong) or len(set(weak)) >= 2
        return Verdict(blocked=blocked, findings=sorted(set(strong + weak)))
