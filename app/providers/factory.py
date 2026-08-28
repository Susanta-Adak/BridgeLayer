"""Factory Method: callers ask for "a CRM provider" / "a commerce

provider" by name; the factory decides which concrete class to
instantiate. Adding a new provider means registering it here (and
in `_register_builtin_providers`) - nothing else in the codebase
changes.
"""

from collections.abc import Callable

from app.core.exceptions import ProviderNotFoundError
from app.providers.base import BaseCommerceProvider, BaseCRMProvider


class ProviderFactory:
    _crm_registry: dict[str, Callable[[], BaseCRMProvider]] = {}
    _commerce_registry: dict[str, Callable[[], BaseCommerceProvider]] = {}

    @classmethod
    def register_crm_provider(
        cls, name: str, builder: Callable[[], BaseCRMProvider]
    ) -> None:
        cls._crm_registry[name] = builder

    @classmethod
    def register_commerce_provider(
        cls, name: str, builder: Callable[[], BaseCommerceProvider]
    ) -> None:
        cls._commerce_registry[name] = builder

    @classmethod
    def get_crm_provider(cls, name: str) -> BaseCRMProvider:
        try:
            builder = cls._crm_registry[name]
        except KeyError:
            raise ProviderNotFoundError(
                f"Unknown CRM provider: {name!r}. "
                f"Available: {sorted(cls._crm_registry)}"
            ) from None
        return builder()

    @classmethod
    def get_commerce_provider(cls, name: str) -> BaseCommerceProvider:
        try:
            builder = cls._commerce_registry[name]
        except KeyError:
            raise ProviderNotFoundError(
                f"Unknown commerce provider: {name!r}. "
                f"Available: {sorted(cls._commerce_registry)}"
            ) from None
        return builder()


def _register_builtin_providers() -> None:
    """Import + register the providers that ship with BridgeLayer.

    Imports are deferred to here (rather than at module top level) to
    avoid import cycles between the factory and provider packages.
    """
    from app.providers.demo_provider.client import DemoCRMProvider
    from app.providers.shopify.client import ShopifyCommerceProvider
    from app.providers.zoho.client import ZohoCRMProvider

    ProviderFactory.register_crm_provider("zoho", ZohoCRMProvider)
    ProviderFactory.register_crm_provider("demo", DemoCRMProvider)
    ProviderFactory.register_commerce_provider(
        "shopify", ShopifyCommerceProvider
    )


_register_builtin_providers()
