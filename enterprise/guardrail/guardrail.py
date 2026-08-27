"""
Guardrail (Model Armor pattern)
==================================
Inline guardrails to block prompt injection, tool poisoning, and PII
leaks, per the Fortified Enterprise Fleet track requirement. This is our
own lightweight implementation of the pattern Google's managed Model Armor
product provides - fleet reports and near-miss descriptions are free-text
fields that ultimately reach an LLM, so they're treated as untrusted input
and screened here before that happens.

In a production deployment on Google Cloud, this module's checks are what
you'd configure as Model Armor policies in front of the Vertex AI/Gemini
endpoint instead of hand-rolling them - we implement the pattern ourselves
here since the managed product requires a billing-enabled project.
"""

from __future__ import annotations
import re

# Patterns that suggest an attempt to override agent instructions via
# untrusted text (e.g. a near-miss report description, a compliance note).
_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above)",
    r"you are now",
    r"system prompt",
    r"act as (if you|a different)",
    r"new instructions:",
]

# Coarse PII patterns - not exhaustive, but catches the common cases that
# should never flow into a narrative sent to an external model unredacted.
_PII_PATTERNS = {
    "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "phone": r"\b\+?\d[\d\-\s()]{7,}\d\b",
    "passport_like": r"\b[A-Z]{1,2}\d{6,9}\b",
}


class GuardrailViolation(Exception):
    """Raised when input text fails the guardrail check."""
    def __init__(self, reason: str, field: str):
        self.reason = reason
        self.field = field
        super().__init__(f"Guardrail blocked '{field}': {reason}")


def check_for_injection(text: str, field_name: str = "input") -> None:
    """Raises GuardrailViolation if text matches a known prompt-injection
    pattern. Call this on any free-text field before it reaches an agent
    or LLM call."""
    lowered = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            raise GuardrailViolation(
                f"text matches a known prompt-injection pattern ('{pattern}')", field_name
            )


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Returns (redacted_text, list_of_pii_types_found). Never raises -
    PII gets redacted rather than blocking the whole request, since a
    fleet report might legitimately reference a contact number that
    should be masked, not rejected outright."""
    found = []
    redacted = text
    for pii_type, pattern in _PII_PATTERNS.items():
        if re.search(pattern, redacted):
            found.append(pii_type)
            redacted = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", redacted)
    return redacted, found


def screen_input(text: str, field_name: str = "input") -> str:
    """The combined guardrail entry point: checks for injection (raises if
    found), then redacts any PII (never raises). Returns the safe-to-use
    text. This is what api/investigate.py and the agent tool wrappers call
    on any field sourced from untrusted free text."""
    check_for_injection(text, field_name)
    redacted, _ = redact_pii(text)
    return redacted
