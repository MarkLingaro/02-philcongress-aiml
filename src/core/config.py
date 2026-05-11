# src/core/config.py
"""
Central configuration — reads from .env (or environment variables).
Import get_settings() anywhere you need a config value.
"""

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # PostgreSQL
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="philcongressai")
    postgres_user: str = Field(default="philcongress")
    postgres_password: str = Field(default="changeme")

    @computed_field
    @property
    def database_url(self) -> str:
        u = self.postgres_user
        p = self.postgres_password
        h = self.postgres_host
        port = self.postgres_port
        db = self.postgres_db
        return f"postgresql+asyncpg://{u}:{p}@{h}:{port}/{db}"

    @computed_field
    @property
    def database_url_sync(self) -> str:
        u = self.postgres_user
        p = self.postgres_password
        h = self.postgres_host
        port = self.postgres_port
        db = self.postgres_db
        return f"postgresql://{u}:{p}@{h}:{port}/{db}"

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="changeme")

    # Qdrant
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_chat_model: str = Field(default="mistral")
    ollama_embed_model: str = Field(default="nomic-embed-text")

    # HREP API — primary bills source (api.congress.gov.ph)
    # Reverse-engineered from LEGIS website DevTools
    # Covers 8th–19th Congress, 5000 req/hour rate limit
    hrep_api_base_url: str = Field(default="https://api.congress.gov.ph/hrep/api-v1")
    hrep_api_token: str = Field(default="cc8bd00d-9b88-4fee-aafe-311c574fcdc1")

    # BetterGov — supplementary / cross-check only
    bettergov_base_url: str = Field(default="https://open-congress-api.bettergov.ph")

    # Bill downloader — PDF fallback (low priority, abstract-first approach)
    bill_pdf_dir: str = Field(default="data/raw/bills")
    bill_download_concurrency: int = Field(default=5)
    bill_download_delay: float = Field(default=0.5)


@lru_cache
def get_settings() -> Settings:
    return Settings()
