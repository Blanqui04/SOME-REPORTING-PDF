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

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
