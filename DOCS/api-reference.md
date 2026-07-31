# Sentinel API — API Reference

Base URL (local default): `http://127.0.0.1:8000`

Most canary routes share the prefix `/canary`. **All endpoints** listed below are rate-limited via the shared `ratelimiter` dependency.

> **New to auth?** Read [authentication.md](./authentication.md) for the difference between `auth_string` (owner secret) and `Canary_Token` (deployable decoy).

Interactive OpenAPI UI: `/docs` (FastAPI auto-generated)  
Custom docs pointer: `/canary/docs` (links to Git repository)

---

## Summary Table

| Method | Path | Status (success) | Auth | Lifecycle role |
|--------|------|------------------|------|----------------|
| `GET` | `/` | 200 | No | API health / welcome |
| `GET` | `/canary/docs` | 200 | No | Project documentation pointer |
| `POST` | `/canary/generate-token` | 201 | No | **Provision** a new honeypot token |
| `GET` | `/canary/fetch/id/{token_id}/{auth_string}` | 200 | Owner secret | **Inspect** token by UUID |
| `GET` | `/canary/fetch/name/{name}/{auth_string}` | 200 | Owner secret | **Inspect** token by name |
| `GET` | `/canary/trigger/{token_id}` | 200 | No (honeypot) | **Intercept** unauthorized access |
| `DELETE` | `/canary/delete/id/{token_id}/{auth_string}` | 200 | Owner secret | **Retire** token by UUID |
| `DELETE` | `/canary/delete/name/{name}/{auth_string}` | 200 | Owner secret | **Retire** token by name |

---

## Authentication

Fetch and delete routes require the per-token **owner secret** (`auth_string`) as a URL path segment. This value is returned once in the `POST /canary/generate-token` response. Store it securely — it cannot be recovered without already having access to the token record.

| Condition | Status | Detail |
|-----------|--------|--------|
| Token not found | `404` | Varies by route (see below) |
| Wrong `auth_string` | `403` | `Access Denied: Invalid X-API-Key for this token ID.` (or `...token name.`) |

Generation and trigger routes have **no authentication**.

---

## Root Endpoints

### `GET /`

**Lifecycle role:** Confirms the API process is running.

**Request body:** None

**Content negotiation:** If the `Accept` header contains `text/html`, a styled HTML welcome page is returned. Otherwise JSON is returned.

**Success response (200) — JSON:**

```json
{
  "message": "welcome to canary token generator API",
  "status": 200
}
```

---

### `GET /canary/docs`

**Lifecycle role:** Returns a pointer to the project Git repository (not the OpenAPI spec).

**Request body:** None

**Content negotiation:** HTML page when `Accept: text/html`; JSON otherwise.

**Success response (200) — JSON:**

```json
{
  "message": "Docs endpoint reached",
  "GitRepo": "https://github.com/AWERDdev/sentinel-api"
}
```

> FastAPI's built-in interactive OpenAPI UI is at `/docs`, separate from this custom route.

---

## Token Generation

### `POST /canary/generate-token`

**Lifecycle role:** Creates a new canary token, persists it in Redis, and returns the decoy payload plus the owner secret.

#### Request

**Headers:**

```http
Content-Type: application/json
```

**Body schema (`CanaryTokenCreate`):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `token_type` | string | Yes | One of: `http`, `https`, `aws`, `web`, `url` (case-insensitive; trimmed). `web` and `url` generate HTTP tripwire URLs like `http`/`https`. |
| `name` | string | Yes | Human-readable identifier; used for secondary Redis index |
| `alert_email` | string (email) | Yes | Email address for breach notifications |

**Example — HTTP tripwire:**

```json
{
  "token_type": "http",
  "name": "Production Passwords File",
  "alert_email": "security@company.local"
}
```

**Example — AWS credential honeypot:**

```json
{
  "token_type": "aws",
  "name": "Production Database Honey Key",
  "alert_email": "security@company.local"
}
```

#### Success response (201 Created)

```json
{
  "message": "your token has been generated successfully",
  "Canary_Token": "http://127.0.0.1:8000/canary/trigger/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "Token_ID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "Token_Name": "Production Passwords File",
  "auth_string": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

| Response field | Meaning |
|----------------|---------|
| `Canary_Token` | **Deploy this** — the decoy URL or credential block to embed in your environment |
| `Token_ID` | UUID used in trigger URLs and management routes |
| `auth_string` | **Save this** — owner secret required for fetch and delete routes |

For `token_type: "aws"`, `Canary_Token` is a multi-line fake credential block:

```json
{
  "message": "your token has been generated successfully",
  "Canary_Token": "aws_access_key_id=AKIA_A1B2C3D4E5F6789\naws_secret_access_key=fake_secret_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "Token_ID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "Token_Name": "Production Database Honey Key",
  "auth_string": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

#### Error responses

| Status | Condition | Body |
|--------|-----------|------|
| `400` | Invalid `token_type` | `{"detail": "Invalid token type. Choose from: http, https, aws, web, url"}` |
| `422` | Missing/invalid JSON fields | Pydantic validation error detail |
| `429` | Rate limit exceeded | `{"detail": "Too many requests. Please try again later."}` |

#### Redis side effects

- `SET canary:token:{token_id}` → full `CanaryToken` JSON
- `SET canary:name:{normalized_name}` → `token_id`

---

## Token Retrieval

### `GET /canary/fetch/id/{token_id}/{auth_string}`

**Lifecycle role:** Allows operators to audit a token's current state, including breach history after a trigger.

**Path parameters:**

| Parameter | Description |
|-----------|-------------|
| `token_id` | UUID assigned at generation time |
| `auth_string` | Owner secret returned at generation time |

**Request body:** None

**Example:**

```http
GET /canary/fetch/id/a1b2c3d4-e5f6-7890-abcd-ef1234567890/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

**Success response (200):**

```json
{
  "token_ID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "token_type": "http",
  "name": "Production Passwords File",
  "alert_email": "security@company.local",
  "created_at": "2026-06-13T18:34:37.123456",
  "is_active": true,
  "auth_string": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "CanaryToken": "http://127.0.0.1:8000/canary/trigger/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "ACTIVE",
  "breach_count": 0,
  "logs": []
}
```

After a trigger, `status` becomes `COMPROMISED`, `breach_count` increments, and `logs` contains attacker metadata.

**Error responses:**

| Status | Condition | Body |
|--------|-----------|------|
| `403` | Wrong `auth_string` | `{"detail": "Access Denied: Invalid X-API-Key for this token ID."}` |
| `404` | Token not found | `{"detail": "Cannary token not found"}` |
| `429` | Rate limit exceeded | `{"detail": "Too many requests. Please try again later."}` |

---

### `GET /canary/fetch/name/{name}/{auth_string}`

**Lifecycle role:** Resolves a token by its `name` field using the Redis name index, then returns the full token document.

**Path parameters:**

| Parameter | Description |
|-----------|-------------|
| `name` | Token name as provided at creation (URL-encode spaces) |
| `auth_string` | Owner secret returned at generation time |

**Example:**

```http
GET /canary/fetch/name/Production%20Database%20Honey%20Key/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

**Success response (200):** Same structure as fetch-by-ID.

**Error responses:**

| Status | Condition | Body |
|--------|-----------|------|
| `403` | Wrong `auth_string` | `{"detail": "Access Denied: Invalid X-API-Key for this token name."}` |
| `404` | Name index missing | `{"detail": "Canary token name not found."}` |
| `404` | Index exists but token payload missing | `{"detail": "Canary token payload data missing."}` |
| `429` | Rate limit exceeded | `{"detail": "Too many requests. Please try again later."}` |

---

## Trigger Interception (Honeypot)

### `GET /canary/trigger/{token_id}`

**Lifecycle role:** The tripwire endpoint. Invoked when someone accesses an embedded URL or otherwise hits the tracking link. Records attacker fingerprints, marks the token compromised, queues an email alert, and returns a **deceptive** success response.

**Authentication:** None — must remain open for the honeypot to function.

**Path parameters:**

| Parameter | Description |
|-----------|-------------|
| `token_id` | UUID from the generated tripwire URL or credential mapping |

**Request body:** None

**Headers read (for attribution):**

- `X-Forwarded-For` — first IP in the chain used if present
- `User-Agent` — stored in breach log; defaults to `"Unknown"` if absent

#### Success response — deceptive (200 OK)

When the token exists, the handler returns HTTP `200` with a body that **looks like a server meltdown**:

```json
{
  "status": "panik",
  "code": "SERVER_HAS_LEFT_THE_CHAT",
  "message": "Something went horribly wrong. We blamed the intern, but honestly, it was probably your payload :).",
  "Your_Problem_not_mine": "It worked on my machine. ¯\\_(ツ)_/¯"
}
```

This is intentional honeypot behavior: attackers and scanners see a plausible failure rather than a "token triggered" confirmation.

#### Error responses

| Status | Condition | Body |
|--------|-----------|------|
| `404` | Token not in Redis | `{"detail": "Failed to find redis token"}` |
| `500` | Unhandled exception during processing | `{"detail": "failed to trigger canary token"}` |
| `429` | Rate limit exceeded | `{"detail": "Too many requests. Please try again later."}` |

#### Side effects (on successful processing)

1. `status` → `"COMPROMISED"`
2. `breach_count` incremented by 1
3. New log entry: `{ "ip", "user_agent", "timestamp" }`
4. Updated document written to `canary:token:{token_id}`
5. `send_security_alert` queued via `BackgroundTasks` (if `alert_email` is present)

#### Email alert (background)

- **From:** `CanaryBox <onboarding@resend.dev>` (Resend sandbox default)
- **Subject:** `🚨 BREACH DETECTED: {token_name}`
- **Contains:** token name, attacker IP, user agent, UTC timestamp

---

## Token Deletion

### `DELETE /canary/delete/id/{token_id}/{auth_string}`

**Lifecycle role:** Permanently removes a canary token and its name index from Redis.

**Path parameters:**

| Parameter | Description |
|-----------|-------------|
| `token_id` | UUID of the token to delete |
| `auth_string` | Owner secret returned at generation time |

**Request body:** None

**Success response (200):**

```json
{
  "message": "Token with ID a1b2c3d4-e5f6-7890-abcd-ef1234567890 deleted successfully."
}
```

**Error responses:**

| Status | Condition | Body |
|--------|-----------|------|
| `403` | Wrong `auth_string` | `{"detail": "Access Denied: Invalid X-API-Key for this token ID."}` |
| `404` | Token not found | `{"detail": "Cannary token not found"}` |
| `500` | Unexpected error during delete | `{"detail": "Internal server error occurred during deletion"}` |
| `429` | Rate limit exceeded | `{"detail": "Too many requests. Please try again later."}` |

**Redis side effects:** Deletes `canary:token:{token_id}` and `canary:name:{normalized_name}`.

---

### `DELETE /canary/delete/name/{name}/{auth_string}`

**Lifecycle role:** Deletes a token by resolving the name index first, then removing both Redis keys.

**Path parameters:**

| Parameter | Description |
|-----------|-------------|
| `name` | Human-readable name assigned at creation |
| `auth_string` | Owner secret returned at generation time |

**Request body:** None

**Success response (200):**

```json
{
  "message": "Token 'Production Database Honey Key' deleted successfully."
}
```

**Error responses:**

| Status | Condition | Body |
|--------|-----------|------|
| `403` | Wrong `auth_string` | `{"detail": "Access Denied: Invalid X-API-Key for this token name."}` |
| `404` | Name index not found | `{"detail": "Canary token name not found."}` |
| `404` | Index exists but payload missing | `{"detail": "Canary token payload data missing."}` |
| `500` | Unexpected error during delete | `{"detail": "Internal server error occurred during deletion"}` |
| `429` | Rate limit exceeded | `{"detail": "Too many requests. Please try again later."}` |

---

## Stored Token Schema (`CanaryToken`)

Documents persisted in Redis follow this shape:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `token_ID` | string | — | UUID primary identifier |
| `token_type` | string | — | `http`, `https`, `aws`, `web`, or `url` |
| `name` | string | — | Operator-defined label |
| `alert_email` | string (email) | — | Breach notification recipient |
| `created_at` | datetime (ISO) | UTC now | Creation timestamp |
| `is_active` | boolean | `true` | Active flag |
| `auth_string` | string \| null | `null` | **Owner secret** for fetch/delete auth |
| `CanaryToken` | string | — | **Deployable decoy** (tripwire URL or fake AWS block) |
| `status` | string | `"ACTIVE"` | Becomes `"COMPROMISED"` after trigger |
| `breach_count` | integer | `0` | Number of trigger events |
| `logs` | array | `[]` | Breach log entries (`ip`, `user_agent`, `timestamp`) |

---

## Rate Limiting (All Endpoints)

When exceeded:

**Status:** `429 Too Many Requests`

```json
{
  "detail": "Too many requests. Please try again later."
}
```

Defaults: **5 requests per 60 seconds** per client IP (configurable via `REDIS_MAX_REQUESTS` and `REDIS_WINDOW_SECONDS`).

Client IP is derived from `X-Forwarded-For` (first hop) when present, otherwise `request.client.host`.

---

## Typical Operator Workflow

```text
1. POST /canary/generate-token
      → save Token_ID, auth_string, and deploy Canary_Token decoy
2. Embed Canary_Token in environment (outside the API)
3. (Attacker) GET /canary/trigger/{token_id}
      → breach logged, email sent, deceptive response returned
4. GET /canary/fetch/id/{token_id}/{auth_string}
      → review logs and status
5. DELETE /canary/delete/id/{token_id}/{auth_string}
      → cleanup when no longer needed
```
