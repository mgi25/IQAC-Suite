import json
from pathlib import Path
from typing import Dict, Any, List

# Extract from POST for simplicity; frontend will send these (with fallbacks)
BASIC_FIELDS = [
    "organization_type", "department", "committees_collaborations",
    "event_title", "target_audience", "event_focus_type", "location",
    "start_date", "end_date", "academic_year",
    "pos_pso_management", "sdg_goals",
    "num_activities", "student_coordinators", "faculty_incharges",
    "additional_context",
]

CONFIG_DIR = Path(__file__).resolve().parent / "field_config"


def load_fields(task: str) -> List[str]:
    """Load the minimal field list for a given AI task."""
    path = CONFIG_DIR / f"{task}.json"
    try:
        with path.open() as fh:
            data = json.load(fh)
        return data.get("fields", [])
    except FileNotFoundError:
        return []


def collect_basic_facts(request, field_names: List[str] | None = None) -> Dict[str, Any]:
    get = request.POST.get
    facts = {
        "organization_type": get("organization_type", "") or "[TBD]",
        "department": get("department", "") or "[TBD]",
        "committees_collaborations": request.POST.getlist("committees_collaborations[]") or
                                     request.POST.getlist("committees_collaborations") or [],
        "event_title": get("event_title", get("title", "")) or "[TBD]",
        "target_audience": get("target_audience", "") or "[TBD]",
        "event_focus_type": get("event_focus_type", get("focus", "")) or "[TBD]",
        "location": get("location", "") or "[TBD]",
        "start_date": get("start_date", "") or "[TBD]",
        "end_date": get("end_date", "") or "[TBD]",
        "academic_year": get("academic_year", "") or "[TBD]",
        "pos_pso_management": get("pos_pso_management", get("pos_pso", "")) or "[TBD]",
        "sdg_goals": request.POST.getlist("sdg_goals[]") or request.POST.getlist("sdg_goals") or [],
        "num_activities": get("num_activities", "") or "[TBD]",
        "student_coordinators": request.POST.getlist("student_coordinators[]") or [],
        "faculty_incharges": request.POST.getlist("faculty_incharges[]") or [],
        "additional_context": get("additional_context", ""),
    }
    if field_names is not None:
        facts = {k: facts[k] for k in field_names if k in facts}
    return facts
