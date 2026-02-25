"""Application configuration loaded from environment variables."""

from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    All settings can be overridden via a .env file or direct
    environment variables. Required fields have no defaults
    and will raise a validation error if not provided.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # --- Application ---
    APP_NAME: str = "Grafana PDF Reporter"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # --- Database ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "grafana_reporter"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "grafana_reporter"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Construct the synchronous SQLAlchemy database URL."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:"
            f"{quote_plus(self.POSTGRES_PASSWORD)}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- JWT Authentication ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- Grafana ---
    GRAFANA_URL: str
    GRAFANA_API_KEY: str
    GRAFANA_TIMEOUT: int = 30

    # --- Redis & Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_TIMEOUT: int = 600

    # --- SMTP (Email) ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@grafana-reporter.local"
    SMTP_TLS: bool = True

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # --- LDAP / Active Directory ---
    LDAP_ENABLED: bool = False
    LDAP_SERVER: str = ""
    LDAP_PORT: int = 389
    LDAP_USE_SSL: bool = False
    LDAP_BIND_DN: str = ""
    LDAP_BIND_PASSWORD: str = ""
    LDAP_SEARCH_BASE: str = ""
    LDAP_USER_FILTER: str = "(sAMAccountName={username})"
    LDAP_EMAIL_ATTRIBUTE: str = "mail"
    LDAP_DISPLAY_NAME_ATTRIBUTE: str = "displayName"
    LDAP_DEFAULT_ROLE: str = "editor"

    # --- TOTP 2FA ---
    TOTP_ENABLED: bool = False
    TOTP_ISSUER: str = "Grafana PDF Reporter"

    # --- Webhook Notifications ---
    WEBHOOK_SLACK_URL: str = ""
    WEBHOOK_TEAMS_URL: str = ""
    WEBHOOK_GENERIC_URL: str = ""

    # --- S3 / MinIO Object Storage ---
    S3_ENABLED: bool = False
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET_NAME: str = "grafana-reports"
    S3_REGION: str = "us-east-1"

    # --- Prometheus Metrics ---
    PROMETHEUS_ENABLED: bool = False
