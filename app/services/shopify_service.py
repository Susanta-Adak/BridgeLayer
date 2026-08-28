"""Facade over the Shopify provider."""

from app.providers.factory import ProviderFactory
from app.providers.schemas import Customer, CustomerInput, Order, Page
from app.providers.shopify.client import ShopifyCommerceProvider


def _provider() -> ShopifyCommerceProvider:
    return ProviderFactory.get_commerce_provider("shopify")


async def create_customer(data: CustomerInput) -> Customer:
    return await _provider().create_customer(data)


async def get_customer(customer_id: str) -> Customer:
    return await _provider().get_customer(customer_id)


async def list_customers(page: int, per_page: int) -> Page:
    return await _provider().list_customers(page, per_page)


async def update_customer(customer_id: str, data: CustomerInput) -> Customer:
    return await _provider().update_customer(customer_id, data)


async def list_orders(page: int, per_page: int) -> Page:
    return await _provider().list_orders(page, per_page)


async def get_order(order_id: str) -> Order:
    return await _provider().get_order(order_id)
