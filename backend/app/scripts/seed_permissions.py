"""Add any missing permissions and their default role assignments.

Safe to run many times: existing role changes are kept. Runs automatically
in the Docker entrypoint after migrations::

    python -m app.scripts.seed_permissions
"""
from app.core.database import SessionLocal
from app.services.permission_service import seed_permissions


def main() -> None:
    """Seed permissions into the database."""
    with SessionLocal() as db:
        seed_permissions(db)
    print("Permissions seeded.")


if __name__ == "__main__":
    main()
