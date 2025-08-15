from typing import Dict, Any

# Extract from POST for simplicity; frontend will send these (with fallbacks)
BASIC_FIELDS = [
    "organization_type", "department", "committees_collaborations",
    "event_title", "target_audience", "event_focus_type", "location",
    "start_date", "end_date", "academic_year",
    "pos_pso_management", "sdg_goals",
    "num_activities", "student_coordinators", "faculty_incharges",
    "additional_context",
]

def collect_basic_facts(request) -> Dict[str, Any]:
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
    return facts
