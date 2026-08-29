# CLAUDE.md — BridgeLayer

> Unified integration layer connecting Zoho CRM and Shopify through a single, extensible API — built so adding a new third-party provider tomorrow requires zero changes to existing code.

This file gives Claude (or any contributor) the context needed to work on this codebase effectively.

---

## 1. Project Overview

**BridgeLayer** is a Python-based integration layer that connects independently with **Zoho CRM** and **Shopify**, exposing both through a unified, consistent API. It was built as a take-home technical assignment to demonstrate production-minded API integration, authentication, architecture, and error handling.

**Primary design goal: extensibility.** The single biggest driver of every architectural decision here is: *"How easy is it to plug in a third provider (HubSpot, WooCommerce, Salesforce, etc.) without touching existing Zoho/Shopify code?"* Every pattern chosen below is chosen specifically to serve that goal — see Section 4.

**Core idea:** Zoho and Shopify already have their own APIs — this service doesn't replace them. It sits on top as a middleware/orchestration layer that:
- Handles OAuth/token lifecycle so callers never touch it directly
- Normalizes both providers into one consistent request/response contract
- Validates input before burning external API calls
- Persists tokens and integration data locally (SQLite)
- Returns clean, consistent errors instead of leaking raw provider errors
- Is architected so a third provider (e.g. HubSpot, WooCommerce) could be added without touching core logic

---

## 2. Tech Stack

| Concern | Choice |
|---|---|
| Language | Python 3.11+ |
| Web framework | FastAPI (async, auto Swagger/OpenAPI docs) |
| Database | SQLite (via SQLAlchemy ORM) |
| HTTP client | `httpx` (async) |
| Config | `pydantic-settings` + `.env` |
| Testing | `pytest` + `pytest-mock` / `respx` for HTTP mocking |
| Migrations | Alembic (optional, if schema evolves) |

---

## 3. Architecture Principles

1. **Provider abstraction first.** Both integrations implement a shared base interface (`BaseCRMProvider` / `BaseCommerceProvider` or similar) so routes and business logic never call Zoho/Shopify SDKs directly — they call the abstraction.
2. **Strict separation of concerns.**
   - `providers/` — external API clients (Zoho, Shopify) — nothing but HTTP calls + response parsing
   - `services/` — business logic, validation, orchestration
   - `api/` — FastAPI routers, request/response schemas
   - `db/` — models, session handling, token storage
   - `core/` — config, logging, shared HTTP client, exceptions
3. **No provider-specific logic leaks into `api/` or `db/`.** Adding a new provider should only mean adding a new folder under `providers/` plus a router.
4. **Consistent response envelope** across both integrations: `{ "success": bool, "data": ..., "error": {...} }`.
5. **Tokens are never returned in API responses or logged.**

---

## Core Style Rules
 - Line Length: Limit all lines to a maximum of 79 characters. Limit docstrings and comments to 72 characters.
 - Blank Lines:
   - Surround top-level functions and class definitions with two blank lines.
   - Surround method definitions inside a class with one blank line.
 - Imports:
   - Place imports on separate lines (e.g., write import os and import sys on their own lines, not together).
   - Group imports in this order: standard library imports, related third-party imports, and local application/library specific imports.

 - Naming Conventions:
   - Functions and Variables: Use lowercase words separated by underscores (snake_case).
   - Classes: Use CapWords (capitalizing the first letter of each word, also known as PascalCase).
   - Constants: Use ALL_CAPS with underscores (UPPER_CASE_WITH_UNDERSCORES).
   - Private Attributes: Use a single leading underscore (_protected) or double leading underscores (__private) to restrict access.
          
---
## 4. Design Patterns Applied (extensibility is the whole point)

Reference: [Refactoring.Guru — Catalog of Design Patterns](https://refactoring.guru/design-patterns/catalog)

The goal — "adding a new third-party API should be super easy" — is a textbook case for a small combination of GoF patterns rather than one silver bullet. Here's the mapping:

| Pattern | Category | Where it's used | Why |
|---|---|---|---|
| **[Strategy](https://refactoring.guru/design-patterns/strategy)** | Behavioral | `providers/base.py` defines `BaseCRMProvider` / `BaseCommerceProvider` interfaces (e.g. `create_contact()`, `list_orders()`) | Each provider (Zoho, Shopify, future HubSpot) is an interchangeable strategy implementing the same contract. Services depend only on the interface, never the concrete class. |
| **[Factory Method](https://refactoring.guru/design-patterns/factory-method)** | Creational | `providers/factory.py` — `ProviderFactory.get_crm_provider("zoho")` | Callers ask for "a CRM provider" by name/config; the factory decides which concrete class to instantiate. Adding a provider = register it in the factory, nothing else changes. |
| **[Adapter](https://refactoring.guru/design-patterns/adapter)** | Structural | Inside each provider (e.g. `zoho/contacts.py`, `shopify/customers.py`) | Zoho and Shopify return wildly different JSON shapes. Each provider adapts its raw response into BridgeLayer's own unified internal schema (e.g. a common `Contact` / `Order` DTO) before handing it to the service layer. |
| **[Template Method](https://refactoring.guru/design-patterns/template-method)** | Behavioral | `providers/base.py` — shared `authenticated_request()` flow | The "make request → check for 401 → refresh token → retry once → return" sequence is identical across providers. The base class defines the skeleton; each provider only overrides the auth-specific steps (`get_access_token()`, `refresh_token()`). |
| **[Facade](https://refactoring.guru/design-patterns/facade)** | Structural | `services/zoho_service.py`, `services/shopify_service.py` | API routes talk to one simple service method (e.g. `zoho_service.create_contact(data)`), which internally coordinates validation, the provider, and DB persistence — hiding that complexity from `api/`. |
| **[Singleton](https://refactoring.guru/design-patterns/singleton)** *(lightweight, via DI)* | Creational | `core/http_client.py` shared async client, DB session factory | One shared, connection-pooled HTTP client and DB session per app lifecycle instead of creating new ones per request. |

### How this achieves "super easy to add a new provider"

To add, say, HubSpot, in the future a contributor should only need to:
1. Create `providers/hubspot/` implementing `BaseCRMProvider` (Strategy)
2. Register `"hubspot"` in `ProviderFactory` (Factory Method)
3. Add a thin `services/hubspot_service.py` (Facade) and a router in `api/`

**Nothing in `api/`, `db/`, or the Zoho/Shopify code should need to change.** This is the concrete, demonstrable proof point for the assignment's "Architecture" and "Bonus: Additional provider abstraction" evaluation criteria — it may be worth actually stubbing a fake third provider (e.g. a mock "DemoCRM") to prove this works in practice, since it's explicitly called out as a bonus point.

---

## 5. Proposed Project Structure

```
bridgelayer/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py          # env/.env settings
│   │   ├── logging.py
│   │   ├── http_client.py     # shared async HTTP client w/ retry (Singleton)
│   │   └── exceptions.py
│   ├── db/
│   │   ├── database.py
│   │   ├── models.py          # Token, ContactCache, etc.
│   │   └── session.py
│   ├── providers/
│   │   ├── base.py            # BaseCRMProvider / BaseCommerceProvider (Strategy + Template Method)
│   │   ├── factory.py         # ProviderFactory — registers & instantiates providers (Factory Method)
│   │   ├── schemas.py         # unified internal DTOs (Contact, Lead, Customer, Order)
│   │   ├── zoho/
│   │   │   ├── auth.py        # OAuth flow + token refresh
│   │   │   ├── client.py
│   │   │   ├── contacts.py    # adapts Zoho JSON → unified DTO (Adapter)
│   │   │   └── leads.py
│   │   ├── shopify/
│   │   │   ├── auth.py
│   │   │   ├── client.py
│   │   │   ├── customers.py   # adapts Shopify JSON → unified DTO (Adapter)
│   │   │   └── orders.py
│   │   └── demo_provider/     # stub 3rd provider proving extensibility (bonus points)
│   ├── services/
│   │   ├── zoho_service.py    # Facade over zoho provider + validation + persistence
│   │   └── shopify_service.py # Facade over shopify provider + validation + persistence
│   ├── api/
│   │   ├── routes_zoho.py
│   │   ├── routes_shopify.py
│   │   └── schemas.py
│   └── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 6. Feature Scope

### Zoho CRM (OAuth 2.0)
- Auth: authorization code exchange, access + refresh token handling, auto-refresh on expiry
- Contacts: Create / Get by ID / List / Update / Delete
- Leads: Create / List / Get by ID
- Fields: `first_name`, `last_name`, `email`, `phone`, `company` (+ `lead_source` for leads)

### Shopify (OAuth 2.0, static-token fallback)
- Auth: authorization code exchange (shop/state/HMAC verification
  on callback) for a permanent offline access token, stored in the
  `tokens` table. Falls back to a static `SHOPIFY_ACCESS_TOKEN`
  (custom/private app) if no OAuth token has been stored yet.
- Customers: Create / Get / List / Update
- Orders: List / Get by ID
- Order fields exposed: `order_id`, `customer`, `total_price`, `currency`, `order_status`, `created_at`

---

## 7. Non-Negotiables (from assignment spec)

- No hardcoded credentials anywhere — `.env` + `.env.example` only
- `.gitignore` must exclude `.env` and any generated secrets
- All external API failures handled gracefully with meaningful error responses
- Input validation before external calls
- Meaningful logging (no secrets/tokens in logs)
- README must cover setup, config, auth, DB schema, API usage, run instructions
- Tests for core business logic and API endpoints

## 8. Bonus (stretch goals, in priority order)

1. Retry with backoff for transient failures
2. Pagination support on list endpoints
3. Docker/Docker Compose
4. Rate-limit handling
5. A third mock/demo provider to prove extensibility
6. Webhook support

---

## 9. Conventions for Claude

- **Extensibility is the north star.** Before writing any Zoho/Shopify-specific code, ask "would this force a change elsewhere if I added a third provider?" If yes, it belongs in `base.py` / `factory.py`, not in a provider-specific file.
- Always implement new providers against the `BaseCRMProvider` / `BaseCommerceProvider` interface (Section 4) — never let `api/` or `services/` import a concrete provider class directly; go through `ProviderFactory`.
- Prefer async/await throughout (FastAPI + httpx are both async-native).
- Every provider method should raise typed exceptions (`ProviderAuthError`, `ProviderAPIError`, `ProviderTimeoutError`) caught centrally and mapped to HTTP responses — don't let raw provider exceptions bubble to the API layer.
- Write provider clients so they're testable without live API calls (inject the HTTP client, mock at the transport level).
- Keep Zoho and Shopify code fully independent — no shared provider-specific code, only shared *generic* utilities (HTTP client, retry logic, base interfaces, Template Method skeleton).
- When in doubt about scope, remember: this demonstrates *pattern*, not full platform coverage — don't over-build beyond the listed endpoints unless going for bonus points.