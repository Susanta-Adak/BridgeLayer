# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Unified integration layer connecting Zoho CRM and Shopify through a single API — organized as one fully self-contained module per provider so adding a third provider tomorrow means copying that module's folder shape, not editing shared code.

---

## Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in credentials

# Run the dev server (http://localhost:8000, docs at /docs)
uvicorn app.main:app --reload

# Run the full test suite (no live API calls - Zoho/Shopify HTTP
# calls are respx-mocked; a temp SQLite DB is created per test run)
pytest

# Run a single test file
pytest app/tests/test_zoho_contacts.py

# Run a single test by name
pytest app/tests/test_zoho_contacts.py::test_create_contact_creates_then_fetches_record

# Run via Docker (persists the SQLite file in a named volume)
docker compose up --build
```

There is no configured linter/formatter (no ruff/black/flake8 config in this repo) — follow the "Core Style Rules" below by hand.

---

## 1. Project Overview

**BridgeLayer** is a Python-based integration layer that connects independently with **Zoho CRM** and **Shopify**, exposing both through a unified, consistent API. It was built as a take-home technical assignment to demonstrate production-minded API integration, authentication, architecture, and error handling.

**Primary design goal: extensibility via a consistent module template**, not a shared polymorphic abstraction. Earlier iterations of this codebase used a shared `BaseCRMProvider`/`ProviderFactory` (Strategy + Factory Method) so every provider ran through one common interface. This was deliberately dropped in favor of **package-by-feature**: each provider is a fully standalone module, and extensibility comes from every module following the same internal shape, not from inheriting a shared base class. See Section 4.

**Core idea:** Zoho and Shopify already have their own APIs — this service doesn't replace them. It sits on top as a middleware/orchestration layer that:
- Handles OAuth/token lifecycle per provider so callers never touch it directly
- Gives each provider its own consistent request/response contract (its own `schemas.py` per resource)
- Validates input before burning external API calls
- Persists OAuth tokens locally (SQLite) — **Zoho and Shopify remain the source of truth for all business data**, so contacts/leads/customers/orders are never cached or duplicated locally (see the README's "Local persistence" section for why)
- Returns clean, consistent errors instead of leaking raw provider errors
- Is organized so a third provider (e.g. HubSpot, WooCommerce) can be added by copying an existing module's folder shape into `modules/<provider>/`, without editing Zoho/Shopify code

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

1. **Package by feature (provider), not by layer.** Each provider lives entirely under `app/modules/<provider>/`: its own auth flow + token table, its own HTTP client, and one subfolder per resource (`contacts/`, `leads/`, `customers/`, `orders/`) holding that resource's `schemas.py` (request/response), `service.py` (business logic + provider call), and `router.py` (FastAPI router). Nothing crosses from `modules/zoho/` into `modules/shopify/` or vice versa.
2. **`core/` and `db/` hold only generic, non-provider infrastructure.** `core/` = config, logging, the shared pooled HTTP client, typed exceptions, and the generic response-envelope/pagination schemas. `db/` = the SQLAlchemy engine and session factory only — no table definitions live here; only each provider's `auth/models.py` owns a table.
3. **No provider-specific logic leaks into `core/` or `db/`.** Adding a new provider should only mean creating `app/modules/<provider>/` and registering its routers in `main.py`.
4. **Consistent response envelope** across every provider: `{ "success": bool, "data": ..., "error": {...} }` (defined once, in `core/schemas.py`).
5. **Tokens are never returned in API responses or logged.**
6. **Zoho and Shopify are the source of truth.** Resource `service.py` files (`contacts/`, `leads/`, `customers/`, `orders/`) never touch the local DB — they call the provider and return its response, mapped. Only `auth/service.py` reads/writes the database (the OAuth token), keeping authentication cleanly separate from business logic — see Section 9.

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
## 4. Design Patterns Applied

Reference: [Refactoring.Guru — Catalog of Design Patterns](https://refactoring.guru/design-patterns/catalog)

This version intentionally uses fewer GoF patterns than a classic layered design would, in favor of module-per-provider simplicity. What's still applied, and what was deliberately dropped:

| Pattern | Category | Where it's used | Why |
|---|---|---|---|
| **[Facade](https://refactoring.guru/design-patterns/facade)** | Structural | Every resource's `service.py` (e.g. `modules/zoho/contacts/service.py`) | The router (`router.py`) talks to one simple function (e.g. `service.create_contact(data)`), which internally coordinates the provider call and JSON mapping — hiding that complexity from `router.py`. |
| **[Adapter](https://refactoring.guru/design-patterns/adapter)** | Structural | Inside each resource's `service.py` (e.g. `_from_zoho_record`, `_to_zoho_payload`) | Zoho and Shopify return wildly different JSON shapes. Each service maps its provider's raw response to/from that module's own `schemas.py` types — inline now, since there's no cross-provider DTO to adapt into. |
| **[Singleton](https://refactoring.guru/design-patterns/singleton)** *(lightweight, via DI)* | Creational | `core/http_client.py` shared async client, DB session factory | One shared, connection-pooled HTTP client and DB session per app lifecycle instead of creating new ones per request. This is generic infrastructure, not provider-specific, so it stays in `core/`. |

**Deliberately dropped** (present in earlier iterations, removed in favor of standalone modules):
- **Strategy** (`BaseCRMProvider`/`BaseCommerceProvider`) — there is no shared provider interface anymore. Each module's `client.py` and `service.py` have their own shapes.
- **Factory Method** (`ProviderFactory`) — nothing looks up "a CRM provider by name" anymore; `router.py` imports its own module's `service.py` directly.
- **Template Method** (shared `authenticated_request()`) — each provider's `client.py` implements its own get-token/refresh/retry-once flow. This is genuinely duplicated between `modules/zoho/client.py` and `modules/shopify/client.py` — an accepted tradeoff for module isolation, not an oversight.

### How this achieves "easy to add a new provider"

To add, say, HubSpot, a contributor should only need to:
1. Create `app/modules/hubspot/` with the same internal shape as `modules/zoho/`: `auth/` (own token table + OAuth logic), `client.py` (own request/retry logic), and one subfolder per resource with `schemas.py`/`service.py`/`router.py` (no `models.py` — HubSpot stays the source of truth for its own data, same as Zoho/Shopify).
2. Register its routers in `app/main.py` (`app.include_router(...)`).

**Nothing in `core/`, `db/`, or the Zoho/Shopify modules should need to change.** There is currently no third provider module in the codebase to demonstrate this live — an earlier in-memory `demo` module that proved it out was removed. The claim rests on `modules/zoho/` and `modules/shopify/` already being structurally independent of each other, not on shared code either of them would need to be pulled out of.

---

## 5. Project Structure

```
bridgelayer/
├── app/
│   ├── main.py                    # FastAPI app, lifespan, router registration
│   ├── core/
│   │   ├── config.py              # env/.env settings
│   │   ├── logging.py
│   │   ├── http_client.py         # shared async HTTP client w/ retry (Singleton)
│   │   ├── schemas.py             # Envelope, ErrorDetail, PageMeta, AuthUrlResponse
│   │   ├── deps.py                # envelope() helper
│   │   └── exceptions.py          # typed exceptions + envelope-mapping handlers
│   ├── db/
│   │   ├── database.py            # Base, engine, SessionLocal, init_db()
│   │   └── session.py
│   ├── modules/
│   │   ├── zoho/
│   │   │   ├── auth/
│   │   │   │   ├── models.py      # ZohoToken (own table)
│   │   │   │   ├── service.py     # OAuth code exchange + refresh
│   │   │   │   └── router.py      # /zoho/auth/*
│   │   │   ├── client.py          # Zoho's own authenticated_request + retry/refresh
│   │   │   ├── contacts/
│   │   │   │   ├── schemas.py     # ContactRequest/ContactResponse/ContactListResponse
│   │   │   │   ├── service.py     # Facade: call Zoho, map JSON, return it - no local DB
│   │   │   │   └── router.py      # /zoho/contacts router
│   │   │   └── leads/             # same shape as contacts/
│   │   └── shopify/
│   │       ├── auth/              # same shape as zoho/auth/, own ShopifyToken table
│   │       ├── client.py
│   │       ├── customers/         # same shape as zoho/contacts/
│   │       ├── orders/            # same shape, read-only
│   │       └── webhooks.py        # /webhooks/shopify
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
  on callback) for a permanent offline access token, stored in
  `modules/shopify/auth`'s own `shopify_tokens` table. Falls back to
  a static `SHOPIFY_ACCESS_TOKEN` (custom/private app) if no OAuth
  token has been stored yet.
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

- **Extensibility is the north star, achieved by template, not polymorphism.** Before writing any Zoho/Shopify-specific code, ask "would a new provider need to know about this?" If yes, it doesn't belong in `core/`; it belongs inside that provider's own `modules/<provider>/` folder. A new provider should never need to import anything from `modules/zoho/` or `modules/shopify/`.
- Never let one provider's module import another provider's module (no `modules/shopify/` importing from `modules/zoho/`, or vice versa). Cross-resource imports *within* the same provider are fine (e.g. `modules/shopify/orders/schemas.py` importing `CustomerResponse` from `modules/shopify/customers/schemas.py`).
- Prefer async/await throughout (FastAPI + httpx are both async-native) for provider HTTP calls; local DB access stays synchronous (see README's "Design decisions").
- Every provider method should raise typed exceptions (`ProviderAuthError`, `ProviderAPIError`, `ProviderTimeoutError`, all from `core/exceptions.py`) caught centrally and mapped to HTTP responses — don't let raw provider exceptions bubble to the API layer.
- Write each module's `client.py` so it's testable without live API calls (respx-mock at the transport level via the shared `core/http_client.py`).
- Keep provider modules fully independent — no shared provider-specific code between `modules/zoho/` and `modules/shopify/`, only shared *generic* utilities from `core/` (HTTP client, exceptions, envelope/pagination schemas).
- **Never add a `models.py` to a resource folder (`contacts/`, `leads/`, `customers/`, `orders/`).** Zoho and Shopify are the source of truth for that data — `service.py` calls the provider and returns its response, mapped, and nothing more. If a future requirement genuinely needs local caching, that's a deliberate decision to revisit (and re-document in the README), not a default to reach for per-resource.
- **The database is for OAuth tokens only.** Only `auth/models.py` and `auth/service.py` (per provider) may import `app.db`/use `SessionLocal`. This is what keeps authentication cleanly separate from business logic — a resource's `service.py` should never need a DB session for anything.
- When in doubt about scope, remember: this demonstrates *pattern*, not full platform coverage — don't over-build beyond the listed endpoints unless going for bonus points.
