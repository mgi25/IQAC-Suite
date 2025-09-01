"""Navigation tree and helpers for sidebar permissions."""

NAV_ITEMS = [
    {
        "id": "dashboard",
        "label": "Dashboard",
        "children": [
            {"id": "dashboard:admin", "label": "Admin Dashboard"},
            {"id": "dashboard:faculty", "label": "Faculty Dashboard"},
            {"id": "dashboard:student", "label": "Student Dashboard"},
            {"id": "dashboard:cdl_head", "label": "CDL Head Dashboard"},
            {"id": "dashboard:cdl_work", "label": "CDL Work Dashboard"},
        ],
    },
    {
        "id": "events",
        "label": "Event Management Suite",
        "children": [
            {"id": "events:submit_proposal", "label": "Event Proposal"},
            {"id": "events:pending_reports", "label": "Report Generation"},
            {"id": "events:generated_reports", "label": "View Reports"},
            {"id": "events:my_approvals", "label": "Event Approvals"},
        ],
    },
    {"id": "transcript", "label": "Graduate Transcript"},
    {"id": "cdl", "label": "CDL"},
    {
        "id": "settings",
        "label": "Settings",
        "children": [
            {"id": "settings:user_settings", "label": "User Settings"},
            {"id": "settings:approval_flow", "label": "Approval Flow Management"},
            {"id": "settings:pso_psos", "label": "POs & PSOs Management"},
            {"id": "settings:academic_year", "label": "Academic Year Settings"},
            {"id": "settings:history", "label": "History"},
            {"id": "settings:sidebar_permissions", "label": "Sidebar Permissions"},
        ],
    },
    {"id": "user_management", "label": "User Management"},
    {"id": "event_proposals", "label": "Event Proposals"},
    {"id": "reports", "label": "Reports"},
]


def _flatten(items):
    ids = []
    for item in items:
        ids.append(item["id"])
        children = item.get("children") or []
        ids.extend(_flatten(children))
    return ids

SIDEBAR_ITEM_IDS = set(_flatten(NAV_ITEMS))
