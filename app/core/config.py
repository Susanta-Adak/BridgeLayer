from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./bridgelayer.db"

    zoho_client_id: str = ""
    zoho_client_secret: str = ""
    zoho_redirect_uri: str = ""
    zoho_accounts_base_url: str = "https://accounts.zoho.in"
    zoho_api_base_url: str = "https://www.zohoapis.in"

    shopify_shop_domain: str = ""
    shopify_access_token: str = ""
    shopify_api_version: str = "2024-07"
    shopify_webhook_secret: str = ""
    shopify_client_id: str = ""
    shopify_client_secret: str = ""
    shopify_redirect_uri: str = (
        "http://localhost:8000/api/v1/shopify/auth/callback"
    )
    shopify_scopes: str = "read_customers,write_customers,read_orders"

    http_timeout_seconds: float = 15.0
    http_max_retries: int = 3
    http_backoff_base_seconds: float = 0.5


@lru_cache
def get_settings() -> Settings:
    return Settings()
