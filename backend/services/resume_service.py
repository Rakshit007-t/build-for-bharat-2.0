"""Deterministic, local resume text extraction and claim/evidence parsing."""

from __future__ import annotations

from io import BytesIO
import re
from typing import Any
from backend.services.verification_service import score_evidence


SKILL_CONFIG: dict[str, dict[str, Any]] = {
    # Core DevOps, Cloud & Infrastructure
    "AWS": {
        "slug": "aws",
        "category": "Cloud Platforms",
        "aliases": [r"\baws\b", r"\bamazon web services\b", r"\bec2\b", r"\brds\b", r"\becs\b", r"\becr\b", r"\bs3\b", r"\bcloudwatch\b", r"\bsecrets manager\b"],
    },
    "Azure": {
        "slug": "azure",
        "category": "Cloud Platforms",
        "aliases": [r"\bazure\b", r"\bmicrosoft azure\b"],
    },
    "DigitalOcean": {
        "slug": "digitalocean",
        "category": "Cloud Platforms",
        "aliases": [r"\bdigitalocean\b", r"\bdigital ocean\b"],
    },
    "Hostinger": {
        "slug": "hostinger",
        "category": "Cloud Platforms",
        "aliases": [r"\bhostinger\b"],
    },
    "Docker": {
        "slug": "docker",
        "category": "CI/CD & Containers",
        "aliases": [r"\bdocker\b", r"\bdockerfiles?\b"],
    },
    "Kubernetes": {
        "slug": "kubernetes",
        "category": "CI/CD & Containers",
        "aliases": [r"\bkubernetes\b", r"\bk8s\b"],
    },
    "Terraform": {
        "slug": "terraform",
        "category": "Infrastructure as Code",
        "aliases": [r"\bterraform\b"],
    },
    "Ansible": {
        "slug": "ansible",
        "category": "Infrastructure as Code",
        "aliases": [r"\bansible\b"],
    },
    "Jenkins": {
        "slug": "jenkins",
        "category": "CI/CD & Containers",
        "aliases": [r"\bjenkins\b"],
    },
    "GitHub Actions": {
        "slug": "github-actions",
        "category": "CI/CD & Containers",
        "aliases": [r"\bgithub actions\b"],
    },
    "CI/CD": {
        "slug": "cicd",
        "category": "CI/CD & Containers",
        "aliases": [r"\bci[/-]cd\b", r"\bcontinuous integration\b", r"\bcontinuous deployment\b", r"\bpipelines?\b"],
    },
    "Git": {
        "slug": "git",
        "category": "CI/CD & Containers",
        "aliases": [r"\bgit\b(?!hub actions)", r"\bgithub\b(?! actions)", r"\bgitlab\b", r"\bbitbucket\b"],
    },
    "JFrog Artifactory": {
        "slug": "jfrog",
        "category": "CI/CD & Containers",
        "aliases": [r"\bjfrog\b", r"\bartifactory\b"],
    },
    "Linux": {
        "slug": "linux",
        "category": "Infrastructure & OS",
        "aliases": [r"\blinux\b", r"\bubuntu\b", r"\bdebian\b", r"\bcentos\b", r"\bredhat\b"],
    },
    "Bash": {
        "slug": "bash",
        "category": "Infrastructure & OS",
        "aliases": [r"\bbash\b", r"\bshell scripting\b", r"\bshell script\b"],
    },
    # Monitoring, Observability & Security
    "Grafana": {
        "slug": "grafana",
        "category": "Monitoring & Observability",
        "aliases": [r"\bgrafana\b"],
    },
    "Prometheus": {
        "slug": "prometheus",
        "category": "Monitoring & Observability",
        "aliases": [r"\bprometheus\b", r"\bblackbox exporter\b"],
    },
    "ELK Stack": {
        "slug": "elk",
        "category": "Monitoring & Observability",
        "aliases": [r"\belk stack\b", r"\belasticsearch\b", r"\blogstash\b", r"\bkibana\b", r"\bfilebeat\b", r"(?-i:\bELK\b)"],
    },
    "SonarQube": {
        "slug": "sonarqube",
        "category": "Monitoring & Observability",
        "aliases": [r"\bsonarqube\b", r"\bsonar\b"],
    },
    "Nginx": {
        "slug": "nginx",
        "category": "Web Servers & Networking",
        "aliases": [r"\bnginx\b"],
    },
    "Certbot / SSL": {
        "slug": "ssl",
        "category": "Security & Networking",
        "aliases": [r"\bcertbot\b", r"\bssl\b", r"\btls\b"],
    },
    "DNS & Networking": {
        "slug": "networking",
        "category": "Security & Networking",
        "aliases": [r"\bdns\b", r"\bsmtp\b"],
    },
    "WordPress": {
        "slug": "wordpress",
        "category": "Web Applications",
        "aliases": [r"\bwordpress\b"],
    },
    # Programming Languages
    "Python": {
        "slug": "python",
        "category": "Programming Languages",
        "aliases": [r"\bpython(?:3)?\b", r"\bpandas\b", r"\bnumpy\b", r"\bscikit[- ]learn\b"],
    },
    "Java": {
        "slug": "java",
        "category": "Programming Languages",
        "aliases": [r"\bjava\b(?!script)"],
    },
    "JavaScript": {
        "slug": "javascript",
        "category": "Programming Languages",
        "aliases": [r"\bjavascript\b", r"(?<!\.)\bjs\b"],
    },
    "TypeScript": {
        "slug": "typescript",
        "category": "Programming Languages",
        "aliases": [r"\btypescript\b", r"(?<!\.)\bts\b"],
    },
    "Go": {
        "slug": "go",
        "category": "Programming Languages",
        "aliases": [r"\bgolang\b", r"(?-i:\bGo\b)"],
    },
    "Rust": {
        "slug": "rust",
        "category": "Programming Languages",
        "aliases": [r"\brust\b"],
    },
    "C++": {
        "slug": "cpp",
        "category": "Programming Languages",
        "aliases": [r"\bc\+\+(?!\w)"],
    },
    "SQL": {
        "slug": "sql",
        "category": "Databases & Storage",
        "aliases": [r"\bsql\b", r"\bmysql\b", r"\bpostgres(?:ql)?\b"],
    },
    # Web Frameworks
    "Node.js": {
        "slug": "nodejs",
        "category": "Web Frameworks",
        "aliases": [r"\bnode(?:\.js)?\b"],
    },
    "Next.js": {
        "slug": "nextjs",
        "category": "Web Frameworks",
        "aliases": [r"\bnext(?:\.js)?\b"],
    },
    "Angular": {
        "slug": "angular",
        "category": "Web Frameworks",
        "aliases": [r"\bangular\b"],
    },
    "Laravel": {
        "slug": "laravel",
        "category": "Web Frameworks",
        "aliases": [r"\blaravel\b"],
    },
    "React": {
        "slug": "react",
        "category": "Web Frameworks",
        "aliases": [r"\breact(?:\.js)?\b"],
    },
    # Data & AI
    "Machine Learning": {
        "slug": "ml",
        "category": "Data & AI",
        "aliases": [r"\bmachine[ -]learning\b", r"\bml\b", r"\bscikit[- ]learn\b"],
    },
}

ASSESSABLE_SKILLS = {
    "python", "sql", "javascript", "typescript", "go", "rust", "cpp", "ml", "aws",
    "docker", "kubernetes", "terraform", "jenkins", "ansible", "linux", "bash",
    "grafana", "prometheus", "elk", "sonarqube", "nginx", "java", "nodejs", "cicd", "git", "azure",
}

NOT_CLAIMED = re.compile(r"\b(?:wouldn['’]t|would not|don['’]t|do not)\s+call\s+(?:it|them)\s+(?:a\s+)?skill\b", re.I)

LEVELS = {
    "Beginner": [r"\bbeginner\b", r"\bbasics?\b", r"\bfamiliar\b", r"\bnovice\b", r"\bfoundational\b"],
    "Intermediate": [r"\bintermediate\b", r"\bproficient\b", r"\bworking knowledge\b", r"\bcomfortable(?:[- ]ish)?\b", r"\bpractitioner\b"],
    "Advanced": [r"\badvanced\b", r"\bexpert\b", r"\bextensive\b", r"\bstrong\b", r"\blead\b", r"\barchitect\b"],
}

ACTION_TERMS = re.compile(
    r"\b(project|experience|internship|certification|certificate|tools?|implementation|"
    r"built|develop\w*|deploy\w*|analy[sz]\w*|train\w*|creat\w*|automat\w*|manag\w*|"
    r"configur\w*|engineer\w*|streamlin\w*|monitor\w*|administr\w*|pipelin\w*|"
    r"infrastructur\w*|architect\w*|maintain\w*|patch\w*|resolv\w*|deliver\w*|"
    r"provis\w*|rotat\w*|collect\w*|support\w*|integrat\w*|scripting|alert\w*|traceab\w*)\b",
    re.I,
)

SECTION_SUMMARY = re.compile(r"^(professional\s+|career\s+)?(summary|profile|about\s+me|objective)\s*:?[\s]*$", re.I)
SECTION_PROJECT = re.compile(r"^(selected\s+)?projects?\s*:?[\s]*$", re.I)
SECTION_CERT = re.compile(r"^(certifications?|certificates?)\s*:?[\s]*$", re.I)
SECTION_EXPERIENCE = re.compile(r"^(work\s+)?(experience|internships?|employment|work\s+history)\s*:?[\s]*$", re.I)
SECTION_SKILLS = re.compile(r"^(technical\s+|core\s+)?(skills?|competencies|technologies|tools)\s*:?[\s]*$", re.I)
SECTION_EDUCATION = re.compile(r"^education\s*:?[\s]*$", re.I)

SECTION_HEADERS = {
    "summary": SECTION_SUMMARY,
    "experience": SECTION_EXPERIENCE,
    "projects": SECTION_PROJECT,
    "certifications": SECTION_CERT,
    "education": SECTION_EDUCATION,
    "skills": SECTION_SKILLS,
}


def extract_pdf_text(payload: bytes) -> str:
    """Extract selectable text from a local PDF using pypdf with layout and space fallback."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PDF support requires the local pypdf dependency. Install requirements.txt.") from exc
    reader = PdfReader(BytesIO(payload), strict=False)

    plain_pages = [page.extract_text() or "" for page in reader.pages]
    layout_pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]

    plain_text = "\n".join(plain_pages).strip()
    layout_text = "\n".join(layout_pages).strip()

    def space_density(t: str) -> float:
        return t.count(" ") / max(1, len(t))

    plain_density = space_density(plain_text)
    layout_density = space_density(layout_text)

    # Check if layout mode produced concatenated words (words > 28 chars not URLs)
    has_layout_mashed_words = any(
        len(w) > 28 and not re.search(r"https?://|www\.|@|linkedin|github", w, re.I)
        for w in layout_text.split()
    )

    if plain_density >= 0.06 and (has_layout_mashed_words or layout_density < 0.08):
        chosen = plain_text
    elif plain_density >= 0.07 and not has_layout_mashed_words:
        chosen = plain_text
    elif layout_density >= 0.08 and not has_layout_mashed_words:
        chosen = layout_text
    else:
        chosen = plain_text or layout_text

    cleaned = (
        chosen.replace("\ufffd", " ")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\u2022", "•")
        .replace("\u25cf", "•")
        .replace("\u25cb", "•")
        .strip()
    )
    # Fix words mashed together without spaces at punctuation
    cleaned = re.sub(r':([A-Za-z])', r': \1', cleaned)
    cleaned = re.sub(r',([A-Za-z])', r', \1', cleaned)
    cleaned = re.sub(r'•\s*[-–—]?\s*', r'• ', cleaned)
    return cleaned


def _skill_matches(skill: str, text: str) -> list[re.Match[str]]:
    matches = []
    for alias in SKILL_CONFIG[skill]["aliases"]:
        matches.extend(re.finditer(alias, text, re.I))
    return sorted(matches, key=lambda item: item.start())


def _level_near(text: str, position: int, window: int = 120) -> str:
    left = max(0, position - window)
    line_start = text.rfind("\n", left, position) + 1
    line_end = text.find("\n", position)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end]
    search_text = line
    relative_position = position - line_start
    found: list[tuple[int, int, str]] = []
    for level, patterns in LEVELS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, search_text, re.I):
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
        if active:
            # Check if this line starts a different section
            is_other = any(p.fullmatch(stripped) for name, p in SECTION_HEADERS.items() if p != header_pattern)
            is_generic_header = other_header.fullmatch(stripped) and len(stripped.split()) <= 4 and not re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4})\b", stripped)
            if is_other or is_generic_header:
                active = False
                continue
            found.append(line.strip())
    return found[:25]


def _section_by_header(line: str) -> str | None:
    for name, pattern in SECTION_HEADERS.items():
        if pattern.fullmatch(line.strip(" •\t-–—")):
            return name
    return None


def parse_resume(text: str) -> dict[str, Any]:
    """Build normalized claims, stepped proficiency, and evidence without external AI."""
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
        elif re.fullmatch(r"(?:technical\s+|core\s+)?skills?|skill\s+level|other\s+things|references", line.strip(" •\t-–—"), re.I):
            active_section = "skills" if "skill" in line.casefold() else None
        section_by_line.append(active_section)

    name = "Candidate"
    for line in lines[:15]:
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

    extracted_projects = _extract_sections(lines, SECTION_PROJECT)
    extracted_certs = _extract_sections(lines, SECTION_CERT)

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
        project_count = 0
        experience_count = 0
        cert_count = 0
        tool_count = 0

        # Check section matches and excerpts
        for line_index, line in enumerate(lines):
            line_matches = _skill_matches(skill, line)
            if not line_matches:
                continue
            section = section_by_line[line_index]
            section_summary = section == "summary"
            section_project = section == "projects"
            section_experience = section == "experience"
            section_certification = section == "certifications"
            section_skills = section == "skills"
            contextual = bool(ACTION_TERMS.search(line)) or section_summary or section_project or section_experience or section_certification or section_skills

            if contextual and line not in excerpts:
                excerpts.append(line[:360])

            if section_skills:
                line_levels = [_level_near(line, match.start()) for match in line_matches]
                effective_line_level = next((value for value in reversed(line_levels) if value != "Unspecified"), "Unspecified")
                excerpt = line[:360]
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
                project_count += 1
                details.append("Project evidence identified in a relevant resume excerpt (+20 per item, up to 40).")
            if section_experience or section_summary or re.search(r"\b(experience|internship|intern|engineer|developer|admin|lead|architect)\b", low):
                experience_count += 1
                details.append("Experience evidence identified in a relevant resume excerpt (+12.5 per item, up to 25).")
            if section_certification or re.search(r"\b(certification|certified|certificate)\b", low):
                cert_count += 1
                details.append("Certification evidence identified in a relevant resume excerpt (+15 per item, up to 15).")
            if re.search(r"\b(tool|implement\w*|built|develop\w*|deploy\w*|analy[sz]\w*|train\w*|creat\w*|automat\w*|manag\w*|configur\w*|engineer\w*|monitor\w*|provis\w*|streamlin\w*)\b", low):
                tool_count += 1
                details.append("Tool or implementation evidence identified in a relevant resume excerpt (+10 per item, up to 20).")

        # Cross-reference with extracted certifications if not already linked
        for cert_line in extracted_certs:
            if _skill_matches(skill, cert_line) and cert_line not in excerpts:
                excerpts.append(cert_line[:360])
                cert_count += 1
                details.append("Certification evidence identified in a relevant resume excerpt (+15 per item, up to 15).")

        # Fallback claim excerpt to first excerpt
        if not claim_excerpt and excerpts:
            claim_excerpt = excerpts[0]

        # Explicit level check
        explicit = next((level for level in reversed(skill_section_levels) if level != "Unspecified"), None)
        if explicit is None:
            explicit = next((level for level in reversed(levels) if level != "Unspecified"), None)

        # Scale signals (e.g. 50+ accounts, 200+ servers)
        scale_detected = bool(re.search(r"\b(?:\d{2,}\+|large[- ]scale|enterprise|fleet|multi[- ]account)\b", normalized, re.I)) and any(
            re.search(r"\b(?:\d{2,}\+|large[- ]scale|enterprise|fleet|multi[- ]account)\b", ex, re.I) for ex in excerpts
        )

        # Calculate evidence score
        ev_score_data = score_evidence(details, excerpts)
        ev_score = ev_score_data["score"]

        # Stepped Proficiency & Claimed Level Determination
        has_real_sections = (
            any(s in ("experience", "certifications", "projects") for s in section_by_line)
            and len(lines) >= 6
            and not re.search(r"\bno[- ]level\b", name, re.I)
        )

        if explicit and not (scale_detected and ev_score >= 60 and explicit != "Advanced"):
            final_level = explicit
            step_num = 3 if explicit == "Advanced" else 2 if explicit == "Intermediate" else 1
            step_label = f"Step {step_num}: {final_level}"
            level_reason = f"Explicitly stated '{explicit}' in resume."
        elif scale_detected and ev_score >= 80:
            final_level = "Advanced"
            step_num = 4
            step_label = "Step 4: Expert"
            level_reason = f"Fleet scale operations · 50+ accounts / 200+ servers ({ev_score:.0f}/100)"
        elif has_real_sections and (ev_score >= 50 or (cert_count > 0 and (project_count > 0 or experience_count > 0)) or scale_detected):
            final_level = "Advanced"
            step_num = 3
            step_label = "Step 3: Advanced"
            reason_parts = []
            if scale_detected:
                reason_parts.append("Enterprise scale deployment")
            if cert_count > 0:
                reason_parts.append("Accredited certification")
            if project_count > 0:
                reason_parts.append(f"{project_count} project reference(s)")
            if experience_count > 0:
                reason_parts.append(f"{experience_count} work role(s)")
            level_reason = " · ".join(reason_parts) or f"High evidence score ({ev_score:.0f}/100)"
        elif has_real_sections and (ev_score >= 15 or project_count > 0 or experience_count > 0 or cert_count > 0):
            final_level = "Intermediate"
            step_num = 2
            step_label = "Step 2: Intermediate"
            level_reason = f"Demonstrated in practical {'projects' if project_count else 'work experience'} ({ev_score:.0f}/100)"
        elif has_real_sections and (ev_score > 0 or len(excerpts) > 0):
            final_level = "Beginner"
            step_num = 1
            step_label = "Step 1: Beginner"
            level_reason = "Foundational: Cataloged in technical competency stack"
        else:
            final_level = "Unspecified"
            step_num = 0
            step_label = "Step 0: Unspecified"
            level_reason = "Unspecified: Minimal context detected"

        claims.append({
            "skill": skill,
            "slug": SKILL_CONFIG[skill]["slug"],
            "category": SKILL_CONFIG[skill].get("category", "General"),
            "claimed_level": final_level,
            "step_number": step_num,
            "step_label": step_label,
            "level_reason": level_reason,
            "claim_excerpt": claim_excerpt,
            "claim_not_asserted": claim_not_asserted,
            "assessment_supported": SKILL_CONFIG[skill]["slug"] in ASSESSABLE_SKILLS,
            "evidence_score": ev_score,
            "evidence_breakdown": {
                "projects": project_count,
                "experience": experience_count,
                "certifications": cert_count,
                "tools": tool_count,
                "scale_detected": scale_detected,
            },
            "evidence_snippets": excerpts[:10],
            "evidence_details": details,
        })

    # Sort claims by evidence score descending, preserving high priority skills
    claims.sort(key=lambda item: (item["evidence_score"], item["step_number"]), reverse=True)

    return {
        "name": name,
        "education": education,
        "skills": claims,
        "projects": extracted_projects,
        "certifications": extracted_certs,
    }

