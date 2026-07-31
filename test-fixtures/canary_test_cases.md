# Sentinel Canary API — Manual Test Cases

Step-by-step scenarios for local development and QA. All management routes use the **owner secret** (`auth_string`) in the URL path.

* **Base URL:** `http://127.0.0.1:8000`
* **Auth guide:** [DOCS/authentication.md](../DOCS/authentication.md)

---

## Before you start

1. Start Redis and the API (`uvicorn main:app --reload`).
2. Run **Test 1** (generate) first and save `Token_ID` and `auth_string` from the response — every fetch/delete case below needs them.

---

## 1. System health check

### Root welcome

* **URL:** `http://127.0.0.1:8000/`
* **Method:** `GET`
* **Auth:** None

**Expected (`200 OK`):**

```json
{
  "message": "welcome to canary token generator API",
  "status": 200
}
```

---

## 2. Token creation

### Generate canary token

* **URL:** `http://127.0.0.1:8000/canary/generate-token`
* **Method:** `POST`
* **Auth:** None
* **Headers:** `Content-Type: application/json`

**Request body (AWS example):**

```json
{
  "token_type": "aws",
  "name": "Production Database Honey Key",
  "alert_email": "security@company.local"
}
```

**Request body (HTTP example — used in dev testing):**

```json
{
  "token_type": "http",
  "name": "Production Passwords File Cleartext AWERD dev http",
  "alert_email": "myEmail@gmail.com"
}
```

**Expected (`201 Created`):**

```json
{
  "message": "your token has been generated successfully",
  "Canary_Token": "http://127.0.0.1:8000/canary/trigger/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "Token_ID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "Token_Name": "Production Passwords File Cleartext AWERD dev http",
  "auth_string": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

**Save for later tests:**

| Field | Use |
|-------|-----|
| `Token_ID` | Trigger URL + fetch/delete path |
| `auth_string` | Fetch and delete path (owner secret) |
| `Canary_Token` | Deploy as decoy only — not used on management routes |

---

## 3. Data retrieval (auth required)

### Fetch token by ID

* **URL:** `http://127.0.0.1:8000/canary/fetch/id/{token_id}/{auth_string}`
* **Method:** `GET`
* **Auth:** Owner `auth_string` in path

**Example:**

```http
GET /canary/fetch/id/a1b2c3d4-e5f6-7890-abcd-ef1234567890/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

**Expected (`200 OK`):**

```json
{
  "token_ID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "token_type": "http",
  "name": "Production Passwords File Cleartext AWERD dev http",
  "alert_email": "myEmail@gmail.com",
  "created_at": "2026-06-13T18:34:37.123456",
  "is_active": true,
  "auth_string": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "CanaryToken": "http://127.0.0.1:8000/canary/trigger/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "ACTIVE",
  "breach_count": 0,
  "logs": []
}
```

### Fetch token by name

* **URL:** `http://127.0.0.1:8000/canary/fetch/name/{name}/{auth_string}`
* **Method:** `GET`
* **Auth:** Owner `auth_string` in path

**Example (URL-encoded name):**

```http
GET /canary/fetch/name/Production%20Database%20Honey%20Key/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

**Expected (`200 OK`):** Same document shape as fetch-by-ID.

### Fetch with wrong auth (negative test)

* **URL:** `http://127.0.0.1:8000/canary/fetch/id/{token_id}/wrong-secret-uuid`
* **Expected (`403 Forbidden`):**

```json
{
  "detail": "Access Denied: Invalid X-API-Key for this token ID."
}
```

---

## 4. Incident interception (no auth)

### Trigger canary tripwire

The honeypot endpoint is **intentionally open** — only `token_id` is required.

* **URL:** `http://127.0.0.1:8000/canary/trigger/{token_id}`
* **Method:** `GET`
* **Auth:** None

**Deceptive response (`200 OK`):**

```json
{
  "status": "panik",
  "code": "SERVER_HAS_LEFT_THE_CHAT",
  "message": "Something went horribly wrong. We blamed the intern, but honestly, it was probably your payload :).",
  "Your_Problem_not_mine": "It worked on my machine. ¯\\_(ツ)_/¯"
}
```

**Side effects:** `status` → `COMPROMISED`, `breach_count` incremented, log entry appended, email queued if `RESEND_API_KEY` is configured.

### Trigger unknown token (negative test)

* **URL:** `http://127.0.0.1:8000/canary/trigger/00000000-0000-0000-0000-000000000000`
* **Expected (`404 Not Found`):**

```json
{
  "detail": "Failed to find redis token"
}
```

---

## 5. Token deletion (auth required)

### Delete by ID

* **URL:** `http://127.0.0.1:8000/canary/delete/id/{token_id}/{auth_string}`
* **Method:** `DELETE`
* **Auth:** Owner `auth_string` in path

**Example:**

```bash
curl -X DELETE "http://127.0.0.1:8000/canary/delete/id/a1b2c3d4-e5f6-7890-abcd-ef1234567890/f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

**Expected (`200 OK`):**

```json
{
  "message": "Token with ID a1b2c3d4-e5f6-7890-abcd-ef1234567890 deleted successfully."
}
```

### Delete by name

* **URL:** `http://127.0.0.1:8000/canary/delete/name/{name}/{auth_string}`
* **Method:** `DELETE`

**Example:**

```bash
curl -X DELETE "http://127.0.0.1:8000/canary/delete/name/Production%20Database%20Honey%20Key/f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

---

## 6. Suggested test order

```text
1. GET  /                              → health
2. POST /canary/generate-token         → save Token_ID + auth_string
3. GET  /canary/fetch/id/{id}/{auth}   → 200
4. GET  /canary/fetch/id/{id}/bad      → 403
5. GET  /canary/trigger/{id}           → 200 deceptive body
6. GET  /canary/fetch/id/{id}/{auth}   → status COMPROMISED, logs populated
7. DELETE /canary/delete/id/{id}/{auth} → 200
8. GET  /canary/fetch/id/{id}/{auth}   → 404
```
