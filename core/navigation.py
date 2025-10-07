"""Navigation tree helpers (DB + fallback).

Primary source becomes `SidebarModule` rows; if none exist yet we fall back
to the original static structure (also used to seed first run).
"""

from functools import lru_cache

STATIC_NAV_ITEMS = [
    {"id": "dashboard", "label": "Dashboard", "children": [
        {"id": "dashboard:admin", "label": "Admin Dashboard"},
        {"id": "dashboard:faculty", "label": "Faculty Dashboard"},
        {"id": "dashboard:student", "label": "Student Dashboard"},
        {"id": "dashboard:cdl_head", "label": "CDL Head Dashboard"},
        {"id": "dashboard:cdl_work", "label": "CDL Work Dashboard"},
    ]},
    {"id": "events", "label": "Event Management Suite", "children": [
        {"id": "events:submit_proposal", "label": "Event Proposal"},
        {"id": "events:pending_reports", "label": "Report Generation"},
        {"id": "events:generated_reports", "label": "View Reports"},
        {"id": "events:review", "label": "Review"},
        {"id": "events:my_approvals", "label": "Event Approvals"},
    ]},
    {"id": "transcript", "label": "Graduate Transcript"},
    {"id": "cdl", "label": "CDL Support"},
    {"id": "analysis", "label": "Analysis"},
    {"id": "settings", "label": "Settings", "children": [
        {"id": "settings:user_settings", "label": "User Settings"},
        {"id": "settings:approval_flow", "label": "Approval Flow Management"},
        {"id": "settings:pso_psos", "label": "POs & PSOs Management"},
        {"id": "settings:academic_year", "label": "Academic Year Settings"},
        {"id": "settings:history", "label": "History"},
        {"id": "settings:sidebar_permissions", "label": "Sidebar Permissions"},
    ]},
    {"id": "user_management", "label": "User Management"},
    {"id": "event_proposals", "label": "Event Proposals"},
    {"id": "reports", "label": "Reports"},
]


def _flatten(items):
    out = []
    for it in items:
        out.append(it['id'])
        for ch in it.get('children') or []:
            out.extend(_flatten([ch]))
    return out


@lru_cache(maxsize=1)
def get_nav_items():
    """Return navigation tree (DB or fallback).

    Cache for request scope; cache invalidation can be manual via
    `get_nav_items.cache_clear()` after admin edits (future admin UI).
    """
    try:
        from core.models import SidebarModule  # local import to avoid cycle
        if SidebarModule.objects.exists():
            return SidebarModule.as_nav_tree()
    except Exception:  # pragma: no cover
        pass
    return STATIC_NAV_ITEMS


def get_sidebar_item_ids():
    return set(_flatten(get_nav_items()))


# Backwards compatibility names used in existing code
NAV_ITEMS = get_nav_items()
SIDEBAR_ITEM_IDS = get_sidebar_item_ids()

