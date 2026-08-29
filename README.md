# BridgeLayer

Unified integration layer connecting **Zoho CRM** and **Shopify**
through a single, consistent API — organized as one self-contained
module per provider (and one submodule per resource inside it) so a
third provider (HubSpot, WooCommerce, ...) can be added by copying
that folder shape, without touching Zoho/Shopify code. A stub `demo`
provider ships alongside Zoho/Shopify as a live proof of that claim
(see [Extensibility](#extensibility-the-demo-module)).

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
- [Extensibility: the demo module](#extensibility-the-demo-module)
- [Running tests](#running-tests)
- [Docker](#docker)
- [Design decisions & known limitations](#design-decisions--known-limitations)

## Architecture

```
app/
├── main.py               FastAPI app, lifespan, exception handlers, routers
├── core/                  config, logging, shared HTTP client, generic
│                           schemas (envelope/pagination), exceptions
├── db/                    SQLAlchemy engine + session factory only -
│                           no shared table definitions live here
└── modules/
    ├── zoho/
    │   ├── auth/           OAuth2 code exchange + refresh (own ZohoToken table)
    │   ├── client.py        Zoho's own authenticated-request/retry flow
    │   ├── contacts/        models.py + schemas.py + service.py + api.py
    │   └── leads/            (same shape)
    ├── shopify/
    │   ├── auth/            OAuth2 (+ static-token fallback), own ShopifyToken table
    │   ├── client.py
    │   ├── customers/        models.py + schemas.py + service.py + api.py
    │   ├── orders/            (same shape; read-only, mirrored on read)
    │   └── webhooks.py       Shopify webhook receiver
    └── demo/
        ├── contacts/          in-memory stub CRM proving extensibility
        └── leads/
```

Each provider module is **fully self-contained**: its own auth flow
and token table, its own HTTP client with its own retry/refresh
logic, and one folder per resource holding that resource's local DB
table, request/response schemas, business logic, and router. Nothing
is shared between `zoho/` and `shopify/` beyond generic, non-provider
infrastructure in `core/` (settings, the pooled HTTP client, typed
exceptions, the response envelope). Adding a new provider means
copying this folder shape into `modules/<provider>/` and registering
its routers in `main.py` — no other file changes.

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
   stores them in the `zoho_tokens` table.

After that, every Zoho call transparently refreshes the access
token when it's expired or when the API returns a 401 — callers
never see a token.

## Shopify OAuth flow

Same shape as Zoho's flow, but with two extra checks on the callback
that Zoho doesn't need — Shopify requires verifying the redirect
actually came from Shopify:

1. `GET /shopify/auth/authorize` → returns `{ authorization_url }`
   (also generates and remembers a one-time `state` nonce). Open it
   in a browser (or hit `GET /shopify/auth/authorize/redirect`).
2. Approve access. Shopify redirects to `SHOPIFY_REDIRECT_URI` with
   `shop`, `code`, `state`, `timestamp`, and `hmac` query params.
3. That redirect must land on `GET /shopify/auth/callback`, which:
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

Every module owns its own tables — there is no shared, generic
table across providers. Each resource's `models.py` defines real,
typed columns (not a JSON blob), so local data is directly queryable.

| Table | Owned by | Notes |
|---|---|---|
| `zoho_tokens` | `modules/zoho/auth/models.py` | single-row OAuth token; `access_token` never returned in API responses or logged |
| `zoho_contacts` | `modules/zoho/contacts/models.py` | `external_id` (Zoho's ID, unique), name/email/phone/company, `is_deleted` |
| `zoho_leads` | `modules/zoho/leads/models.py` | same shape as contacts + `lead_source` |
| `shopify_tokens` | `modules/shopify/auth/models.py` | single-row OAuth/static token |
| `shopify_customers` | `modules/shopify/customers/models.py` | `external_id` (Shopify's ID, unique), name/email/phone |
| `shopify_orders` | `modules/shopify/orders/models.py` | `external_id`, denormalized customer id/email, price/currency/status |
| `demo_contacts` / `demo_leads` | `modules/demo/*/models.py` | same shape as Zoho's, proving the template replicates for a new provider |

All tables include `created_at`/`updated_at` (UTC). Tables are
created automatically on startup (`init_db()` in the app lifespan,
which imports every module's `models.py` before calling
`Base.metadata.create_all`) — no manual migration step for this
scope.

## Local persistence

Every create/update/delete a module's `service.py` sends to Zoho or
Shopify is also mirrored into that resource's own local table, so
BridgeLayer keeps its own durable copy of what it sent instead of
only trusting the third party's copy of it. This isn't just a
pass-through API call — the local write happens inside the same
service function as the provider call, right after it succeeds:

- **Create** (`create_contact`, `create_lead`, `create_customer`)
  upserts the returned record locally, keyed by the provider's ID
  (`external_id`).
- **Update** (`update_contact`, `update_customer`) overwrites the
  local row with the latest data.
- **Delete** (`delete_contact`) soft-deletes the local row
  (`is_deleted = true`) rather than removing it, so there's still a
  local record of what used to exist even after Zoho no longer has
  it.
- **Orders are read-only** in this API (Shopify is the only place an
  order is created), so `list_orders`/`get_order` upsert the local
  `shopify_orders` row on every read instead — the only touchpoint
  BridgeLayer has with that data.

Each resource's `service.py` (e.g.
`app/modules/zoho/contacts/service.py`) owns this end to end: it
calls the provider via that module's `client.py`, maps the response
to/from its own `schemas.py`, and upserts/soft-deletes its own
`models.py` table directly via SQLAlchemy. There's no shared
persistence helper — a new provider's resource gets the same
guarantee by following the same four-file shape
(`models.py`/`schemas.py`/`service.py`/`api.py`), not by importing
something generic.

Reads (`get_*`, `list_*`, aside from Orders above) still hit the
provider directly — the provider stays the source of truth for
reads, and the local mirror exists to guarantee nothing BridgeLayer
*wrote* is ever silently lost, not to serve as a read cache.

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
`provider_rate_limited`, `provider_timeout`, `internal_error`) with
an appropriate HTTP status — raw Zoho/Shopify error payloads never
reach the caller.

## Extensibility: the demo module

`app/modules/demo/` is a working third provider with an in-memory
store instead of a real API, laid out exactly like `modules/zoho/`:
one folder per resource (`contacts/`, `leads/`), each with its own
`models.py` (local mirror table), `schemas.py`, `service.py`, and
`api.py`, exposed at `/demo/contacts` and `/demo/leads`. The only
difference from Zoho/Shopify is that `service.py` reads/writes an
in-memory dict instead of calling `client.py` — everything else,
including the local-mirror-on-write behavior, is identical. Nothing
in `core/`, `db/`, or the Zoho/Shopify modules was touched to add
it — that's the concrete proof that copying this folder shape is
the entire integration surface for a new provider.

```bash
curl -X POST localhost:8000/demo/contacts \
  -H 'Content-Type: application/json' \
  -d '{"first_name":"Ada","last_name":"Lovelace","email":"ada@example.com"}'
```

## Running tests

```bash
pytest
```

35 tests cover:
- the shared HTTP client's retry-with-backoff and rate-limit
  handling
- Zoho OAuth (code exchange, refresh), fully mocked with `respx` —
  no live API calls
- Zoho Contacts/Leads CRUD, including local-mirror upsert on
  create/update and soft-delete on delete
- Shopify OAuth (authorization URL, shop/state/HMAC verification,
  code exchange), fully mocked
- Shopify Customers CRUD and pagination (`Link` header parsing),
  including local-mirror upsert on create/update
- Shopify Orders list/get, including local-mirror upsert on read
- API-level tests through `TestClient` (envelope shape, validation
  errors, 404s, full demo contact/lead lifecycle)

## Docker

```bash
docker compose up --build
```

Serves on `localhost:8000`; the SQLite file persists in a named
volume so token and local-mirror state survive container restarts.

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
  the same way as Zoho, via the shared HTTP client in `core/`.
- **DB access is synchronous** (SQLAlchemy, not `asyncio`) despite
  the rest of the stack being async. The only DB traffic is small,
  infrequent token/local-mirror reads and writes, so the tradeoff
  favors simplicity over a fully async stack for this scope.
- **Webhooks**: `POST /webhooks/shopify` verifies Shopify's HMAC
  signature (when `SHOPIFY_WEBHOOK_SECRET` is set) and logs the
  event — proof of the surface area, not a full event-processing
  pipeline.
