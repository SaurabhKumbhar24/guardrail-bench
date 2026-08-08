"""Nightfall AI — DLP built for AI pipelines.

Nightfall requires you to name the detectors you want; there is no "everything"
default. That makes the detector list a real configuration choice, so it is
stated here in full rather than buried.

The list covers **both PII and secrets**, because Nightfall ships credential
detectors and a benchmark that only enabled PII ones would hand it Presidio's
0/7 on the secret categories through our own omission rather than any limit of
the product.

`minConfidence` is POSSIBLE — Nightfall's most inclusive setting. That maximises
recall and will also surface any false alarms it has, which is the honest way to
run a detector whose threshold we do not otherwise tune.

Reads NIGHTFALL_API_KEY from the environment. Skipped and reported if absent.

Note before publishing: check Nightfall's terms on published benchmarking.
"""
import os
import time

import requests

from .base import Verdict

ENDPOINT = "https://api.nightfall.ai/v3/scan"
TIMEOUT = 40

# Every name here was validated against the live API one at a time; the service
# 422s the whole rule if any single detector name is wrong, which would otherwise
# have shown up as Nightfall "not running" rather than as a typo of ours.
DETECTORS = [
    # PII
    "US_SOCIAL_SECURITY_NUMBER", "CREDIT_CARD_NUMBER", "EMAIL_ADDRESS",
    "PHONE_NUMBER", "IP_ADDRESS", "US_PASSPORT", "US_DRIVERS_LICENSE_NUMBER",
    "IBAN_CODE", "DATE_OF_BIRTH",
    # Secrets / credentials
    "API_KEY", "CRYPTOGRAPHIC_KEY", "PASSWORD_IN_CODE", "PASSWORD",
    "ENCRYPTION_KEY", "DATABASE_CONNECTION_STRING",
]


def _rule() -> dict:
    return {
        "detectionRules": [{
            "name": "bench",
            "logicalOp": "ANY",
            "detectors": [
                {
                    "minConfidence": "POSSIBLE",
                    "minNumFindings": 1,
                    "displayName": d.lower(),
                    "detectorType": "NIGHTFALL_DETECTOR",
                    "nightfallDetector": d,
                }
                for d in DETECTORS
            ],
        }]
    }


class NightfallGate:
    name = "nightfall"
    version = "v3/scan"

    def __init__(self) -> None:
        self._key = os.environ.get("NIGHTFALL_API_KEY", "").strip()
        if not self._key:
            raise RuntimeError("NIGHTFALL_API_KEY not set")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        })
        self._config = _rule()
        r = self._session.post(
            ENDPOINT, json={"payload": ["ping"], "config": self._config}, timeout=TIMEOUT
        )
        if r.status_code >= 400:
            # A rejected detector name shows up here rather than as 49 quiet
            # misses, which is the whole point of validating at construction.
            raise RuntimeError(f"config/auth check failed {r.status_code}: {r.text[:200]}")

    def scan(self, text: str) -> Verdict:
        # Nightfall rate-limits hard on smaller plans. Without backoff a large
        # corpus produces mostly 429s, and a rate-limited score is not a
        # capability measurement — it would have ranked Nightfall last for a
        # reason that has nothing to do with detection quality.
        delay = 1.0
        last = ""
        for attempt in range(6):
            try:
                r = self._session.post(
                    ENDPOINT, json={"payload": [text], "config": self._config},
                    timeout=TIMEOUT,
                )
            except Exception as exc:  # noqa: BLE001
                last = f"{type(exc).__name__}: {exc}"
                time.sleep(delay); delay *= 2
                continue

            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After") or delay)
                time.sleep(min(wait, 30.0))
                delay = min(delay * 2, 30.0)
                last = "HTTP 429 rate limit"
                continue
            if r.status_code >= 400:
                return Verdict(False, [], f"HTTP {r.status_code}: {r.text[:120]}")
            try:
                d = r.json()
                break
            except Exception as exc:  # noqa: BLE001
                return Verdict(False, [], f"decode: {type(exc).__name__}: {exc}")
        else:
            return Verdict(False, [], f"gave up after retries: {last}")

        # findings is a list per payload item; we send exactly one.
        groups = d.get("findings") or []
        hits = groups[0] if groups else []
        names = sorted({(f.get("detector") or {}).get("name", "?") for f in hits})
        return Verdict(blocked=bool(hits), findings=names[:8])
