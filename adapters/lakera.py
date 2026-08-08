"""Lakera Guard — the best-known dedicated LLM guardrail product.

Uses the v2 `/v2/guard` endpoint, which takes a messages array and returns a
single `flagged` boolean plus a per-detector breakdown. The corpus text is sent
as an **assistant** turn, because that is what it is: something the model is
about to say. Sending it as a user turn would be asking Lakera to judge it as an
incoming attack, which is a different product question and would misrepresent it.

Stock configuration — no policy or project id, no threshold overrides. Reads
LAKERA_API_KEY from the environment; the adapter is skipped and reported if it is
absent, never scored as zero.

Note before publishing: check Lakera's terms on published benchmarking.
"""
import os

import requests

from .base import Verdict

ENDPOINT = os.environ.get("LAKERA_ENDPOINT", "https://api.lakera.ai/v2/guard")

# Which turn the corpus text is presented as. "assistant" for output-side
# corpora (something the model is about to say); "user" for input-side ones
# (something a user just sent). Getting this wrong asks the product a different
# question than the corpus is posing, so it is explicit rather than assumed.
ROLE = os.environ.get("LAKERA_ROLE", "assistant")
TIMEOUT = 30


class LakeraGate:
    name = "lakera-guard"
    version = "v2/guard"

    def __repr__(self) -> str:
        return f"<LakeraGate role={ROLE}>"

    def __init__(self) -> None:
        self._key = os.environ.get("LAKERA_API_KEY", "").strip()
        if not self._key:
            raise RuntimeError("LAKERA_API_KEY not set")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        })
        # Prove the credential works before scoring anything.
        r = self._session.post(
            ENDPOINT, json={"messages": [{"role": ROLE, "content": "ping"}]},
            timeout=TIMEOUT,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"auth check failed {r.status_code}: {r.text[:160]}")

    def scan(self, text: str) -> Verdict:
        try:
            r = self._session.post(
                ENDPOINT,
                json={"messages": [{"role": ROLE, "content": text}], "breakdown": True},
                timeout=TIMEOUT,
            )
            if r.status_code >= 400:
                return Verdict(False, [], f"HTTP {r.status_code}: {r.text[:120]}")
            d = r.json()
        except Exception as exc:  # noqa: BLE001
            return Verdict(False, [], f"{type(exc).__name__}: {exc}")

        flagged = bool(d.get("flagged"))
        findings = []
        for b in d.get("breakdown", []) or []:
            if b.get("detected"):
                findings.append(str(b.get("detector_type") or b.get("policy_id") or "detected"))
        return Verdict(blocked=flagged, findings=sorted(set(findings))[:8])
