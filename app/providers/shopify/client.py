from app.core.config import get_settings
from app.providers.base import BaseCommerceProvider
from app.providers.shopify import auth as shopify_auth
from app.providers.shopify.customers import ShopifyCustomersMixin
from app.providers.shopify.orders import ShopifyOrdersMixin


class ShopifyCommerceProvider(
    ShopifyCustomersMixin, ShopifyOrdersMixin, BaseCommerceProvider
):
    name = "shopify"

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def base_url(self) -> str:
        return (
            f"https://{self._settings.shopify_shop_domain}"
            f"/admin/api/{self._settings.shopify_api_version}"
        )

    async def get_access_token(self) -> str:
        return self._current_token()

    async def refresh_token(self) -> str:
        # Neither an OAuth offline token nor a static custom-app
        # token can be silently refreshed - re-read whatever's on
        # file so a genuinely invalid token surfaces a clear
        # ProviderAuthError via the base class's retry-once check.
        return self._current_token()

    def _current_token(self) -> str:
        token = shopify_auth.load_token()
        if token is not None:
            return token.access_token
        return shopify_auth.get_static_access_token()

    def is_token_expired(self) -> bool:
        return False

    def build_auth_headers(self, token: str) -> dict[str, str]:
        return {"X-Shopify-Access-Token": token}
