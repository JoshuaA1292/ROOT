from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "backend/.env", "../.env"],
        extra="ignore",
    )

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "root_trees"
    mongodb_access_mode: str = "repository"  # repository | mcp
    mongodb_mcp_config_path: str = "mcp/mcp.config.json"

    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    google_application_credentials: str = ""

    agent_builder_location: str = "us-central1"
    agent_builder_agent_id: str = ""

    google_ai_studio_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    nyc_dob_permit_url: str = ""
    parks_tree_work_url: str = ""
    portland_tree_inventory_url: str = ""
    seattle_tree_inventory_url: str = ""

    auth_mode: str = "dev_header"  # dev_header | iap | firebase | oauth

    nyc_parks_submission_url: str = ""
    community_board_submission_url: str = ""
    agency_submission_api_key: str = ""

    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Email — Resend (recommended: just one API key) or SMTP
    resend_api_key: str = ""          # Get free key at resend.com — set RESEND_API_KEY
    # SMTP fallback
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "guardian@root-trees.app"
    notification_email: str = ""  # recipient address for guardian emails

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Defer to function call at access time — avoids module-level env validation
settings = get_settings()
