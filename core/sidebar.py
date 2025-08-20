"""Central registry for Sidebar modules and submodules.

This registry is used by:
- Admin permissions UI to display assignable modules/submodules
- Context processor to render the sidebar dynamically

Conventions:
- Keys are slugs. These slugs are persisted in SidebarPermission.items
- items JSON is a dict: { module_slug: [sub_slug, ...] }
  - If a module key exists with an empty list [], it means FULL access to all submodules.
  - If a module key is missing, the module is not visible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class SubModule:
    slug: str
    label: str
    url: Optional[str]  # Django URL or absolute path


@dataclass(frozen=True)
class Module:
    slug: str
    label: str
    icon: str  # font-awesome icon class
    url: Optional[str]
    submodules: List[SubModule]


MODULES: Dict[str, Module] = {
    # Dashboard (single link in sidebar; submodules are for dashboard page widgets/tabs if needed)
    "dashboard": Module(
        slug="dashboard",
        label="Dashboard",
        icon="fas fa-chart-pie",
        url="/dashboard/",  # use route path for simpler rendering
        submodules=[
            SubModule("overview", "Overview", None),
            SubModule("event_calendar", "Event Calendar", None),
            SubModule("analytics", "Analytics", None),
        ],
    ),

    # Event Management Suite
    "events": Module(
        slug="events",
        label="Event Management Suite",
        icon="fas fa-clipboard-list",
        url=None,
        submodules=[
            SubModule("propose_event", "Event Proposal", "/suite/submit/"),
            SubModule("report_generation", "Report Generation", "/suite/pending-reports/"),
            SubModule("generated_reports", "View Reports", "/suite/generated-reports/"),
            SubModule("event_approvals", "Event Approvals", "/suite/my-approvals/"),
        ],
    ),

    # Reports (core admin reports area)
    "reports": Module(
        slug="reports",
        label="Reports",
        icon="fas fa-file-alt",
        url="/core-admin/reports/",
        submodules=[
            SubModule("generated_reports", "Generated Reports", "/suite/generated-reports/"),
            SubModule("custom_reports", "Custom Reports", None),
            SubModule("archived_reports", "Archived Reports", None),
        ],
    ),

    # Settings (admin area)
    "settings": Module(
        slug="settings",
        label="Settings",
        icon="fas fa-cog",
        url="/core-admin/settings/",
        submodules=[
            SubModule("profile_settings", "User Settings", "/core-admin/master-data/"),
            SubModule("approval_flow", "Approval Flow Management", "/core-admin/approval-flow/"),
            SubModule("pso_pso_management", "POs & PSOs Management", "/core-admin/pso-po/"),
            SubModule("academic_year", "Academic Year Settings", "/core-admin/academic-year/"),
            SubModule("history", "History", "/core-admin/history/"),
            SubModule("sidebar_permissions", "Sidebar Permissions", "/core-admin/sidebar-permissions/"),
            SubModule("integrations", "Integrations", None),
            SubModule("security", "Security", None),
        ],
    ),

    # User Management (admin)
    "user_management": Module(
        slug="user_management",
        label="User Management",
        icon="fas fa-users",
        url=None,
        submodules=[
            SubModule("manage_users", "Manage Users", "/core-admin/users/"),
            SubModule("add_roles", "Add Roles", "/core-admin/user-roles/"),
        ],
    ),

    # Graduate Transcript (superuser-only previously; now permission-driven)
    "transcript": Module(
        slug="transcript",
        label="Graduate Transcript",
        icon="fas fa-graduation-cap",
        url="/transcript/",
        submodules=[],
    ),

    # CDL
    "cdl": Module(
        slug="cdl",
        label="CDL",
        icon="fas fa-photo-video",
        url=None,
        submodules=[
            SubModule("pre_event", "Pre-Event", "/cdl/"),
            SubModule("post_event", "Post-Event", "/cdl/"),
        ],
    ),

    # Event Proposals (admin)
    "event_proposals": Module(
        slug="event_proposals",
        label="Event Proposals",
        icon="fas fa-list",
        url="/core-admin/event-proposals/",
        submodules=[],
    ),
}


def normalize_items(items: Optional[dict | list]) -> Dict[str, List[str]]:
    """Normalize stored items from legacy list to hierarchical dict.

    - If items is a list (legacy), convert to {key: []} meaning full module.
    - If items is a dict, ensure values are lists; coerce None to [].
    - Unknown keys are left as-is (safe forward-compat).
    """
    if not items:
        return {}
    if isinstance(items, list):
        return {str(k): [] for k in items}
    if isinstance(items, dict):
        return {str(k): ([] if v in (None, True) else list(v)) for k, v in items.items()}
    return {}
