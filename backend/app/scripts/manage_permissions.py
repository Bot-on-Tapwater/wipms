"""Command line tool to view and change role permissions.

Examples::

    python -m app.scripts.manage_permissions list
    python -m app.scripts.manage_permissions list --role subcontractor
    python -m app.scripts.manage_permissions grant subcontractor reports.view
    python -m app.scripts.manage_permissions revoke subcontractor reports.view
    python -m app.scripts.manage_permissions reset

The same changes can be made through the API
(``/api/v1/permissions/roles/{role}/grant`` and ``/revoke``).
"""
import argparse
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.services import permission_service


def list_command(db: Session, role: Optional[str]) -> None:
    """
    Print all permission codes, or the codes granted to one role.

    Args:
        db (Session): Database session.
        role (Optional[str]): Role value, e.g. ``subcontractor``.
    """
    if role:
        permission_service.validate_role(role)
        for code in permission_service.get_permissions_for_role(db, role):
            print(code)
        return
    for permission in permission_service.list_permissions(db):
        print(f"{permission.code:50} {permission.description}")


def build_parser() -> argparse.ArgumentParser:
    """
    Define the command line arguments.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(description="Manage role permissions")
    commands = parser.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser("list", help="List permissions")
    list_parser.add_argument("--role", help="Only show permissions of this role")

    grant_parser = commands.add_parser("grant", help="Give a permission to a role")
    grant_parser.add_argument("role")
    grant_parser.add_argument("code")

    revoke_parser = commands.add_parser("revoke", help="Remove a permission from a role")
    revoke_parser.add_argument("role")
    revoke_parser.add_argument("code")

    commands.add_parser("reset", help="Restore the default permissions of every role")
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """
    Run the requested command.

    Args:
        argv (Optional[List[str]]): Arguments to parse; defaults to ``sys.argv``.
    """
    args = build_parser().parse_args(argv)
    try:
        run_command(args)
    except AppError as error:
        raise SystemExit(f"Error: {error.message}")


def run_command(args: argparse.Namespace) -> None:
    """
    Execute one parsed command against the database.

    Args:
        args (argparse.Namespace): Parsed command line arguments.
    """
    with SessionLocal() as db:
        if args.command == "list":
            list_command(db, args.role)
        elif args.command == "grant":
            permission_service.grant_permission(db, args.role, args.code)
            print(f"Granted {args.code} to {args.role}")
        elif args.command == "revoke":
            permission_service.revoke_permission(db, args.role, args.code)
            print(f"Revoked {args.code} from {args.role}")
        elif args.command == "reset":
            permission_service.seed_permissions(db, reset_roles=True)
            print("All roles reset to their default permissions")


if __name__ == "__main__":
    main()
