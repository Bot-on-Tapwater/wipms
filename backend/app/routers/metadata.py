"""Choice lists the frontend uses for dropdowns."""
from typing import Dict, List

from fastapi import APIRouter

from app.constants.choices import Gender, LabourerTitle, TaskCategory, label_for
from app.constants.roles import Role

router = APIRouter(prefix="/metadata", tags=["Metadata"])


def _choices(enum_class: type) -> List[Dict[str, str]]:
    """
    Convert an Enum into ``[{"value": ..., "label": ...}]``.

    Args:
        enum_class (type): Enum whose values are listed.

    Returns:
        List[Dict[str, str]]: List of ``{"value", "label"}`` dictionaries.
    """
    items = []
    for item in enum_class:
        items.append({"value": item.value, "label": label_for(item.value)})
    return items


@router.get("/choices")
def get_choices() -> Dict[str, List[Dict[str, str]]]:
    """
    Return labourer titles, genders, task categories and roles (public endpoint).

    Returns:
        Dict[str, List[Dict[str, str]]]: Each choice list as value and label pairs.
    """
    roles = []
    for role in Role:
        if role != Role.SUPER_ADMIN:
            roles.append({"value": role.value, "label": label_for(role.value.replace("-", " "))})
    return {
        "labourer_titles": _choices(LabourerTitle),
        "genders": _choices(Gender),
        "task_categories": _choices(TaskCategory),
        "roles": roles,
    }
