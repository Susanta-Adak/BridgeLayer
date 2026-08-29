"""Facade over the Shopify provider."""

from app.db import repository
from app.providers.factory import ProviderFactory
from app.providers.schemas import Customer, CustomerInput, Order, Page
from app.providers.shopify import auth as shopify_auth
from app.providers.shopify.client import ShopifyCommerceProvider

_PROVIDER = "shopify"


def _provider() -> ShopifyCommerceProvider:
    return ProviderFactory.get_commerce_provider("shopify")


def get_authorization_url() -> str:
    return shopify_auth.build_authorization_url()


async def handle_oauth_callback(*, params: dict, hmac_signature: str) -> None:
    shop = params.get("shop", "")
    code = params.get("code", "")
    state = params.get("state", "")

    shopify_auth.verify_shop_domain(shop)
    shopify_auth.verify_state(state)
    shopify_auth.verify_callback_hmac(params, hmac_signature)
    await shopify_auth.exchange_code_for_token(shop, code)


async def create_customer(data: CustomerInput) -> Customer:
    customer = await _provider().create_customer(data)
    repository.upsert_record(
        _PROVIDER, "customer", customer.id, customer.model_dump()
    )
    return customer


async def get_customer(customer_id: str) -> Customer:
    return await _provider().get_customer(customer_id)


async def list_customers(page: int, per_page: int) -> Page:
    return await _provider().list_customers(page, per_page)


async def update_customer(customer_id: str, data: CustomerInput) -> Customer:
    customer = await _provider().update_customer(customer_id, data)
    repository.upsert_record(
        _PROVIDER, "customer", customer.id, customer.model_dump()
    )
    return customer


async def list_orders(page: int, per_page: int) -> Page:
    return await _provider().list_orders(page, per_page)


async def get_order(order_id: str) -> Order:
    return await _provider().get_order(order_id)
