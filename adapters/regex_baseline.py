"""The control: about thirty lines of regex, the kind of thing a team writes in
an afternoon when they decide they need "some PII filtering".

It exists so every other contestant has to beat something. A commercial product
that does not clearly outperform this is not earning its price, and an OSS
library that does not is not earning its dependency. Including a control is also
the cheapest defence against a rigged-looking benchmark: if our own scanner only
narrowly beats thirty lines of regex, that shows up here too.
"""
import re

from .base import Verdict

PATTERNS = {
    "us_ssn":            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card":       re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "email":             re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b"),
    "phone":             re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
    "openai_key":        re.compile(r"\bsk-[A-Za-z0-9-]{20,}\b"),
    "aws_key":           re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token":      re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"),
    "private_key":       re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "connection_string": re.compile(r"\b\w+://[^\s:]+:[^\s@]+@\S+"),
}


class RegexBaseline:
    name = "regex-baseline"
    version = "1.0"

    def scan(self, text: str) -> Verdict:
        hits = [n for n, rx in PATTERNS.items() if rx.search(text)]
        return Verdict(blocked=bool(hits), findings=hits)
