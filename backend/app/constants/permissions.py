"""Catalogue of every permission and the default permissions of each role.

This file is the single source of truth used to *seed* the database.
After seeding, permissions live in the ``permissions`` and ``role_permissions``
tables and can be changed without touching code, using either:

* the CLI: ``python -m app.scripts.manage_permissions grant <role> <code>``
* the API: ``POST /api/v1/permissions/roles/{role}/grant`` and ``/revoke``
  (needs ``permissions.manage``, which only the super admin has by default)

The defaults below reproduce the access rules of the old Django backend.
Note: in the old backend ``IsContractorSupervisor`` also let the main
contractor through, so the main contractor has those permissions as well.
"""
from typing import Dict, List

from app.constants.roles import Role

# code -> human readable description
PERMISSIONS: Dict[str, str] = {
    # Users
    "users.view_all": "List all users (e.g. to pick people to assign to a project)",
    # Permissions
    "permissions.manage": "Grant or revoke permissions for roles",
    # Projects
    "projects.view_all": "See every project on the platform",
    "projects.create": "Create a project",
    "projects.edit": "Edit project details",
    "projects.delete": "Delete a project",
    "projects.assign_supervisors": "Assign/unassign contractor and consultant supervisors",
    "projects.assign_subcontractors": "Assign subcontractors to a project",
    "projects.unassign_subcontractors": "Remove subcontractors from a project",
    "projects.fund_wallet": "Add funds to a project wallet",
    "projects.view_wallet": "View the deposits and payouts of a project wallet",
    # Works
    "works.create": "Create a work under a project",
    "works.edit": "Edit a work",
    "works.delete": "Delete a work",
    "works.assign_subcontractor": "Assign/unassign the subcontractor of a work",
    "works.upload_images": "Upload proof-of-work images",
    "works.comment_as_contractor_supervisor": "Add contractor supervisor comments",
    "works.comment_as_consultant_supervisor": "Add consultant supervisor comments",
    "works.approve_as_consultant": "Approve/disapprove a work as consultant supervisor",
    "works.approve_as_contractor_supervisor": "Approve/disapprove a work as contractor supervisor",
    "works.approve_attendance": "Approve/disapprove labourer attendance",
    "works.approve_cost": "Approve/disapprove the cost of a work",
    "works.manage_labourers": "Assign/unassign labourers to a work",
    # Payments
    "payments.request": "Request payment for a work",
    "payments.approve_as_contractor_supervisor": "Give contractor supervisor payment approval",
    "payments.approve_as_main_contractor": "Give main contractor payment approval",
    "payments.request_retention": "Request release of retention money",
    "payments.approve_retention": "Approve and pay retention money",
    "payments.view": "View payment records and summaries",
    # Labourers
    "labourers.create": "Create labourers",
    "labourers.edit": "Edit labourers",
    "labourers.view": "View and search labourers",
    # Reports
    "reports.view": "Generate and print reports",
    # Insights
    "stats.view": "See labour insights (trades, sites, gender, age groups, pay per trade) "
                  "for projects the user created or is on",
    "stats.view_all": "See labour insights for every project on the platform",
}

_MC = Role.MAIN_CONTRACTOR.value
_CS = Role.CONTRACTORS_SUPERVISOR.value
_CON = Role.CONSULTANTS_SUPERVISOR.value
_SUB = Role.SUBCONTRACTOR.value

# permission code -> roles that have it by default (super-admin gets everything)
DEFAULT_ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "users.view_all": [_MC, _CS],
    "permissions.manage": [],
    "projects.view_all": [_MC],
    "projects.create": [_MC],
    "projects.edit": [_MC, _CS],
    "projects.delete": [_MC],
    "projects.assign_supervisors": [_MC],
    "projects.assign_subcontractors": [_MC, _CS],
    "projects.unassign_subcontractors": [_MC],
    "projects.fund_wallet": [_MC],
    "projects.view_wallet": [_MC, _CS, _CON],
    "works.create": [_MC, _CS, _SUB],
    "works.edit": [_MC, _CS, _SUB],
    "works.delete": [_MC],
    "works.assign_subcontractor": [_MC, _CS],
    "works.upload_images": [_MC, _CS, _CON, _SUB],
    "works.comment_as_contractor_supervisor": [_MC, _CS],
    "works.comment_as_consultant_supervisor": [_CON],
    "works.approve_as_consultant": [_CON],
    "works.approve_as_contractor_supervisor": [_MC, _CS],
    "works.approve_attendance": [_MC, _CS],
    "works.approve_cost": [_MC],
    "works.manage_labourers": [_MC, _CS, _SUB],
    "payments.request": [_MC, _CS, _SUB],
    "payments.approve_as_contractor_supervisor": [_CS],
    "payments.approve_as_main_contractor": [_MC],
    "payments.request_retention": [_MC, _CS, _SUB],
    "payments.approve_retention": [_MC],
    "payments.view": [_MC, _CS, _CON, _SUB],
    "labourers.create": [_MC, _CS, _SUB],
    "labourers.edit": [_MC, _CS, _SUB],
    "labourers.view": [_MC, _CS, _CON, _SUB],
    "reports.view": [_MC, _CS, _CON, _SUB],
    "stats.view": [_MC],
    "stats.view_all": [],
}


def default_permissions_for_role(role: str) -> List[str]:
    """
    Return the default permission codes for a role.

    Args:
        role (str): Role value, e.g. ``subcontractor``.

    Returns:
        List[str]: Default permission codes of the role.
    """
    if role == Role.SUPER_ADMIN.value:
        return list(PERMISSIONS.keys())
    codes = []
    for code, roles in DEFAULT_ROLE_PERMISSIONS.items():
        if role in roles:
            codes.append(code)
    return codes
