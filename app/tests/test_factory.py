import pytest

from app.core.exceptions import ProviderNotFoundError
from app.providers.demo_provider.client import DemoCRMProvider
from app.providers.factory import ProviderFactory
from app.providers.shopify.client import ShopifyCommerceProvider
from app.providers.zoho.client import ZohoCRMProvider


def test_get_crm_provider_zoho_returns_zoho_instance():
    provider = ProviderFactory.get_crm_provider("zoho")
    assert isinstance(provider, ZohoCRMProvider)


def test_get_crm_provider_demo_returns_demo_instance():
    provider = ProviderFactory.get_crm_provider("demo")
    assert isinstance(provider, DemoCRMProvider)


def test_get_commerce_provider_shopify_returns_shopify_instance():
    provider = ProviderFactory.get_commerce_provider("shopify")
    assert isinstance(provider, ShopifyCommerceProvider)


def test_get_crm_provider_unknown_name_raises():
    with pytest.raises(ProviderNotFoundError):
        ProviderFactory.get_crm_provider("hubspot")


def test_get_commerce_provider_unknown_name_raises():
    with pytest.raises(ProviderNotFoundError):
        ProviderFactory.get_commerce_provider("woocommerce")
