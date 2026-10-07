"""Transparent prototype scoring and pure claim/verification comparisons."""

LEVEL_ORDER = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}


def score_evidence(details: list[str], snippets: list[str]) -> dict:
    """Repeatable heuristic capped by evidence category; not a validated measure."""
    project = min(40, 20 * sum("Project evidence" in detail for detail in details))
    experience = min(25, 12.5 * sum("Experience evidence" in detail for detail in details))
    certification = min(15, 15 * sum("Certification evidence" in detail for detail in details))
    implementation = min(20, 10 * sum("Tool or implementation" in detail for detail in details))
    score = round(project + experience + certification + implementation, 1)
    return {"score": score, "details": details or ["No qualifying project, work, certification, or implementation evidence was found."], "evidence_snippets": snippets}


def final_score(evidence_score: float, test_score: float) -> float:
    return round(0.4 * evidence_score + 0.6 * test_score, 1)


def verified_level(score: float) -> str:
    if score < 40:
        return "Beginner"
    if score <= 70:
        return "Intermediate"
    return "Advanced"


def classify(claimed_level: str, verified: str) -> str:
    """Compare levels; an unspecified claim remains explicitly unverified."""
    if claimed_level not in LEVEL_ORDER:
        return "unverified"
    difference = LEVEL_ORDER[verified] - LEVEL_ORDER[claimed_level]
    return "underclaimed" if difference > 0 else "overclaimed" if difference < 0 else "confirmed"


def build_result(claim: dict, test_score: float) -> dict:
    evidence = score_evidence(claim.get("evidence_details", []), claim.get("evidence_snippets", []))
    total = final_score(evidence["score"], test_score)
    level = verified_level(total)
    status = classify(claim["claimed_level"], level)
    explanation = (
        f"Prototype heuristic evidence {evidence['score']:.1f} × 0.4 + local assessment {test_score:.1f} × 0.6 "
        f"= {total:.1f}. The score bands map to {level}; claim comparison is {status}."
    )
    return {"skill": claim["skill"], "claimed_level": claim["claimed_level"], "evidence_score": evidence["score"],
            "test_score": round(test_score, 1), "final_score": total, "verified_level": None if status == "unverified" else level,
            "status": status, "evidence_snippets": evidence["evidence_snippets"], "evidence_details": evidence["details"], "explanation": explanation}
