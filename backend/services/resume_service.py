"""Deterministic, local resume text extraction and claim/evidence parsing."""

from __future__ import annotations

from io import BytesIO
import re
from typing import Any


SKILL_CONFIG: dict[str, dict[str, Any]] = {
    "Python": {"slug": "python", "aliases": [r"\bpython(?:3)?\b", r"\bpandas\b", r"\bnumpy\b", r"\bscikit[- ]learn\b"]},
    "SQL": {"slug": "sql", "aliases": [r"\bsql\b", r"\bmysql\b", r"\bpostgres(?:ql)?\b"]},
    "Machine Learning": {"slug": "ml", "aliases": [r"\bmachine[ -]learning\b", r"\bml\b", r"\bscikit[- ]learn\b"]},
}

LEVELS = {
    "Beginner": [r"\bbeginner\b", r"\bbasic\b", r"\bfamiliar\b", r"\blearning\b"],
    "Intermediate": [r"\bintermediate\b", r"\bproficient\b", r"\bworking knowledge\b"],
    "Advanced": [r"\badvanced\b", r"\bexpert\b", r"\bextensive\b", r"\bstrong\b"],
}
ACTION_TERMS = re.compile(
    r"\b(project|experience|internship|certification|certificate|tools?|implementation|built|developed|deployed|analy[sz]ed|trained|created)\b",
    re.I,
)
SECTION_PROJECT = re.compile(r"^(selected\s+)?projects?\s*:?[\s]*$", re.I)
SECTION_CERT = re.compile(r"^(certifications?|certificates?)\s*:?[\s]*$", re.I)
SECTION_EXPERIENCE = re.compile(r"^(work\s+)?(experience|internships?)\s*:?[\s]*$", re.I)


def extract_pdf_text(payload: bytes) -> str:
    """Extract selectable text from a local PDF using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on the install environment
        raise RuntimeError("PDF support requires the local pypdf dependency. Install requirements.txt.") from exc
    reader = PdfReader(BytesIO(payload), strict=False)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _skill_matches(skill: str, text: str) -> list[re.Match[str]]:
    matches = []
    for alias in SKILL_CONFIG[skill]["aliases"]:
        matches.extend(re.finditer(alias, text, re.I))
    return sorted(matches, key=lambda item: item.start())


def _level_near(text: str, position: int, window: int = 100) -> str:
    left = max(0, position - window)
    line_start = text.rfind("\n", left, position) + 1
    line_end = text.find("\n", position)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end]
    # A level must share the skill's line so a nearby level for another skill
    # cannot be silently inherited.
    search_text = line
    relative_position = position - line_start
    found: list[tuple[int, int, str]] = []
    for level, patterns in LEVELS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, search_text, re.I):
                # "learning" is an alias, but not when it is the second word
                # of the skill name "Machine Learning".
                if level == "Beginner" and match.group(0).casefold() == "learning" and re.search(r"machine[ -]$", search_text[max(0, match.start() - 9):match.start()], re.I):
                    continue
                found.append((abs(match.start() - relative_position), match.start(), level))
    return min(found)[2] if found else "Unspecified"


def _extract_sections(lines: list[str], header_pattern: re.Pattern[str]) -> list[str]:
    found: list[str] = []
    active = False
    other_header = re.compile(r"^[A-Z][A-Za-z &/()-]{1,35}:?$")
    for line in lines:
        stripped = line.strip(" •\t-–—")
        if not stripped:
            continue
        if header_pattern.fullmatch(stripped):
            active = True
            continue
        if active and other_header.fullmatch(stripped) and len(stripped.split()) <= 4:
            active = False
        elif active and re.match(r"^\s*(?:[-•*]|\d+[.)])\s+", line):
            found.append(line.strip())
    return found[:12]


def parse_resume(text: str) -> dict[str, Any]:
    """Build normalized claims and literal resume excerpts without an LLM."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    name = "Candidate"
    for line in lines[:12]:
        match = re.match(r"^(?:name\s*:\s*)?([A-Z][A-Za-z' .-]{2,55})$", line)
        if match and not re.search(r"resume|curriculum vitae|contact|email|phone|linkedin", line, re.I):
            name = match.group(1).strip()
            break
        labeled = re.match(r"^name\s*:\s*(.+)$", line, re.I)
        if labeled:
            name = labeled.group(1).strip()[:80]
            break
    education = next((line.split(":", 1)[1].strip() for line in lines if re.match(r"^education\s*:", line, re.I)), None)
    claims = []
    for skill in SKILL_CONFIG:
        matches = _skill_matches(skill, normalized)
        if not matches:
            continue
        levels = [_level_near(normalized, match.start()) for match in matches]
        # Prefer the last explicit level attached to a mention. In ordinary
        # resumes this is the skills-list declaration after project details.
        explicit = next((level for level in reversed(levels) if level != "Unspecified"), "Unspecified")
        excerpts: list[str] = []
        details: list[str] = []
        for line_index, line in enumerate(lines):
            if not _skill_matches(skill, line):
                continue
            preceding = [prev.strip(" •\t-–—") for prev in lines[max(0, line_index - 3):line_index]]
            section_project = any(SECTION_PROJECT.fullmatch(prev) for prev in preceding)
            section_experience = any(SECTION_EXPERIENCE.fullmatch(prev) for prev in preceding)
            section_certification = any(SECTION_CERT.fullmatch(prev) for prev in preceding)
            contextual = bool(ACTION_TERMS.search(line)) or section_project or section_experience or section_certification
            if contextual and line not in excerpts:
                excerpts.append(line[:360])
            low = line.lower()
            if section_project or re.search(r"\bproject\b", low):
                details.append("Project evidence identified in a relevant resume excerpt (+20 per item, up to 40).")
            if section_experience or re.search(r"\b(experience|internship|intern)\b", low):
                details.append("Experience evidence identified in a relevant resume excerpt (+12.5 per item, up to 25).")
            if section_certification or re.search(r"\b(certification|certified|certificate)\b", low):
                details.append("Certification evidence identified in a relevant resume excerpt (+15 per item, up to 15).")
            if re.search(r"\b(tool|implemented|built|developed|deployed|analy[sz]ed|trained|created)\b", low):
                details.append("Tool or implementation evidence identified in a relevant resume excerpt (+10 per item, up to 20).")
        claims.append({
            "skill": skill,
            "slug": SKILL_CONFIG[skill]["slug"],
            "claimed_level": explicit,
            "evidence_snippets": excerpts[:8],
            "evidence_details": details,
        })
    return {
        "name": name,
        "education": education,
        "skills": claims,
        "projects": _extract_sections(lines, SECTION_PROJECT),
        "certifications": _extract_sections(lines, SECTION_CERT),
    }
