"""
Tenancy
=========
Genuine multi-tenant data isolation: any shipping company can register,
add their own vessels (real or anonymized/coded names - a company may not
want to disclose a real hull name), and run investigations on their own
real data. Backed by Firestore, same free Spark plan as the Memory Bank
and Agent Registry.

Scope decision: access-code based, not full password/email authentication.
A company gets a private access code on registration and uses it to
return - this gives genuine data isolation between tenants (the actual
requirement) without the added build time of a full auth system, which
wasn't the bottleneck this was solving.
"""

from __future__ import annotations
import secrets
import string
from datetime import datetime, timezone

from enterprise._gcp_auth import get_firestore_client

_COMPANIES = "manrova_companies"
_VESSELS = "manrova_vessels"

# In-memory fallback, mirrors the pattern used in memory/firestore_bank.py
_fallback_companies: dict[str, dict] = {}
_fallback_vessels: dict[str, dict] = {}


def _generate_access_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3))


def register_company(display_name: str = "") -> dict:
    """Creates a new tenant. Returns {company_id, access_code}. The
    access_code is the only credential - store it, it can't be recovered."""
    access_code = _generate_access_code()
    company_id = access_code.replace("-", "").lower()
    record = {
        "company_id": company_id,
        "access_code": access_code,
        "display_name": display_name or "Unnamed Fleet Operator",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    client = get_firestore_client()
    if client is None:
        _fallback_companies[access_code] = record
    else:
        client.collection(_COMPANIES).document(company_id).set(record)

    return record


def lookup_company(access_code: str) -> dict | None:
    """Returns the company record for an access code, or None if invalid."""
    client = get_firestore_client()
    if client is None:
        return _fallback_companies.get(access_code)

    company_id = access_code.replace("-", "").lower()
    doc = client.collection(_COMPANIES).document(company_id).get()
    if not doc.exists:
        return None
    record = doc.to_dict()
    if record.get("access_code") != access_code:
        return None  # defends against a guessed/mistyped code matching a different id
    return record


def register_vessel(company_id: str, name: str, vessel_class: str = "unspecified") -> dict:
    """Adds a vessel under a company. `name` can be a real vessel name or
    an internal code/alias - Manrova never requires a real name."""
    vessel_id = f"{company_id}-{secrets.token_hex(3)}"
    record = {
        "vessel_id": vessel_id,
        "company_id": company_id,
        "name": name,
        "vessel_class": vessel_class,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    client = get_firestore_client()
    if client is None:
        _fallback_vessels[vessel_id] = record
    else:
        client.collection(_VESSELS).document(vessel_id).set(record)

    return record


def list_vessels(company_id: str) -> list[dict]:
    client = get_firestore_client()
    if client is None:
        return [v for v in _fallback_vessels.values() if v["company_id"] == company_id]

    query = client.collection(_VESSELS).where("company_id", "==", company_id)
    return [doc.to_dict() for doc in query.stream()]
