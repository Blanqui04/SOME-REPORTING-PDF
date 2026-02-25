"""Create an admin user for the Grafana PDF Reporter.

Usage:
    python -m backend.create_admin
    python -m backend.create_admin --username admin --email admin@example.com --password admin123
"""

import argparse
import logging
import sys

from sqlalchemy import or_

from backend.app.core.config import Settings
from backend.app.core.database import get_session_factory
from backend.app.core.security import hash_password
from backend.app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def create_admin(
    username: str,
    email: str,
    password: str,
) -> None:
    """Create an admin user in the database.

    Args:
        username: Admin username.
        email: Admin email address.
        password: Plain text password to hash.

    Raises:
        SystemExit: If user already exists or DB is unreachable.
    """
    settings = Settings()  # type: ignore[call-arg]
    session_factory = get_session_factory(settings)
    db = session_factory()

    try:
        existing = (
            db.query(User)
            .filter(or_(User.email == email, User.username == username))
            .first()
        )
        if existing is not None:
            if existing.email == email:
                logger.warning("User with email '%s' already exists (id=%s)", email, existing.id)
            else:
                logger.warning("User with username '%s' already exists (id=%s)", username, existing.id)

            # Promote to admin if not already
            if existing.role != "admin" or not existing.is_superuser:
                existing.role = "admin"
                existing.is_superuser = True
                existing.is_active = True
                db.commit()
                logger.info("User '%s' promoted to admin role.", existing.username)
            else:
                logger.info("User '%s' is already an admin.", existing.username)
            return

        user = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            role="admin",
            is_superuser=True,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(
            "Admin user created: username='%s', email='%s', id=%s",
            user.username,
            user.email,
            user.id,
        )
    except Exception as exc:
        db.rollback()
        logger.error("Failed to create admin user: %s", exc)
        sys.exit(1)
    finally:
        db.close()


def main() -> None:
    """Parse arguments and create admin user."""
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--username", default="admin", help="Admin username (default: admin)")
    parser.add_argument(
        "--email", default="admin@grafana-reporter.local", help="Admin email"
    )
    parser.add_argument("--password", default="admin123", help="Admin password")
    args = parser.parse_args()

    create_admin(
        username=args.username,
        email=args.email,
        password=args.password,
    )


if __name__ == "__main__":
    main()
