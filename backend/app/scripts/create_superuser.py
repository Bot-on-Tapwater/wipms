"""Create a super admin account (super admins cannot self-register).

Interactive::

    python -m app.scripts.create_superuser --email admin@example.com \
        --first-name Jane --last-name Doe --phone 254712345678

The password is asked for at the prompt. For automated setups it can be
set as ``SUPERUSER_PASSWORD`` in the .env file instead.
"""
import argparse
import getpass
from typing import List, Optional

from app.constants.roles import Role
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.schemas.common import validate_password_length, validate_phone_number
from app.services.auth_service import get_user_by_email


def read_password() -> str:
    """
    Get the password from SUPERUSER_PASSWORD or ask for it twice.

    Returns:
        str: The password entered.
    """
    if settings.SUPERUSER_PASSWORD:
        return settings.SUPERUSER_PASSWORD
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Password (again): "):
        raise SystemExit("Error: passwords do not match")
    return password


def build_parser() -> argparse.ArgumentParser:
    """
    Define the command line arguments.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(description="Create a super admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--phone", required=True, help="Format 254XXXXXXXXX")
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """
    Validate the input and create the super admin.

    Args:
        argv (Optional[List[str]]): Arguments to parse; defaults to ``sys.argv``.
    """
    args = build_parser().parse_args(argv)
    email = args.email.strip().lower()
    try:
        phone = validate_phone_number(args.phone)
        password = validate_password_length(read_password())
    except ValueError as error:
        raise SystemExit(f"Error: {error}")

    with SessionLocal() as db:
        if get_user_by_email(db, email) is not None:
            raise SystemExit(f"Error: a user with email {email} already exists")
        user = User(
            first_name=args.first_name.strip(),
            last_name=args.last_name.strip(),
            email=email,
            phone_number=phone,
            role=Role.SUPER_ADMIN.value,
            hashed_password=hash_password(password),
        )
        db.add(user)
        db.commit()
    print(f"Super admin {email} created.")


if __name__ == "__main__":
    main()
