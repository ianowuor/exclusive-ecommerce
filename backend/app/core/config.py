from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    database_url: str = Field(
        "postgresql+psycopg://postgres:postgres@db:5432/exclusive_ecommerce",
        alias="DATABASE_URL",
    )

    SHOPIFY_STORE_URL: str
    SHOPIFY_ACCESS_TOKEN: str
    SHOPIFY_API_SECRET: str
    SHOPIFY_LOCATION_ID: str
    SHOPIFY_API_VERSION: str = "2025-01"
    SHOPIFY_WEBHOOK_SECRET: str

    jwt_secret_key: str = Field("change_me_super_secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_minutes: int = Field(60 * 24 * 7, alias="JWT_REFRESH_TOKEN_EXPIRE_MINUTES")

    # In Docker dev, compose mounts `./backend/uploads` -> `/app/uploads`.
    uploads_dir: str = Field("./uploads", alias="UPLOADS_DIR")
    cors_origins_raw: str = Field(
        "http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


settings = Settings()

