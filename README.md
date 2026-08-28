# BridgeLayer

Unified integration layer connecting **Zoho CRM** and **Shopify**
through a single, consistent API — architected so a third provider
(HubSpot, WooCommerce, ...) can be added without touching existing
code. A stub `demo` provider ships alongside Zoho/Shopify as a live
proof of that claim (see [Extensibility](#extensibility-the-demo-provider)).

Every response, regardless of endpoint or outcome, uses the same
envelope:

```json
{ "success": true, "data": { ... }, "error": null }
```

```json
{ "success": false, "data": null, "error": { "code": "not_found", "message": "...", "details": {} } }
```

## Contents

- [Architecture](#architecture)
- [Setup](#setup)
- [Configuration](#configuration)
- [Zoho OAuth flow](#zoho-oauth-flow)
- [Database schema](#database-schema)
- [API usage](#api-usage)
- [Extensibility: the demo provider](#extensibility-the-demo-provider)
- [Running tests](#running-tests)
- [Docker](#docker)
- [Design decisions & known limitations](#design-decisions--known-limitations)

## Architecture

```
app/
├── main.py             FastAPI app, lifespan, exception handlers, routers
├── core/                config, logging, shared HTTP client, exceptions
├── db/                   SQLAlchemy engine, Token model, session
├── providers/
│   ├── base.py           BaseCRMProvider / BaseCommerceProvider (Strategy)
│   │                     + authenticated_request Template Method
│   ├── factory.py        ProviderFactory (Factory Method)
│   ├── schemas.py         unified internal DTOs
│   ├── zoho/              OAuth2, CRM v3 Contacts/Leads (Adapter)
│   ├── shopify/           static-token auth, Customers/Orders (Adapter)
│   └── demo_provider/     in-memory stub CRM proving extensibility
├── services/             Facade layer api/ talks to
└── api/                  routers + request/response schemas
```

See `CLAUDE.md` in the repo root for the full design-pattern rationale
(Strategy, Factory Method, Adapter, Template Method, Facade, Singleton).

## Setup

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in credentials, see below
uvicorn app.main:app --reload
```

Interactive API docs: http://localhost:8000/docs

## Configuration

All configuration is via environment variables (`.env`, loaded by
`pydantic-settings`). See `.env.example` for the full list. Nothing
is hardcoded; `.env` is gitignored.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLite URL, e.g. `sqlite:///./bridgelayer.db` |
| `ZOHO_CLIENT_ID` / `ZOHO_CLIENT_SECRET` | From a Server-based Application at api-console.zoho.com |
| `ZOHO_REDIRECT_URI` | Must match the redirect URI registered with Zoho |
| `ZOHO_ACCOUNTS_BASE_URL` | Data-center specific (`.com`, `.eu`, `.in`, ...) |
| `ZOHO_API_BASE_URL` | Data-center specific |
| `SHOPIFY_SHOP_DOMAIN` | `your-store.myshopify.com` |
| `SHOPIFY_ACCESS_TOKEN` | Custom/private app Admin API access token |
| `SHOPIFY_WEBHOOK_SECRET` | Optional; enables HMAC verification on `/webhooks/shopify` |

## Zoho OAuth flow

Zoho contacts/leads require a one-time authorization before any
CRM call will work:

1. `GET /zoho/auth/authorize` → returns `{ authorization_url }`.
   Open it in a browser (or hit `GET /zoho/auth/authorize/redirect`
   to be redirected straight there).
2. Approve access. Zoho redirects to `ZOHO_REDIRECT_URI` with a
   `code` query param.
3. That redirect must land on `GET /zoho/auth/callback?code=...`,
   which exchanges the code for an access + refresh token and
   stores them in the `tokens` table.

After that, every Zoho call transparently refreshes the access
token when it's expired or when the API returns a 401 — callers
never see a token.

Shopify uses a static custom-app Admin API access token instead of
an OAuth dance, so no authorization step is needed there.

## Database schema

Single table, `tokens`:

| Column | Type | Notes |
|---|---|---|
| `id` | int, PK | |
| `provider` | string, unique | e.g. `"zoho"` |
| `access_token` | string | never returned in API responses or logged |
| `refresh_token` | string, nullable | |
| `expires_at` | datetime, nullable | UTC |
| `created_at` / `updated_at` | datetime | UTC |

Tables are created automatically on startup (`init_db()` in the
app lifespan) — no manual migration step for this scope.

## API usage

All endpoints return the envelope shown above. Examples:

```bash
# Zoho contacts
curl -X POST localhost:8000/zoho/contacts \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"Ada","last_name":"Lovelace","email":"ada@example.com"}'

curl localhost:8000/zoho/contacts?page=1&per_page=20

# Zoho leads
curl -X POST localhost:8000/zoho/leads \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"Grace","last_name":"Hopper","email":"grace@example.com","lead_source":"Web"}'

# Shopify customers
curl -X POST localhost:8000/shopify/customers \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"Grace","last_name":"Hopper","email":"grace@example.com"}'

# Shopify orders
curl localhost:8000/shopify/orders?page=1&per_page=20
curl localhost:8000/shopify/orders/<order_id>
```

Full endpoint list is in `/docs` (Swagger) once the server is
running.

Errors always carry a typed `error.code` (`not_found`,
`validation_error`, `provider_auth_error`, `provider_api_error`,
`provider_rate_limited`, `provider_timeout`, `unknown_provider`,
`internal_error`) with an appropriate HTTP status — raw Zoho/Shopify
error payloads never reach the caller.

## Extensibility: the demo provider

`app/providers/demo_provider/` is a working third CRM provider with
an in-memory store instead of a real API. It implements
`BaseCRMProvider` exactly like Zoho does, is registered in
`ProviderFactory`, and is exposed at `/demo/contacts` and
`/demo/leads` with the exact same shape as the Zoho routes. Nothing
in `api/`, `db/`, or the Zoho/Shopify code was touched to add it —
that's the concrete proof of the "adding a provider is cheap" claim.

```bash
curl -X POST localhost:8000/demo/contacts \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"Ada","last_name":"Lovelace","email":"ada@example.com"}'
```

## Running tests

```bash
pytest
```

31 tests cover:
- the Template Method's 401-refresh-retry behavior, in isolation
  from any real provider
- the shared HTTP client's retry-with-backoff and rate-limit
  handling
- Zoho OAuth (code exchange, refresh) and Contacts/Leads CRUD,
  fully mocked with `respx` — no live API calls
- Shopify Customers/Orders CRUD and pagination (`Link` header
  parsing), fully mocked
- `ProviderFactory` registration and unknown-provider errors
- API-level tests through `TestClient` (envelope shape, validation
  errors, 404s, full contact/lead lifecycle)

## Docker

```bash
docker compose up --build
```

Serves on `localhost:8000`; the SQLite file persists in a named
volume so token state survives container restarts.

## Design decisions & known limitations

- **Zoho scope**: OAuth is a manual browser round-trip
  (`/zoho/auth/authorize` → approve → `/zoho/auth/callback`), not a
  fully automated flow — appropriate for a single-tenant demo, not
  multi-tenant SaaS.
- **Shopify pagination**: Shopify's REST Admin API uses cursor-based
  (`page_info`) pagination, not page numbers. This service reports
  `has_more` correctly (from the `Link` response header) but the
  `page` field is a passthrough of what was requested, not a real
  cursor — fine for this scope, worth revisiting before adding
  cursor-based "next page" navigation.
  Rate limiting, retries and backoff apply to Shopify calls exactly
  the same way as Zoho, via the shared HTTP client.
- **DB access is synchronous** (SQLAlchemy, not `asyncio`) despite
  the rest of the stack being async. The only DB traffic is small,
  infrequent token reads/writes, so the tradeoff favors simplicity
  over a fully async stack for this scope.
- **Webhooks**: `POST /webhooks/shopify` verifies Shopify's HMAC
  signature (when `SHOPIFY_WEBHOOK_SECRET` is set) and logs the
  event — proof of the surface area, not a full event-processing
  pipeline.
