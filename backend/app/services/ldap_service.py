"""LDAP / Active Directory authentication service.

Authenticates users against an LDAP or Active Directory server.
When a user logs in via LDAP for the first time, a local User
record is created automatically (JIT provisioning).
"""

import logging

from ldap3 import ALL, Connection, Server  # type: ignore[import-untyped]
from ldap3.core.exceptions import LDAPException  # type: ignore[import-untyped]

from backend.app.core.config import Settings

logger = logging.getLogger(__name__)


class LDAPAuthResult:
    """Result of an LDAP authentication attempt."""

    def __init__(
        self,
        *,
        success: bool,
        username: str = "",
        email: str = "",
        display_name: str = "",
        error: str = "",
    ) -> None:
        self.success = success
        self.username = username
        self.email = email
        self.display_name = display_name
        self.error = error


class LDAPService:
    """Authenticates users against LDAP / Active Directory.

    Uses a service account (bind DN) to search for the user, then
    attempts to bind as that user to verify credentials.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._server = Server(
            host=settings.LDAP_SERVER,
            port=settings.LDAP_PORT,
            use_ssl=settings.LDAP_USE_SSL,
            get_info=ALL,
        )

    def authenticate(self, username: str, password: str) -> LDAPAuthResult:
        """Authenticate a user against the LDAP directory.

        Steps:
            1. Bind with service account
            2. Search for user entry using configurable filter
            3. Attempt bind with user's DN and password
            4. Extract email and display name attributes

        Args:
            username: The username to authenticate.
            password: The plaintext password.

        Returns:
            LDAPAuthResult with success status and user attributes.
        """
        if not self._settings.LDAP_SERVER:
            return LDAPAuthResult(success=False, error="LDAP server not configured")

        try:
            # 1. Bind with service account
            conn = Connection(
                self._server,
                user=self._settings.LDAP_BIND_DN,
                password=self._settings.LDAP_BIND_PASSWORD,
                auto_bind=True,
                read_only=True,
            )

            # 2. Search for user
            search_filter = self._settings.LDAP_USER_FILTER.replace(
                "{username}", username
            )
            conn.search(
                search_base=self._settings.LDAP_SEARCH_BASE,
                search_filter=search_filter,
                attributes=[
                    self._settings.LDAP_EMAIL_ATTRIBUTE,
                    self._settings.LDAP_DISPLAY_NAME_ATTRIBUTE,
                ],
            )

            if not conn.entries:
                logger.info("LDAP user not found: %s", username)
                conn.unbind()
                return LDAPAuthResult(
                    success=False, error="User not found in directory"
                )

            entry = conn.entries[0]
            user_dn = str(entry.entry_dn)
            email = str(
                getattr(entry, self._settings.LDAP_EMAIL_ATTRIBUTE, "")
            )
            display_name = str(
                getattr(entry, self._settings.LDAP_DISPLAY_NAME_ATTRIBUTE, "")
            )
            conn.unbind()

            # 3. Verify user credentials by binding as the user
            user_conn = Connection(
                self._server,
                user=user_dn,
                password=password,
                auto_bind=True,
                read_only=True,
            )
            user_conn.unbind()

            logger.info("LDAP authentication successful: %s", username)
            return LDAPAuthResult(
                success=True,
                username=username,
                email=email or f"{username}@ldap.local",
                display_name=display_name or username,
            )

        except LDAPException as e:
            logger.warning("LDAP authentication failed for %s: %s", username, e)
            return LDAPAuthResult(
                success=False, error="Invalid credentials or LDAP error"
            )
