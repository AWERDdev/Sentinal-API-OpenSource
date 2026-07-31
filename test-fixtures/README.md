# Test Fixtures

Sample payloads, request collections, and manual test scenarios for the Sentinel API. Use this folder during **local development** and **API testing** — not as production data.

**Authentication:** Fetch and delete routes require the owner secret (`auth_string`) in the URL path. See [DOCS/authentication.md](../DOCS/authentication.md) before running management-route tests.

---

## What's in this folder

| File | Format | Purpose |
|------|--------|---------|
| [`canary_generation_tests.json`](./canary_generation_tests.json) | Postman Collection v2.1 | Health checks, token generation, fetch/delete/trigger lifecycle, and auth failure cases |
| [`canary_test_cases.md`](./canary_test_cases.md) | Markdown | Step-by-step manual scenarios with `auth_string` paths and expected responses |
| [`canaryTokens.json`](./canaryTokens.json) | JSON array | Sample `201 Created` responses including `Token_ID`, `Canary_Token`, and `auth_string` |

---

## Auth quick reference

| Action | URL pattern | Needs `auth_string`? |
|--------|-------------|----------------------|
| Generate | `POST /canary/generate-token` | No |
| Fetch by ID | `GET /canary/fetch/id/{token_id}/{auth_string}` | **Yes** |
| Fetch by name | `GET /canary/fetch/name/{name}/{auth_string}` | **Yes** |
| Trigger | `GET /canary/trigger/{token_id}` | No (honeypot) |
| Delete by ID | `DELETE /canary/delete/id/{token_id}/{auth_string}` | **Yes** |
| Delete by name | `DELETE /canary/delete/name/{name}/{auth_string}` | **Yes** |

After generation, save **`auth_string`** (owner secret) separately from **`Canary_Token`** (decoy to deploy).

---

## Development testing

Use these fixtures while implementing or changing API behavior:

- **Request shapes** — Copy JSON bodies from `canary_generation_tests.json` or `canary_test_cases.md` into Swagger UI (`/docs`), `curl`, or your HTTP client.
- **Expected responses** — Compare live API output against examples in `canary_test_cases.md` and `canaryTokens.json`.
- **Regression checks** — Re-run the Postman collection after code changes to confirm generation, authenticated fetch, trigger, and authenticated delete still work.

Assumes the API is running locally at `http://127.0.0.1:8000` with Redis available. See the [Setup Guide](../DOCS/setup-guide.md).

---

## API testing

### Postman collection

1. Start the API: `uvicorn main:app --reload`
2. In Postman: **Import** → select `canary_generation_tests.json`
3. Run **Generate HTTP Web Beacon Token** first — the test script saves `token_id` and `auth_string` to collection variables.
4. Run fetch, trigger, delete, and auth-failure requests (they use `{{token_id}}` and `{{auth_string}}`).

The collection includes:

- **Health Checks** — `GET /`
- **Successful Token Generation** — `http`, `https`, and `aws` token types
- **Authenticated Management** — fetch by ID/name, delete by ID/name (uses saved variables)
- **Trigger & Honeypot** — tripwire with no auth
- **Auth Failures** — wrong `auth_string` → `403`
- **Input Validation & Error Handling** — invalid `token_type`, malformed payloads, missing fields

### Manual test cases

Open [`canary_test_cases.md`](./canary_test_cases.md) for documented flows with full `auth_string` URLs.

### Sample token data

[`canaryTokens.json`](./canaryTokens.json) holds example generation responses. Each entry includes `auth_string` for building fetch/delete URLs:

```text
GET /canary/fetch/id/{Token_ID}/{auth_string}
```

> IDs and secrets are from historical dev runs. For live testing, generate fresh tokens unless you have seeded Redis with matching records.

---

## Suggested workflow

```text
1. Start Redis + API (see DOCS/setup-guide.md)
2. POST /canary/generate-token → save Token_ID and auth_string
3. Import canary_generation_tests.json → run generation, then lifecycle folder
4. Or follow canary_test_cases.md manually
5. Compare response shapes with canaryTokens.json
```

For full endpoint specifications, see the [API Reference](../DOCS/api-reference.md).  
For auth concepts, see [Authentication](../DOCS/authentication.md).
