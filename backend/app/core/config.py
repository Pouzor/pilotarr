from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App config"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DB_HOST: str
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    # Security
    SECRET_KEY: str
    API_KEY: str
    WEBHOOK_SECRET: str
    ACCESS_TOKEN_EXPIRE_HOURS: int = 48  # 2 days
    DEFAULT_ADMIN_PASSWORD: str = "pilotarr"  # Override in .env — change after first login
    CORS_ORIGINS: list[str] = ["http://localhost", "http://localhost:4028"]
    COOKIE_SECURE: bool = False  # Set True when serving over HTTPS

    # App Info
    APP_NAME: str = "Pilotarr"
    APP_VERSION: str = "1.5.1"

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        """MariaDB connexion url"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
