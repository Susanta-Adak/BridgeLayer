# BridgeLayer

Unified integration layer connecting **Zoho CRM** and **Shopify**
through a single, consistent API. Each provider is a self-contained
module (own auth, own HTTP client, one folder per resource) — adding
a third provider means copying that shape, not editing existing code.

Every response uses the same envelope:

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
├── main.py            FastAPI app, lifespan, mounts api/v1 + unversioned /health
├── api/v1/router.py    composition root: mounts every module's router under /api/v1
├── core/               config, logging, HTTP client, generic schemas, exceptions
├── db/                 SQLAlchemy engine + session factory (OAuth tokens only)
└── modules/
    ├── zoho/
    │   ├── auth/         OAuth2 authorize/callback, own token table
    │   ├── client.py      authenticated request + retry/refresh
    │   ├── contacts/
    │   └── leads/
    └── shopify/
        ├── auth/          OAuth2 (+ static-token fallback), own token table
        ├── client.py
        ├── customers/
        ├── orders/         read-only
        └── webhooks.py
```

Every resource folder (`contacts/`, `leads/`, `customers/`,
`orders/`) has the same three files — `schemas.py` (request/response
models), `service.py` (calls the provider, maps the response),
`router.py` (FastAPI routes) — and no `models.py`: the provider is
the source of truth, so there's nothing local to cache. `core/` and
`db/` hold only generic infrastructure; nothing provider-specific
lives there.

Business/auth endpoints are mounted under `/api/v1` by
`app/api/v1/router.py`. Each module's own `router.py` keeps a plain,
unversioned relative prefix (e.g. `/zoho/contacts`) and doesn't know
it's versioned — a future v2 is a sibling `app/api/v2/router.py`
reusing whichever module routers didn't change. `GET /health` (plus
FastAPI's own `/docs`, `/redoc`, `/openapi.json`) stays unversioned.
See `CLAUDE.md` Section 9 for the full versioning convention,
including where a diverging resource's v2-only files would live.

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
| `SHOPIFY_CLIENT_ID` / `SHOPIFY_CLIENT_SECRET` | From a Shopify app's Client credentials (Partner Dashboard) |
| `SHOPIFY_REDIRECT_URI` | Must match the redirect URI registered on the Shopify app |
| `SHOPIFY_ACCESS_TOKEN` | Fallback: a custom/private app's static Admin API token, used only if no OAuth token has been stored yet |
| `SHOPIFY_WEBHOOK_SECRET` | Optional; enables HMAC verification on `/api/v1/webhooks/shopify` |

## Zoho OAuth flow

1. `GET /api/v1/zoho/auth/authorize` → returns `{ authorization_url }`.
   Open it in a browser.
2. Approve access. Zoho redirects to `ZOHO_REDIRECT_URI` with a
   `code` query param.
3. That redirect must land on `GET /api/v1/zoho/auth/callback?code=...`,
   which exchanges the code for an access + refresh token and
   stores them in `zoho_tokens`.

Every later Zoho call transparently refreshes the access token when
it's expired or the API returns a 401 — callers never see a token.

## Shopify OAuth flow

1. `GET /api/v1/shopify/auth/authorize` → returns `{ authorization_url }`
   and remembers a one-time `state` nonce. Open it in a browser.
2. Approve access. Shopify redirects to `SHOPIFY_REDIRECT_URI` with
   `shop`, `code`, `state`, `timestamp`, and `hmac` query params.
3. `GET /api/v1/shopify/auth/callback` confirms `shop` matches
   `SHOPIFY_SHOP_DOMAIN`, consumes the `state` nonce (defends against
   CSRF), recomputes the HMAC over the query string with
   `SHOPIFY_CLIENT_SECRET` to confirm Shopify signed the redirect,
   then exchanges `code` for a permanent offline token stored in
   `shopify_tokens`.

The offline token doesn't expire, so there's no refresh cycle. If no
OAuth token has been stored yet, the app falls back to a static
`SHOPIFY_ACCESS_TOKEN` so non-OAuth setups keep working.

## Database schema

Two tables, one per provider, each owned by that provider's `auth/`
submodule:

| Table | Owned by | Notes |
|---|---|---|
| `zoho_tokens` | `modules/zoho/auth/models.py` | single-row access + refresh token; never returned in responses or logged |
| `shopify_tokens` | `modules/shopify/auth/models.py` | single-row access token (OAuth or static-fallback) |

That's the entire schema — see [Local persistence](#local-persistence)
for why. Both tables include `created_at`/`updated_at` (UTC) and are
created automatically on startup (`init_db()`); no manual migration
step for this scope.

## Local persistence

**Zoho and Shopify are the source of truth for all business data.**
BridgeLayer never caches or mirrors contacts, leads, customers, or
orders — every request goes straight to the provider, and the
response is exactly what the provider just said, mapped into this
API's schema. The database exists for one thing: OAuth tokens, the
minimal state needed to avoid re-authorizing on every restart.

Why not cache: a local copy can silently drift from reality (edited
in the provider's UI, a missed webhook, a delete that didn't
propagate), and this assignment calls for a unified API with
token/session handling, not a sync platform. It also keeps auth and
business logic cleanly separated — only each provider's
`auth/service.py` touches the database; every resource's
`service.py` only calls its module's `client.py`. If a real need for
offline reads or resilience to provider downtime shows up later, add
a deliberate caching layer on top rather than folding persistence
into every write path.

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
an appropriate HTTP status — raw provider error payloads never reach
the caller.

## Running tests

```bash
pytest
```

34 tests cover the shared HTTP client's retry/rate-limit handling,
Zoho and Shopify OAuth (code exchange, refresh, HMAC/state
verification — all `respx`-mocked, no live calls), CRUD and
pagination mapping for every resource, and API-level tests through
`TestClient` (envelope shape, validation errors, 404s, a full
contact lifecycle routed through real HTTP endpoints).

## Docker

```bash
docker compose up --build
```

Serves on `localhost:8000`; the SQLite file persists in a named
volume so OAuth tokens survive container restarts.

## Design decisions & known limitations

- **No shared provider abstraction on purpose.** Earlier iterations
  used a shared base provider class and factory so every provider's
  retry/refresh flow ran through one Template Method. This version
  drops that in favor of each module being fully standalone —
  simpler in isolation, at the cost of `client.py`'s retry/refresh
  logic being duplicated between providers rather than shared.
- **OAuth is a manual browser round-trip** (`authorize` → approve →
  `callback`), not a fully automated flow — appropriate for a
  single-tenant demo, not multi-tenant SaaS.
- **Shopify pagination is cursor-based**, not page-numbered. `has_more`
  is accurate (from the `Link` header), but the `page` field is a
  passthrough of what was requested, not a real cursor — worth
  revisiting before adding cursor-based navigation. Retries and
  backoff apply to Shopify the same way as Zoho, via the shared HTTP
  client in `core/`.
- **DB access is synchronous** despite the rest of the stack being
  async. Traffic is small and infrequent (OAuth tokens only), so the
  tradeoff favors simplicity over a fully async stack.
- **Webhooks are proof of surface area, not a pipeline.**
  `POST /api/v1/webhooks/shopify` verifies Shopify's HMAC signature
  (when `SHOPIFY_WEBHOOK_SECRET` is set) and logs the event — no
  subscription or queueing.
