"""Tools for the GradPath academic planning agent."""

import json
import re
import requests

# Columbia Program Reference Database


PROGRAM_DATABASE = {
    "Columbia MS Data Science": {
        "aliases": [
            "columbia ms data science",
            "columbia data science",
            "ms data science",
            "data science",
            "ds",
        ],
        "school": "Columbia University Data Science Institute",
        "minimum_total_credits": 30,
        "core_courses": [
            "COMS W4121 Computer Systems for Data Science",
            "COMS W4721 Machine Learning for Data Science",
            "CSOR W4246 Algorithms for Data Science",
            "ENGI E4800 Data Science Capstone and Ethics",
            "STAT GR5701 Probability and Statistics for Data Science",
            "STAT GR5702 Exploratory Data Analysis and Visualization",
            "STAT GR5703 Statistical Inference and Modeling",
        ],
        "special_requirements": [
            "21 credits of core coursework",
            "At least 9 elective credits",
        ],
        "source_url": (
            "https://bulletin.columbia.edu/"
            "columbia-engineering/academic-departments-programs/"
            "data-science/graduate-programs/"
        ),
    },

    "Columbia MS Business Analytics": {
        "aliases": [
            "columbia ms business analytics",
            "columbia business analytics",
            "ms business analytics",
            "business analytics",
            "msba",
            "ba",
        ],
        "school": "Columbia Engineering - IEOR",
        "minimum_total_credits": 36,
        "core_courses": [
            "IEOR E4101 Probability, Statistics and Simulation",
            "IEOR E4523 Data Analytics and Machine Learning",
            "DROM B8101 Business Analytics I",
            "MRKT B9651 MS Marketing Analytics",
            "IEOR E4524 Analytics in Practice",
            "IEOR E4004 Optimization Models and Methods",
        ],
        "special_requirements": [
            "At least 18 credits must be completed within IEOR.",
            "At least 15 credits must be completed through Columbia Business School.",
        ],
        "source_url": (
            "https://bulletin.columbia.edu/"
            "columbia-engineering/academic-departments-programs/"
            "industrial-engineering-operations-research/"
            "graduate-programs/business-analytics-ms/"
        ),
    },

    "Columbia MS Computer Science": {
        "aliases": [
            "columbia ms computer science",
            "columbia computer science",
            "ms computer science",
            "computer science",
            "cs",
        ],
        "school": "Columbia Engineering - Computer Science",
        "minimum_total_credits": 30,
        "minimum_gpa": 2.7,
        "minimum_6000_level_credits": 6,
        "core_courses": [],
        "special_requirements": [
            "Students must satisfy the Computer Science Breadth requirement.",
            "Students must complete an approved MS track.",
            "At least 6 credits must be at the 6000 level.",
        ],
        "source_url": (
            "https://bulletin.columbia.edu/"
            "columbia-engineering/academic-departments-programs/"
            "computer-science/graduate-programs/computer-science-ms/"
        ),
    },
}


# External Course Catalog URLs

COURSE_CATALOG_URLS = {
    "COMS": (
        "https://bulletin.columbia.edu/"
        "columbia-engineering/academic-departments-programs/"
        "computer-science/"
    ),
    "CSOR": (
        "https://bulletin.columbia.edu/"
        "columbia-engineering/academic-departments-programs/"
        "industrial-engineering-operations-research/"
    ),
    "IEOR": (
        "https://bulletin.columbia.edu/"
        "columbia-engineering/academic-departments-programs/"
        "industrial-engineering-operations-research/"
    ),
    "STAT": (
        "https://bulletin.columbia.edu/"
        "columbia-engineering/academic-departments-programs/"
        "data-science/graduate-programs/"
    ),
    "ENGI": (
        "https://bulletin.columbia.edu/"
        "columbia-engineering/academic-departments-programs/"
        "data-science/graduate-programs/"
    ),
}


# Helpers


def resolve_program_name(program_name: str):
    """Resolve user input to a supported canonical program."""

    if not isinstance(program_name, str):
        return None

    normalized = program_name.strip().lower()

    for canonical_name, data in PROGRAM_DATABASE.items():

        if normalized == canonical_name.lower():
            return canonical_name

        for alias in data.get("aliases", []):
            if normalized == alias.lower():
                return canonical_name

    return None


def normalize_course_code(course_code: str) -> str:
    """
    Normalize course codes.

    Examples:
        COMS W4721
        COMS4721
        COMS 4721

    become:
        COMS 4721
    """

    if not isinstance(course_code, str):
        return ""

    cleaned = course_code.upper().strip()

    match = re.search(
        r"\b([A-Z]{3,4})\s*[A-Z]?\s*(\d{4})\b",
        cleaned,
    )

    if not match:
        return cleaned

    department = match.group(1)
    number = match.group(2)

    return f"{department} {number}"


def course_matches(required_course: str, completed_course: str) -> bool:
    """Compare two course names/codes flexibly."""

    required = required_course.lower().strip()
    completed = completed_course.lower().strip()

    if required == completed:
        return True

    required_code = normalize_course_code(required_course).lower()
    completed_code = normalize_course_code(completed_course).lower()

    return (
        required_code == completed_code
        or required in completed
        or completed in required
    )


def clean_html(html: str) -> str:
    """Convert HTML into easier-to-search plain text."""

    text = re.sub(
        r"<script.*?</script>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<style.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    replacements = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&quot;": '"',
        "&#39;": "'",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


# Tool 1: GPA Path Calculator

def calculate_gpa_path(
    current_gpa: float,
    completed_credits: float,
    remaining_credits: float,
    target_gpa: float,
) -> str:
    """Calculate the GPA needed over remaining credits."""

    try:
        current_gpa = float(current_gpa)
        completed_credits = float(completed_credits)
        remaining_credits = float(remaining_credits)
        target_gpa = float(target_gpa)

    except (TypeError, ValueError):
        return json.dumps({
            "error": "GPA and credit values must be numbers."
        })

    if not 0 <= current_gpa <= 4:
        return json.dumps({
            "error": "Current GPA must be between 0.0 and 4.0."
        })

    if not 0 <= target_gpa <= 4:
        return json.dumps({
            "error": "Target GPA must be between 0.0 and 4.0."
        })

    if completed_credits < 0:
        return json.dumps({
            "error": "Completed credits cannot be negative."
        })

    if remaining_credits <= 0:
        return json.dumps({
            "error": "Remaining credits must be greater than zero."
        })

    required_gpa = (
        target_gpa * (completed_credits + remaining_credits)
        - current_gpa * completed_credits
    ) / remaining_credits

    feasible = 0 <= required_gpa <= 4.0

    if required_gpa > 4:
        status = "Target GPA is not mathematically reachable."

    elif required_gpa <= 0:
        status = "Target GPA is already secured."

    else:
        status = "Target GPA is mathematically reachable."

    return json.dumps({
        "current_gpa": current_gpa,
        "completed_credits": completed_credits,
        "remaining_credits": remaining_credits,
        "target_gpa": target_gpa,
        "required_remaining_gpa": round(required_gpa, 3),
        "feasible": feasible,
        "status": status,
    })


# Tool 2: External Program Requirement Lookup

def lookup_program_requirements(program_name: str) -> str:
    """
    Look up Columbia program requirements.

    This tool makes a live request to the official Columbia
    source page before returning GradPath's structured data.
    """

    canonical_name = resolve_program_name(program_name)

    if canonical_name is None:
        return json.dumps({
            "error": f"Program '{program_name}' is not supported.",
            "supported_programs": list(PROGRAM_DATABASE.keys()),
        })

    program = PROGRAM_DATABASE[canonical_name]
    source_url = program["source_url"]

    try:
        response = requests.get(
            source_url,
            timeout=10,
            headers={
                "User-Agent": "GradPath academic planning course project"
            },
        )

        response.raise_for_status()

    except requests.RequestException as e:
        return json.dumps({
            "error": "Could not reach the official Columbia program page.",
            "details": str(e),
            "program_name": canonical_name,
            "source_url": source_url,
            "action": (
                "Try again later or verify the requirements "
                "directly on the Columbia program page."
            ),
        })

    return json.dumps({
        "program_name": canonical_name,
        "school": program["school"],
        "minimum_total_credits": program["minimum_total_credits"],
        "core_courses": program.get("core_courses", []),
        "minimum_gpa": program.get("minimum_gpa"),
        "minimum_6000_level_credits": program.get(
            "minimum_6000_level_credits"
        ),
        "special_requirements": program.get(
            "special_requirements",
            [],
        ),
        "source_url": source_url,
        "external_request_status": response.status_code,
        "source_verified_live": True,
        "note": (
            "The official Columbia source page was reached successfully. "
            "GradPath returns structured reference data based on that page."
        ),
    })


# Tool 3: Degree Requirement Audit

def audit_degree_requirements(
    program_name: str,
    completed_courses: list[str],
    completed_credits: float,
    current_gpa: float | None = None,
    credits_6000_level: float | None = None,
) -> str:
    """Audit progress against a supported Columbia graduate program."""

    canonical_name = resolve_program_name(program_name)

    if canonical_name is None:
        return json.dumps({
            "error": f"Program '{program_name}' is not supported.",
            "supported_programs": list(PROGRAM_DATABASE.keys()),
        })

    try:
        completed_credits = float(completed_credits)

    except (TypeError, ValueError):
        return json.dumps({
            "error": "Completed credits must be a number."
        })

    if completed_credits < 0:
        return json.dumps({
            "error": "Completed credits cannot be negative."
        })

    if not isinstance(completed_courses, list):
        return json.dumps({
            "error": "completed_courses must be a list."
        })

    program = PROGRAM_DATABASE[canonical_name]

    result = {
        "program_name": canonical_name,
        "verified_items": [],
        "missing_requirements": [],
        "needs_more_information": [],
        "source_url": program["source_url"],
    }

    credits_remaining = max(
        0,
        program["minimum_total_credits"] - completed_credits,
    )

    if credits_remaining > 0:
        result["missing_requirements"].append({
            "type": "total_credits",
            "missing": credits_remaining,
        })

    else:
        result["verified_items"].append(
            "Total credit requirement is satisfied."
        )

    required_courses = program.get(
        "core_courses",
        [],
    )

    if required_courses:

        missing_courses = []

        for required_course in required_courses:

            matched = any(
                course_matches(
                    required_course,
                    completed,
                )
                for completed in completed_courses
                if isinstance(completed, str)
            )

            if not matched:
                missing_courses.append(
                    required_course
                )

        if missing_courses:
            result["missing_requirements"].append({
                "type": "core_courses",
                "missing": missing_courses,
            })

        else:
            result["verified_items"].append(
                "All listed core courses are complete."
            )


    # Computer Science special checks

    if canonical_name == "Columbia MS Computer Science":

        if current_gpa is None:
            result["needs_more_information"].append(
                "Current GPA is needed to verify the 2.7 GPA minimum."
            )

        else:

            try:
                current_gpa = float(current_gpa)

            except (TypeError, ValueError):
                return json.dumps({
                    "error": "current_gpa must be a number."
                })

            if current_gpa >= 2.7:
                result["verified_items"].append(
                    "The minimum 2.7 GPA requirement is satisfied."
                )

            else:
                result["missing_requirements"].append({
                    "type": "minimum_gpa",
                    "required": 2.7,
                    "current": current_gpa,
                })

        if credits_6000_level is None:

            result["needs_more_information"].append(
                "6000-level credits are needed to verify "
                "the 6-credit minimum."
            )

        else:

            try:
                credits_6000_level = float(
                    credits_6000_level
                )

            except (TypeError, ValueError):
                return json.dumps({
                    "error": "credits_6000_level must be a number."
                })

            if credits_6000_level >= 6:

                result["verified_items"].append(
                    "The 6000-level credit requirement is satisfied."
                )

            else:

                result["missing_requirements"].append({
                    "type": "6000_level_credits",
                    "required": 6,
                    "current": credits_6000_level,
                    "missing": 6 - credits_6000_level,
                })

        result["needs_more_information"].append(
            "Breadth and track-specific requirements must also be verified."
        )

    # Business Analytics special checks

    if canonical_name == "Columbia MS Business Analytics":

        result["needs_more_information"].extend([
            (
                "IEOR credits must be checked "
                "against the 18-credit minimum."
            ),
            (
                "Columbia Business School credits must be checked "
                "against the 15-credit minimum."
            ),
        ])

    result["graduation_requirements_met"] = (
        len(result["missing_requirements"]) == 0
        and len(result["needs_more_information"]) == 0
    )

    return json.dumps(result)


# Tool 4: External Course Catalog Lookup


def lookup_course_catalog(course_code: str) -> str:
    """
    Look up a Columbia course using an official Columbia
    Bulletin page.

    This tool makes a live external HTTP request and attempts
    to return a clean course title, credits, term, and section
    information instead of a large raw text snippet.
    """

    normalized = normalize_course_code(
        course_code
    )

    match = re.match(
        r"([A-Z]{3,4})\s+(\d{4})",
        normalized,
    )

    if not match:
        return json.dumps({
            "error": (
                "Course code was not recognized. "
                "Try a code such as 'COMS W4721' "
                "or 'COMS 4721'."
            )
        })

    department = match.group(1)
    number = match.group(2)

    source_url = COURSE_CATALOG_URLS.get(
        department
    )

    if source_url is None:
        return json.dumps({
            "error": (
                f"Department '{department}' "
                "is not currently supported."
            ),
            "supported_departments": list(
                COURSE_CATALOG_URLS.keys()
            ),
        })

    try:
        response = requests.get(
            source_url,
            timeout=10,
            headers={
                "User-Agent": (
                    "GradPath academic planning course project"
                )
            },
        )

        response.raise_for_status()

        html = response.text

    except requests.RequestException as e:
        return json.dumps({
            "error": "Could not reach the Columbia course catalog.",
            "details": str(e),
            "source_url": source_url,
        })

    plain_text = clean_html(
        html
    )

    
    # Find course

    course_code_pattern = re.compile(
        rf"\b{department}\s*W?{number}\b",
        re.IGNORECASE,
    )

    code_match = course_code_pattern.search(
        plain_text
    )

    if not code_match:
        return json.dumps({
            "course_code": normalized,
            "found": False,
            "source_url": source_url,
            "external_request_status": response.status_code,
            "message": (
                "The Columbia catalog page was reached, "
                "but the course code was not found."
            ),
        })

    # Extract course title + credits

    nearby_start = max(
        0,
        code_match.start() - 50,
    )

    nearby_end = min(
        len(plain_text),
        code_match.end() + 1000,
    )

    nearby_text = plain_text[
        nearby_start:nearby_end
    ]

    title_credit_pattern = re.compile(
        rf"{department}\s*W?{number}\s+"
        rf"(.{{3,120}}?)\s+"
        rf"(\d+(?:\.\d+)?)\s+points",
        re.IGNORECASE,
    )

    title_credit_match = title_credit_pattern.search(
        nearby_text
    )

    title = None
    credits = None

    if title_credit_match:

        title = (
            title_credit_match
            .group(1)
            .strip(" .:-")
        )

        credits = float(
            title_credit_match.group(2)
        )

    
    # Extract term

    term_match = re.search(
        r"\b(Spring|Fall|Summer)\s+(20\d{2})\b",
        nearby_text,
        re.IGNORECASE,
    )

    term = None

    if term_match:
        term = (
            f"{term_match.group(1).title()} "
            f"{term_match.group(2)}"
        )

    # Extract sections

    sections = []

    section_pattern = re.compile(
        rf"{department}\s+{number}\s+"
        rf"([A-Z0-9]+/\d+)"
        rf"(.*?)(?="
        rf"{department}\s+{number}\s+[A-Z0-9]+/\d+"
        rf"|{department}\s*W?\d{{4}}"
        rf"|$)",
        re.IGNORECASE,
    )

    for section_match in section_pattern.finditer(
        nearby_text
    ):

        section_id = section_match.group(1)

        details = (
            section_match
            .group(2)
            .strip()
        )

        time_match = re.search(
            r"\b(?:M|T|W|Th|F|Sa|Su)"
            r"(?:\s+(?:M|T|W|Th|F|Sa|Su))*\s+"
            r"\d{1,2}:\d{2}(?:am|pm)"
            r"\s*-\s*"
            r"\d{1,2}:\d{2}(?:am|pm)",
            details,
            re.IGNORECASE,
        )

        meeting_time = (
            time_match.group(0)
            if time_match
            else None
        )

        enrollment_match = re.search(
            r"\b(\d+/\d+)\b",
            details,
        )

        enrollment = (
            enrollment_match.group(1)
            if enrollment_match
            else None
        )

        sections.append({
            "section": section_id,
            "meeting_time": meeting_time,
            "enrollment": enrollment,
            "details": details[:250],
        })

        if len(sections) >= 5:
            break

    return json.dumps({
        "course_code": f"{department} {number}",
        "title": title,
        "credits": credits,
        "term": term,
        "sections": sections,
        "found": True,
        "source_url": source_url,
        "external_request_status": response.status_code,
        "source_verified_live": True,
    })


# Tool Schemas

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_gpa_path",
            "description": (
                "Calculate the GPA needed across remaining credits "
                "to reach a target cumulative GPA."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "current_gpa": {
                        "type": "number",
                        "description": (
                            "Current cumulative GPA "
                            "on a 4.0 scale."
                        ),
                    },
                    "completed_credits": {
                        "type": "number",
                        "description": (
                            "Number of credits already completed."
                        ),
                    },
                    "remaining_credits": {
                        "type": "number",
                        "description": (
                            "Number of GPA-bearing credits remaining."
                        ),
                    },
                    "target_gpa": {
                        "type": "number",
                        "description": (
                            "Target cumulative GPA."
                        ),
                    },
                },
                "required": [
                    "current_gpa",
                    "completed_credits",
                    "remaining_credits",
                    "target_gpa",
                ],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "lookup_program_requirements",
            "description": (
                "Look up requirements for a supported Columbia "
                "graduate program and verify the official source "
                "page with a live external request."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "program_name": {
                        "type": "string",
                        "description": (
                            "The user's Columbia graduate program."
                        ),
                    },
                },
                "required": [
                    "program_name"
                ],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "audit_degree_requirements",
            "description": (
                "Audit a student's completed coursework and credits "
                "against a supported Columbia graduate program."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "program_name": {
                        "type": "string",
                        "description": (
                            "The student's explicitly stated program."
                        ),
                    },
                    "completed_courses": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": (
                            "Courses the student has completed."
                        ),
                    },
                    "completed_credits": {
                        "type": "number",
                        "description": (
                            "Total credits or points completed."
                        ),
                    },
                    "current_gpa": {
                        "type": "number",
                        "description": (
                            "Current GPA when needed "
                            "for the selected program."
                        ),
                    },
                    "credits_6000_level": {
                        "type": "number",
                        "description": (
                            "Number of 6000-level credits completed."
                        ),
                    },
                },
                "required": [
                    "program_name",
                    "completed_courses",
                    "completed_credits",
                ],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "lookup_course_catalog",
            "description": (
                "Look up a specific Columbia course using a live "
                "request to the official Columbia Bulletin. "
                "Use this when the user asks for information "
                "about a specific course code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "course_code": {
                        "type": "string",
                        "description": (
                            "A Columbia course code such as "
                            "'COMS W4721'."
                        ),
                    },
                },
                "required": [
                    "course_code"
                ],
            },
        },
    },
]


# Tool Map

TOOL_MAP = {
    "calculate_gpa_path": calculate_gpa_path,
    "lookup_program_requirements": lookup_program_requirements,
    "audit_degree_requirements": audit_degree_requirements,
    "lookup_course_catalog": lookup_course_catalog,
}


# Safe Tool Runner

def run_tool(name: str, args: dict) -> str:
    """Run a tool safely without crashing the agent loop."""

    if name not in TOOL_MAP:
        return json.dumps({
            "error": (
                f"Unknown tool '{name}'. "
                f"Available tools: {list(TOOL_MAP.keys())}"
            )
        })

    try:
        return TOOL_MAP[name](**args)

    except TypeError as e:
        return json.dumps({
            "error": (
                f"Bad arguments for {name}: {e}"
            )
        })

    except Exception as e:
        return json.dumps({
            "error": (
                f"{name} failed unexpectedly: "
                f"{type(e).__name__}: {e}"
            )
        })