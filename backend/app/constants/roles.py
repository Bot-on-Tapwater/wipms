"""User roles available on the platform (same values as the old backend)."""
from enum import Enum


class Role(str, Enum):
    """All roles a user can register with."""

    SUPER_ADMIN = "super-admin"
    MAIN_CONTRACTOR = "main-contractor"
    CONTRACTORS_SUPERVISOR = "contractors-supervisor"
    CONSULTANTS_SUPERVISOR = "consultants-supervisor"
    SUBCONTRACTOR = "subcontractor"
