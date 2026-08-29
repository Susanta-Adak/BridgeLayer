# BridgeLayer

Unified integration layer connecting **Zoho CRM** and **Shopify**
through a single, consistent API — organized as one self-contained
module per provider (and one submodule per resource inside it) so a
third provider (HubSpot, WooCommerce, ...) can be added by copying
that folder shape, without touching Zoho/Shopify code.

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
- [Shopify OAuth flow](#shopify-oauth-flow)
- [Database schema](#database-schema)
- [Local persistence](#local-persistence)
- [API usage](#api-usage)
- [Running tests](#running-tests)
- [Docker](#docker)
- [Design decisions & known limitations](#design-decisions--known-limitations)

## Architecture

```
app/
├── main.py               FastAPI app, lifespan, exception handlers;
│                           mounts api/v1 + the unversioned /health
├── api/
│   └── v1/
│       └── router.py      composition root: mounts every module's router
│                           under /api/v1 (see "API versioning" below).
│                           A future v2 is a sibling api/v2/ package.
├── core/                  config, logging, shared HTTP client, generic
│                           schemas (envelope/pagination), exceptions
├── db/                    SQLAlchemy engine + session factory - stores
│                           OAuth tokens only, see "Local persistence"
└── modules/
    ├── zoho/
    │   ├── auth/           OAuth2 code exchange + refresh (own ZohoToken table)
    │   ├── client.py        Zoho's own authenticated-request/retry flow
    │   ├── contacts/        schemas.py + service.py + router.py
    │   └── leads/            (same shape)
    └── shopify/
        ├── auth/            OAuth2 (+ static-token fallback), own ShopifyToken table
        ├── client.py
        ├── customers/        schemas.py + service.py + router.py
        ├── orders/            (same shape; read-only)
        └── webhooks.py       Shopify webhook receiver
```

Each provider module is **fully self-contained**: its own auth flow
and token table, its own HTTP client with its own retry/refresh
logic, and one folder per resource holding that resource's
request/response schemas, business logic, and router. Nothing is
shared between `zoho/` and `shopify/` beyond generic, non-provider
infrastructure in `core/` (settings, the pooled HTTP client, typed
exceptions, the response envelope). Adding a new provider means
copying this folder shape into `modules/<provider>/` and registering
its routers in `app/api/v1/router.py` — no other file changes.

Resource folders (`contacts/`, `leads/`, `customers/`, `orders/`)
deliberately have **no `models.py`** — Zoho and Shopify are the
source of truth for that data, so there's nothing local to define a
table for. Only `auth/` has a `models.py`, for the OAuth token. See
[Local persistence](#local-persistence).

### API versioning

Every business/auth endpoint is mounted under `/api/v1` (e.g.
`/api/v1/zoho/contacts`, `/api/v1/shopify/auth/authorize`). This
lives in one place, `app/api/v1/router.py`, which imports each
module's `router` unchanged and mounts it under an
`APIRouter(prefix="/api/v1")` — no module's own `router.py` knows or
cares that it's versioned. `app/api/` is a package for exactly this
reason: adding v2 later means adding a sibling `app/api/v2/router.py`
that composes whichever module routers changed (old ones can still
be reused unchanged, unmodified) and mounting both in `main.py` —
`v1/` itself is never touched.

If a specific resource's contract diverges in v2 (e.g. renamed
response fields), its v2-only `schemas.py`/`router.py` live in a
`v2/` subfolder inside that resource's own folder (e.g.
`modules/zoho/contacts/v2/`) — its `service.py`/`client.py`/`auth/`
stay shared and unversioned. See `CLAUDE.md` Section 9 for the full
convention and a worked example. None of this exists yet — it's
documented so the "where do I put it" question has one answer when
it's actually needed.

`GET /health` is intentionally **not** versioned — it's an
infra-level liveness check for load balancers/orchestrators, not a
business-data endpoint, so it stays at a stable path regardless of
API version. `/docs`, `/redoc`, and `/openapi.json` are FastAPI's own
unversioned, auto-generated routes.

See `CLAUDE.md` in the repo root for the full architecture rationale.

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
| `SHOPIFY_CLIENT_ID` / `SHOPIFY_CLIENT_SECRET` | Preferred: from a Shopify app's Client credentials (Partner Dashboard) |
| `SHOPIFY_REDIRECT_URI` | Must match the redirect URI registered on the Shopify app |
| `SHOPIFY_ACCESS_TOKEN` | Fallback: a custom/private app's static Admin API access token, used only if no OAuth token has been stored yet |
| `SHOPIFY_WEBHOOK_SECRET` | Optional; enables HMAC verification on `/api/v1/webhooks/shopify` |

## Zoho OAuth flow

Zoho contacts/leads require a one-time authorization before any
CRM call will work:

1. `GET /api/v1/zoho/auth/authorize` → returns `{ authorization_url }`.
   Open it in a browser.
2. Approve access. Zoho redirects to `ZOHO_REDIRECT_URI` with a
   `code` query param.
3. That redirect must land on `GET /api/v1/zoho/auth/callback?code=...`,
   which exchanges the code for an access + refresh token and
   stores them in the `zoho_tokens` table.

After that, every Zoho call transparently refreshes the access
token when it's expired or when the API returns a 401 — callers
never see a token.

## Shopify OAuth flow

Same shape as Zoho's flow, but with two extra checks on the callback
that Zoho doesn't need — Shopify requires verifying the redirect
actually came from Shopify:

1. `GET /api/v1/shopify/auth/authorize` → returns `{ authorization_url }`
   (also generates and remembers a one-time `state` nonce). Open it
   in a browser.
2. Approve access. Shopify redirects to `SHOPIFY_REDIRECT_URI` with
   `shop`, `code`, `state`, `timestamp`, and `hmac` query params.
3. That redirect must land on `GET /api/v1/shopify/auth/callback`, which:
   - confirms `shop` matches the configured `SHOPIFY_SHOP_DOMAIN`,
   - confirms `state` matches a nonce this app actually issued
     (single-use, defends against CSRF),
   - recomputes the HMAC over the query string using
     `SHOPIFY_CLIENT_SECRET` and compares it to the `hmac` param
     (confirms Shopify signed the redirect),
   - then exchanges `code` for a permanent offline access token and
     stores it in the `shopify_tokens` table.

Shopify's offline access token doesn't expire, so there's no
refresh cycle to manage. If no OAuth token has been stored yet, the
provider falls back to a static `SHOPIFY_ACCESS_TOKEN` (custom/
private app token) so existing non-OAuth setups keep working.

## Database schema

Two tables, one per provider, both owned by that provider's `auth/`
submodule:

| Table | Owned by | Notes |
|---|---|---|
| `zoho_tokens` | `modules/zoho/auth/models.py` | single-row OAuth access + refresh token; `access_token` never returned in API responses or logged |
| `shopify_tokens` | `modules/shopify/auth/models.py` | single-row OAuth (or static-token-derived) access token |

That's the entire schema — see [Local persistence](#local-persistence)
for why there's nothing else. Both tables include
`created_at`/`updated_at` (UTC). Tables are created automatically on
startup (`init_db()` in the app lifespan, which imports each
provider's `auth/models.py` before calling
`Base.metadata.create_all`) — no manual migration step for this scope.

## Local persistence

**Zoho and Shopify are the source of truth for all business data**
(contacts, leads, customers, orders). BridgeLayer does not keep a
local copy, cache, or mirror of that data — every `create`/`get`/
`list`/`update`/`delete` call goes straight to the provider, and the
response returned to the caller is exactly what the provider just
said, mapped into this API's schema. There is no `models.py` in any
`contacts/`/`leads/`/`customers/`/`orders/` folder.

The local SQLite database exists for exactly one thing: **OAuth
tokens** (`zoho_tokens`, `shopify_tokens` above), which is the
minimal integration state actually needed to avoid re-authorizing on
every restart.

This is a deliberate choice, not an oversight:
- **Avoids staleness/sync bugs.** A cached copy of Zoho/Shopify data
  can drift from reality (edited directly in Zoho's UI, a webhook
  missed, a delete that didn't propagate). Not caching means there's
  nothing that can ever be stale — every response reflects the
  provider's current state at request time.
- **Matches the assignment's scope.** The brief asks for a unified
  API on top of Zoho/Shopify with token/session handling, not a
  data-sync or offline-cache platform. A full local mirror is scope
  creep for that goal and adds real failure modes (partial writes,
  drift, migration churn) for no requirement it serves.
- **Keeps auth and business logic separate.** Only `auth/service.py`
  touches the database in each provider module (via `SessionLocal`);
  `contacts/service.py`, `leads/service.py`, `customers/service.py`,
  and `orders/service.py` never import `app.db` at all - they only
  call their module's `client.py` and map the JSON response. That
  separation is easy to verify by grep: `SessionLocal` only appears
  under `modules/*/auth/`.

If a future requirement needs offline reads, analytics, or resilience
to provider downtime, the right tool is a deliberate caching layer
added on top of this - not folding persistence into every resource's
write path by default.

## API usage

All endpoints return the envelope shown above. Examples:

```bash
# Zoho contacts
curl -X POST localhost:8000/api/v1/zoho/contacts \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"Ada","last_name":"Lovelace","email":"ada@example.com"}'

curl localhost:8000/api/v1/zoho/contacts?page=1&per_page=20

# Zoho leads
curl -X POST localhost:8000/api/v1/zoho/leads \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"Grace","last_name":"Hopper","email":"grace@example.com","lead_source":"Web"}'

# Shopify customers
curl -X POST localhost:8000/api/v1/shopify/customers \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"Grace","last_name":"Hopper","email":"grace@example.com"}'

# Shopify orders
curl localhost:8000/api/v1/shopify/orders?page=1&per_page=20
curl localhost:8000/api/v1/shopify/orders/<order_id>
```

Full endpoint list is in `/docs` (Swagger) once the server is
running.

Errors always carry a typed `error.code` (`not_found`,
`validation_error`, `provider_auth_error`, `provider_api_error`,
`provider_rate_limited`, `provider_timeout`, `internal_error`) with
an appropriate HTTP status — raw Zoho/Shopify error payloads never
reach the caller.

## Running tests

```bash
pytest
```

34 tests cover:
- the shared HTTP client's retry-with-backoff and rate-limit
  handling
- Zoho OAuth (code exchange, refresh), fully mocked with `respx` —
  no live API calls
- Zoho Contacts/Leads CRUD and request/response mapping
- Shopify OAuth (authorization URL, shop/state/HMAC verification,
  code exchange), fully mocked
- Shopify Customers CRUD and pagination (`Link` header parsing)
- Shopify Orders list/get and nested-customer mapping
- API-level tests through `TestClient` (envelope shape, validation
  errors, 404s, a full Zoho contact lifecycle routed through the
  actual HTTP endpoints)

## Docker

```bash
docker compose up --build
```

Serves on `localhost:8000`; the SQLite file persists in a named
volume so OAuth token state survives container restarts.

## Design decisions & known limitations

- **No shared provider abstraction on purpose**: earlier iterations
  of this codebase used a shared `BaseCRMProvider`/`ProviderFactory`
  (Strategy + Factory Method) so every provider's HTTP/retry/refresh
  flow ran through one Template Method. This version deliberately
  drops that in favor of each provider module being fully
  standalone — simpler to read and reason about in isolation, at the
  cost of `client.py`'s retry/refresh flow being duplicated (not
  shared) between `modules/zoho/` and `modules/shopify/`.
- **Zoho scope**: OAuth is a manual browser round-trip
  (`/api/v1/zoho/auth/authorize` → approve →
  `/api/v1/zoho/auth/callback`), not a fully automated flow —
  appropriate for a single-tenant demo, not multi-tenant SaaS.
- **Shopify pagination**: Shopify's REST Admin API uses cursor-based
  (`page_info`) pagination, not page numbers. This service reports
  `has_more` correctly (from the `Link` response header) but the
  `page` field is a passthrough of what was requested, not a real
  cursor — fine for this scope, worth revisiting before adding
  cursor-based "next page" navigation.
  Rate limiting, retries and backoff apply to Shopify calls exactly
  the same way as Zoho, via the shared HTTP client in `core/`.
- **DB access is synchronous** (SQLAlchemy, not `asyncio`) despite
  the rest of the stack being async. The only DB traffic is small,
  infrequent OAuth token reads and writes, so the tradeoff favors
  simplicity over a fully async stack for this scope.
- **Webhooks**: `POST /api/v1/webhooks/shopify` verifies Shopify's
  HMAC signature (when `SHOPIFY_WEBHOOK_SECRET` is set) and logs the
  event — proof of the surface area, not a full event-processing
  pipeline.
