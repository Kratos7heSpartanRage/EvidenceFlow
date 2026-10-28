from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """EvidenceFlow application configuration.

    All settings can be overridden via environment variables or a local .env file.
    No secrets should be committed to version control.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "sqlite:///./evidenceflow.db"
    HTTP_TIMEOUT: int = 20
    IMPORT_CAP: int = 500

    # NCBI E-utilities requirements
    NCBI_EMAIL: str = "researcher@example.edu"
    NCBI_TOOL: str = "evidenceflow"
    NCBI_API_KEY: str | None = None

    HOST: str = "127.0.0.1"
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v


settings = Settings()
