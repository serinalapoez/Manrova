"""
Manrova - Contextual Risk Fusion
==================================
Deterministic scoring so the "why was this escalated" explanation is always
reproducible and auditable - the LLM layer explains the fusion result in
natural language, it does not compute it.
"""

from core.domain.models import Severity, RiskAssessment

_SEVERITY_WEIGHT = {
    Severity.NONE: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}

_WEIGHTS = {
    "nav": 0.40,
    "crew": 0.20,
    "historical": 0.20,
    "compliance": 0.20,
}


def _score(sev: Severity) -> float:
    return _SEVERITY_WEIGHT[sev] / 4.0


def _band(score: float) -> Severity:
    if score >= 0.80:
        return Severity.CRITICAL
    if score >= 0.60:
        return Severity.HIGH
    if score >= 0.35:
        return Severity.MEDIUM
    if score >= 0.10:
        return Severity.LOW
    return Severity.NONE


def fuse_risk(
    nav_risk: Severity,
    crew_risk: Severity,
    historical_similarity: Severity,
    compliance_exposure: Severity,
    base_confidence: float,
) -> RiskAssessment:
    weighted = (
        _score(nav_risk) * _WEIGHTS["nav"]
        + _score(crew_risk) * _WEIGHTS["crew"]
        + _score(historical_similarity) * _WEIGHTS["historical"]
        + _score(compliance_exposure) * _WEIGHTS["compliance"]
    )
    overall = _band(weighted)

    explanation = []
    if nav_risk in (Severity.HIGH, Severity.CRITICAL):
        explanation.append(f"Significant navigation risk ({nav_risk.value})")
    if historical_similarity in (Severity.HIGH, Severity.CRITICAL):
        explanation.append("Similar historical fleet event found")
    if crew_risk in (Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL):
        explanation.append(f"Elevated crew readiness risk ({crew_risk.value})")
    if compliance_exposure in (Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL):
        explanation.append(f"Compliance exposure present ({compliance_exposure.value})")
    if not explanation:
        explanation.append("No significant cross-domain risk factors detected")

    # Confidence rises slightly with corroborating evidence, capped at 0.99
    corroboration_bonus = 0.02 * sum(
        1 for s in (nav_risk, crew_risk, historical_similarity, compliance_exposure)
        if s not in (Severity.NONE,)
    )
    confidence = min(0.99, round(base_confidence + corroboration_bonus, 2))

    return RiskAssessment(
        nav_risk=nav_risk,
        crew_risk=crew_risk,
        historical_similarity=historical_similarity,
        compliance_exposure=compliance_exposure,
        overall_severity=overall,
        confidence=confidence,
        explanation=explanation,
    )
