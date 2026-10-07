from __future__ import annotations

import re
from typing import Any

from backend.schemas.api_models import (
    TalentProfileInput,
    TalentProfileResponse,
    TalentRoleMatch,
    TalentSkillEvidence,
)


SKILL_LABELS = {
    "python": "Python",
    "sql": "SQL",
    "machine_learning": "Machine Learning",
    "statistics": "Statistics",
    "big_data": "Big Data",
    "dashboard_storytelling": "Dashboard / Storytelling",
}
SKILL_TERMS = {
    "python": ("python",),
    "sql": ("sql",),
    "machine_learning": ("machine learning", "machinelearning"),
    "statistics": ("statistics", "statistical", "statistic", "maths", "mathematics"),
    "big_data": ("big data", "bigdata", "hadoop"),
    "dashboard_storytelling": ("dashboard", "storytelling", "data visualization", "visualization", "tableau", "power bi"),
}

# Analyst-authored title/skill rules. The supplied files have no row-level join key
# or role-by-skill cross-tab, so these rules are not learned from the data.
ROLE_SKILLS = {
    "business analyst": ("sql", "statistics", "dashboard_storytelling"),
    "data analyst": ("sql", "statistics", "dashboard_storytelling", "python"),
    "data scientist": ("python", "sql", "machine_learning", "statistics"),
    "data engineer": ("python", "sql", "big_data"),
    "machine learning engineer": ("python", "machine_learning", "statistics", "big_data"),
    "data architect": ("sql", "big_data"),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


class TalentProfileService:
    def analyze(self, request: TalentProfileInput, market_summary: dict[str, Any]) -> TalentProfileResponse:
        vocabulary = market_summary.get("skill_vocabulary") or market_summary.get("top_skills", [])
        frequencies: dict[str, int] = {}
        for item in vocabulary:
            normalized = _normalize(str(item.get("name", "")))
            if normalized:
                frequencies[normalized] = frequencies.get(normalized, 0) + int(item.get("count", 0))
        evidence: list[TalentSkillEvidence] = []
        for key in request.skills:
            terms = SKILL_TERMS[key]
            supporting = [term for term in terms if frequencies.get(_normalize(term), 0) > 0]
            count = sum(frequencies.get(_normalize(term), 0) for term in supporting)
            evidence.append(TalentSkillEvidence(
                skill=key,
                label=SKILL_LABELS[key],
                matched=bool(supporting),
                frequency=count,
                supporting_terms=supporting,
            ))

        matched = [item for item in evidence if item.matched]
        unmatched = [item for item in evidence if not item.matched]
        overlap_percent = 100.0 * len(matched) / len(evidence) if evidence else 0.0

        matched_keys = {item.skill for item in matched}
        high_demand = []
        for item in (market_summary.get("top_skills") or [])[:10]:
            name = str(item.get("name", ""))
            normalized = _normalize(name)
            category = next((key for key, terms in SKILL_TERMS.items() if any(_normalize(term) == normalized for term in terms)), None)
            if category not in matched_keys:
                high_demand.append({"name": name, "count": int(item.get("count", 0))})

        role_matches: list[TalentRoleMatch] = []
        for item in market_summary.get("top_roles", []):
            role_name = str(item.get("name", ""))
            normalized_role = _normalize(role_name)
            rule_key = next((key for key in ROLE_SKILLS if key in normalized_role), None)
            if not rule_key:
                continue
            rule = ROLE_SKILLS[rule_key]
            role_overlap = [key for key in rule if key in matched_keys]
            if not role_overlap:
                continue
            role_matches.append(TalentRoleMatch(
                role=role_name,
                role_frequency=int(item.get("count", 0)),
                overlap_percent=100.0 * len(role_overlap) / len(rule),
                matched_skills=[SKILL_LABELS[key] for key in role_overlap],
                role_skill_rule=[SKILL_LABELS[key] for key in rule],
            ))
        role_matches.sort(key=lambda match: (-match.overlap_percent, -match.role_frequency, match.role))

        return TalentProfileResponse(
            title="Descriptive job-market alignment",
            analysis_type="descriptive_overlap",
            overlap_percent=round(overlap_percent, 1),
            profile_skill_count=len(evidence),
            matched_skills=matched,
            unmatched_profile_skills=unmatched,
            missing_high_demand_skills=high_demand,
            top_role_categories=role_matches[:5],
            explanation="This is a descriptive overlap analysis based on supplied job-posting data; it is not a hiring probability.",
            role_matching_note="Role ordering uses analyst-authored title-to-skill rules and source role frequencies. The job files have no row-level join key or role-by-skill cross-tab, so these are heuristic suggestions, not observed role-specific skill matches.",
            skill_frequency_note="Skill mention counts come from the Analytics Jobs key_skills field; DataScience Jobs has no extracted skill field and contributes no skill mentions to this vocabulary.",
            limitations=[
                "The overlap percent counts selected skill categories with at least one matching normalized vocabulary term; it is not a fit score or prediction.",
                "Skill frequencies are normalized mentions in the supplied postings, not unique people or unique jobs.",
                "Role suggestions use explicit analyst-authored title rules because the sources cannot link each skill mention to a role.",
            ],
        )
