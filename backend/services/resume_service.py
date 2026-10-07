"""Deterministic, local resume text extraction and claim/evidence parsing."""

from __future__ import annotations

from io import BytesIO
import re
from typing import Any


SKILL_CONFIG: dict[str, dict[str, Any]] = {
    "Python": {"slug": "python", "aliases": [r"\bpython(?:3)?\b", r"\bpandas\b", r"\bnumpy\b", r"\bscikit[- ]learn\b"]},
    "SQL": {"slug": "sql", "aliases": [r"\bsql\b", r"\bmysql\b", r"\bpostgres(?:ql)?\b"]},
    "JavaScript": {"slug": "javascript", "aliases": [r"\bjavascript\b", r"\bjs\b"]},
    "TypeScript": {"slug": "typescript", "aliases": [r"\btypescript\b"]},
    "Go": {"slug": "go", "aliases": [r"\bgolang\b", r"(?-i:\bGo\b)"]},
    "Rust": {"slug": "rust", "aliases": [r"\brust\b"]},
    "C++": {"slug": "cpp", "aliases": [r"\bc\+\+(?!\w)"]},
    "Machine Learning": {"slug": "ml", "aliases": [r"\bmachine[ -]learning\b", r"\bml\b", r"\bscikit[- ]learn\b"]},
    "AWS": {"slug": "aws", "aliases": [r"\baws\b", r"\bamazon web services\b"]},
}

ASSESSABLE_SKILLS = {"python", "sql", "javascript", "typescript", "go", "rust", "cpp", "ml", "aws"}
NOT_CLAIMED = re.compile(r"\b(?:wouldn['’]t|would not|don['’]t|do not)\s+call\s+(?:it|them)\s+(?:a\s+)?skill\b", re.I)

LEVELS = {
    # "Learning" is intentionally not a level by itself: in phrases like
    # "Machine Learning / Deep Learning / Expert" it is a technology name.
    "Beginner": [r"\bbeginner\b", r"\bbasics?\b", r"\bfamiliar\b"],
    "Intermediate": [r"\bintermediate\b", r"\bproficient\b", r"\bworking knowledge\b", r"\bcomfortable(?:[- ]ish)?\b"],
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
    # Keep line breaks because skills and proficiency descriptions often share
    # a visual row in resumes. Repair common PDF encoding artifacts locally.
    return (
        "\n".join(page.extract_text(extraction_mode="layout") or "" for page in reader.pages)
        .replace("\ufffd", " ")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .strip()
    )


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


SECTION_HEADERS = {
    "experience": SECTION_EXPERIENCE,
    "projects": SECTION_PROJECT,
    "certifications": SECTION_CERT,
    "education": re.compile(r"^education\s*:?$", re.I),
}


def _section_by_header(line: str) -> str | None:
    for name, pattern in SECTION_HEADERS.items():
        if pattern.fullmatch(line.strip(" •\t-–—")):
            return name
    return None


def parse_resume(text: str) -> dict[str, Any]:
    """Build normalized claims and literal resume excerpts without an LLM."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufffd", " ")
    raw_lines = normalized.splitlines()
    indexed_lines = [(index, line.strip()) for index, line in enumerate(raw_lines) if line.strip()]
    lines = [line for _, line in indexed_lines]
    raw_line_indexes = [index for index, _ in indexed_lines]
    section_by_line: list[str | None] = []
    active_section: str | None = None
    for line in lines:
        new_section = _section_by_header(line)
        if new_section:
            active_section = new_section
        elif re.fullmatch(r"(?:technical\s+)?skills?|skill\s+level|other\s+things|references", line.strip(" •\t-–—"), re.I):
            active_section = "skills" if "skill" in line.casefold() else None
        section_by_line.append(active_section)
    name = "Candidate"
    for line in lines[:12]:
        match = re.match(r"^(?:name\s*:\s*)?([A-Z][A-Za-z' .-]{2,55})$", line)
        if match and not re.search(r"resume|curriculum vitae|contact|email|phone|linkedin", line, re.I):
            name = re.sub(r"\s+[-–—]\s+CV(?:\s+\(Underclaimed\))?$", "", match.group(1).strip(), flags=re.I)
            break
        labeled = re.match(r"^name\s*:\s*(.+)$", line, re.I)
        if labeled:
            name = labeled.group(1).strip()[:80]
            break
    education = next((line.split(":", 1)[1].strip() for line in lines if re.match(r"^education\s*:", line, re.I)), None)
    if not education:
        education_lines = [line for line, section in zip(lines, section_by_line) if section == "education" and not _section_by_header(line)]
        education_parts: list[str] = []
        for line in education_lines:
            if education_parts and not re.search(r"[.!?)]$", education_parts[-1]) and re.match(r"[a-z]", line):
                education_parts[-1] += f" {line}"
            else:
                education_parts.append(line)
        education = "; ".join(education_parts) or None
    claims = []
    for skill in SKILL_CONFIG:
        matches = _skill_matches(skill, normalized)
        if not matches:
            continue
        levels = [_level_near(normalized, match.start()) for match in matches]
        skill_section_levels: list[str] = []
        excerpts: list[str] = []
        claim_excerpt: str | None = None
        claim_not_asserted = False
        details: list[str] = []
        for line_index, line in enumerate(lines):
            line_matches = _skill_matches(skill, line)
            if not line_matches:
                continue
            section = section_by_line[line_index]
            section_project = section == "projects"
            section_experience = section == "experience"
            section_certification = section == "certifications"
            contextual = bool(ACTION_TERMS.search(line)) or section_project or section_experience or section_certification
            if contextual and line not in excerpts:
                excerpts.append(line[:360])
            if section == "skills":
                line_levels = [_level_near(line, match.start()) for match in line_matches]
                effective_line_level = next((value for value in reversed(line_levels) if value != "Unspecified"), "Unspecified")
                excerpt = line[:360]
                # PDF tables can wrap one skills row onto the next physical
                # line. Inherit a level only when there is no blank line
                # between them; separate rows in these resumes have spacing.
                raw_index = raw_line_indexes[line_index]
                if (effective_line_level == "Unspecified" and raw_index > 0
                        and raw_lines[raw_index - 1].strip()
                        and line_index > 0 and section_by_line[line_index - 1] == "skills"):
                    previous_line = raw_lines[raw_index - 1].strip()
                    previous_level = _level_near(previous_line, max(0, len(previous_line) - 1))
                    if previous_level != "Unspecified":
                        effective_line_level = previous_level
                        excerpt = f"{previous_line} {line}"[:360]
                if effective_line_level != "Unspecified":
                    skill_section_levels.append(effective_line_level)
                    claim_excerpt = excerpt
                    claim_not_asserted = bool(NOT_CLAIMED.search(line))
                elif claim_excerpt is None:
                    claim_excerpt = excerpt
                    claim_not_asserted = bool(NOT_CLAIMED.search(line))
            low = line.lower()
            if section_project or re.search(r"\bproject\b", low):
                details.append("Project evidence identified in a relevant resume excerpt (+20 per item, up to 40).")
            if section_experience or re.search(r"\b(experience|internship|intern)\b", low):
                details.append("Experience evidence identified in a relevant resume excerpt (+12.5 per item, up to 25).")
            if section_certification or re.search(r"\b(certification|certified|certificate)\b", low):
                details.append("Certification evidence identified in a relevant resume excerpt (+15 per item, up to 15).")
            if re.search(r"\b(tool|implemented|built|developed|deployed|analy[sz]ed|trained|created)\b", low):
                details.append("Tool or implementation evidence identified in a relevant resume excerpt (+10 per item, up to 20).")
        # The skills section is the candidate's direct claim. Use prose elsewhere
        # only as a fallback so an unrelated nearby word cannot override it.
        explicit = next((level for level in reversed(skill_section_levels) if level != "Unspecified"), None)
        if explicit is None:
            explicit = next((level for level in reversed(levels) if level != "Unspecified"), "Unspecified")
        claims.append({
            "skill": skill,
            "slug": SKILL_CONFIG[skill]["slug"],
            "claimed_level": explicit,
            "claim_excerpt": claim_excerpt,
            "claim_not_asserted": claim_not_asserted,
            "assessment_supported": SKILL_CONFIG[skill]["slug"] in ASSESSABLE_SKILLS,
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
