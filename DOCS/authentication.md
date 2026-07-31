# Sentinel API — Authentication

This document explains how access control works in Sentinel API (CanaryBox). The design uses **per-token owner secrets**, not global API keys or JWT sessions.

For endpoint paths and response shapes, see [api-reference.md](./api-reference.md).

---

## Two different secrets (do not confuse them)

Every canary token has two unrelated values. Mixing them up is the most common integration mistake.

| Name | When you get it | What it is | Where it goes |
|------|-----------------|------------|---------------|
| **`auth_string`** | Returned once in `POST /canary/generate-token` | Owner secret (UUID). Proves you may **manage** this token. | Path segment on fetch and delete routes |
| **`Canary_Token`** (response) / **`CanaryToken`** (Redis) | Same generation response | **Deployable decoy** — tripwire URL or fake AWS credentials | Embed in `.env`, repos, configs — **not** used on management routes |

```text
Generation response
├── Canary_Token   → deploy in the wild (attackers may find this)
├── Token_ID       → used in trigger URL and management paths
└── auth_string    → save securely; never embed in the decoy
```

**Example generation response:**

```json
{
  "message": "your token has been generated successfully",
  "Canary_Token": "http://127.0.0.1:8000/canary/trigger/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "Token_ID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "Token_Name": "Production Passwords File",
  "auth_string": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

- Deploy `Canary_Token` where you want the tripwire.
- Store `auth_string` in your password manager or secrets store for later fetch/delete calls.

---

## Which routes require auth?

| Route | Auth required? | Why |
|-------|----------------|-----|
| `GET /` | No | Public health check |
| `GET /canary/docs` | No | Public docs pointer |
| `POST /canary/generate-token` | No | Anyone can create tokens (see limitations) |
| `GET /canary/trigger/{token_id}` | **No** | Honeypot must stay open so attackers can trip it |
| `GET /canary/fetch/id/{token_id}/{auth_string}` | **Yes** | Operator-only inspection |
| `GET /canary/fetch/name/{name}/{auth_string}` | **Yes** | Operator-only inspection |
| `DELETE /canary/delete/id/{token_id}/{auth_string}` | **Yes** | Operator-only retirement |
| `DELETE /canary/delete/name/{name}/{auth_string}` | **Yes** | Operator-only retirement |

---

## How verification works

Management routes call `utils/canary_verify.py`:

1. Load the token from Redis (`canary:token:{token_id}` or resolve name → id).
2. Read the stored `auth_string` field from the document.
3. Compare it to the `auth_string` path parameter.
4. If they match → return token data (fetch) or proceed with delete.
5. If they do not match → `403 Forbidden`.

```text
Client                          API                         Redis
  │                              │                            │
  │  GET /fetch/id/{id}/{secret} │                            │
  ├─────────────────────────────►│  GET canary:token:{id}     │
  │                              ├───────────────────────────►│
  │                              │◄───────────────────────────┤
  │                              │  secret == stored auth?    │
  │◄─────────────────────────────┤  200 + body  or  403       │
```

There is no `Authorization` header and no session cookie. The secret is part of the URL path.

---

## Example requests

Replace placeholders with values from your generation response.

### Fetch by ID

```bash
curl "http://127.0.0.1:8000/canary/fetch/id/a1b2c3d4-e5f6-7890-abcd-ef1234567890/f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

### Fetch by name

URL-encode spaces in the name:

```bash
curl "http://127.0.0.1:8000/canary/fetch/name/Production%20Passwords%20File/f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

### Delete by ID

```bash
curl -X DELETE "http://127.0.0.1:8000/canary/delete/id/a1b2c3d4-e5f6-7890-abcd-ef1234567890/f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

### Trigger (no auth — honeypot)

```bash
curl "http://127.0.0.1:8000/canary/trigger/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

Only `token_id` is needed. The owner `auth_string` is **not** used on the trigger route.

---

## Error responses

| Status | When | Example `detail` |
|--------|------|------------------|
| `403` | Wrong `auth_string` on fetch/delete | `Access Denied: Invalid X-API-Key for this token ID.` |
| `404` | Token or name not found | `Cannary token not found` / `Canary token name not found.` |

A `403` means the token exists but the secret is wrong. A `404` means the token id or name could not be resolved.

---

## Security notes

**Save `auth_string` at generation time.** It is returned in the `201 Created` body only. There is no recovery endpoint if you lose it (you would need direct Redis access).

**Path secrets and logs.** Because `auth_string` is in the URL, it may appear in:

- Web server access logs
- Browser history
- Proxy logs

For local development and testing this is acceptable. For production hardening, a future improvement would move the secret to an `Authorization` header or `X-API-Key` header.

**Open token generation.** `POST /canary/generate-token` has no auth. Untrusted networks could allow others to create tokens and consume Redis storage. Rate limiting mitigates abuse but does not restrict who can create tokens.

**Trigger stays public by design.** Requiring auth on `/canary/trigger/{token_id}` would break the honeypot — attackers must be able to hit the tripwire without credentials.

---

## Quick checklist for testers

1. `POST /canary/generate-token` → copy `Token_ID` and `auth_string`.
2. Use **both** on fetch/delete URLs: `.../fetch/id/{Token_ID}/{auth_string}`.
3. Use **only** `Token_ID` on trigger: `.../trigger/{Token_ID}`.
4. Deploy **`Canary_Token`** (not `auth_string`) as the decoy in your environment.
5. Wrong secret → expect `403`, not `404`.

See [test-fixtures/](../test-fixtures/) for Postman collections and manual scenarios that follow this model.
