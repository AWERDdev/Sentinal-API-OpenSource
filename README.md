# Sentinel API

A lightweight honeypot canary token service built with **FastAPI**. Provision fake URLs or AWS-style credentials, deploy them as tripwires in your environments, and get alerted when an unauthorized party interacts with them.

**Hosted demo**: [https://sentinel-api-rho.vercel.app/](https://sentinel-api-rho.vercel.app/)

---

## ⚠️ Live Demo Disclaimer

> **This is a live public demo instance.** Do **not** enter real credentials, personally identifiable information (PII), or any sensitive data.
>
> Strictly use **synthetic or mock data** when testing token generation, fetch endpoints, and canary triggers.
>
> Read the full notice: [DISCLAIMER.md](./DISCLAIMER.md)

---

## What it does

1. **Generate** decoy tokens (`http`, `https`, or `aws` format)
2. **Deploy** the returned payload in configs, repos, or secret stores
3. **Detect** when someone triggers the tripwire
4. **Alert** you via email (Resend) with attacker IP, user agent, and timestamp

Token state and rate limiting are backed by **Redis**.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file with at least:

```env
DOMAIN=http://127.0.0.1:8000
RESEND_API_KEY=your_resend_api_key
REDIS_HOST=localhost
REDIS_PORT=6379
```

Start Redis, then run the API:

```bash
uvicorn main:app --reload
```

Verify it is running:

```bash
curl http://127.0.0.1:8000/
```

For full setup steps, environment variables, and Redis verification, see the [Setup Guide](DOCS/setup-guide.md).

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](DOCS/architecture.md) | System design, project structure, FastAPI and Redis roles, request flow from token generation to trigger interception |
| [Authentication](DOCS/authentication.md) | Per-token `auth_string` secrets — what they are, which routes need them, and common mistakes |
| [API Reference](DOCS/api-reference.md) | Endpoint specifications — methods, request/response examples, status codes, and lifecycle roles |
| [Setup Guide](DOCS/setup-guide.md) | Environment configuration, local execution, Redis connectivity checks, and troubleshooting |
| [Design Decisions](DOCS/design-decisions.md) | Engineering rationale — `BackgroundTasks`, token validation, honeypot deception strategy, and more |
| [Test Fixtures](test-fixtures/README.md) | Postman collection, sample payloads, and manual test scenarios for development and API testing |

---

## API overview

Fetch and delete routes require the owner secret (`auth_string`) returned at token creation. See [Authentication](DOCS/authentication.md).

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| `POST` | `/canary/generate-token` | No | Create a new canary token |
| `GET` | `/canary/fetch/id/{token_id}/{auth_string}` | Owner secret | Retrieve token by UUID |
| `GET` | `/canary/fetch/name/{name}/{auth_string}` | Owner secret | Retrieve token by name |
| `GET` | `/canary/trigger/{token_id}` | No | Honeypot tripwire (attacker-facing) |
| `DELETE` | `/canary/delete/id/{token_id}/{auth_string}` | Owner secret | Delete token by UUID |
| `DELETE` | `/canary/delete/name/{name}/{auth_string}` | Owner secret | Delete token by name |

Interactive OpenAPI docs: [https://sentinel-api-rho.vercel.app/docs](https://sentinel-api-rho.vercel.app/docs) (hosted) or `http://127.0.0.1:8000/docs` (local, when the server is running).

See [API Reference](DOCS/api-reference.md) for full request bodies, response shapes, and error codes.

---

## Development & testing

The [`test-fixtures/`](test-fixtures/) folder provides sample data for **local development** and **API testing**. Use it while building new routes, validating changes, or running regression checks — not as production data.

### What's included

| File | Format | Use |
|------|--------|-----|
| [`canary_generation_tests.json`](test-fixtures/canary_generation_tests.json) | Postman Collection v2.1 | Automated requests — health checks, token generation (`http`, `https`, `aws`), and validation error cases |
| [`canary_test_cases.md`](test-fixtures/canary_test_cases.md) | Markdown | Manual scenarios with example URLs, request bodies, and expected responses across the full canary lifecycle |
| [`canaryTokens.json`](test-fixtures/canaryTokens.json) | JSON | Sample `201 Created` responses (`Token_ID`, `Canary_Token`, etc.) for reference while debugging response shape |

### Development testing

While implementing or changing API behavior:

- Copy request bodies from the Postman collection or markdown scenarios into Swagger UI (`/docs`), `curl`, or your HTTP client
- Compare live responses against examples in `canary_test_cases.md` and `canaryTokens.json`
- Re-run the collection or manual cases after code changes to confirm generation, fetch, trigger, and delete flows still work

### API testing

**Postman** — import `canary_generation_tests.json`, point requests at `http://127.0.0.1:8000`, and run the collection.

**Manual** — follow [`canary_test_cases.md`](test-fixtures/canary_test_cases.md) for health checks, token creation, fetch by ID/name, trigger interception (including the deceptive honeypot response), and error cases.

**Sample data** — use `canaryTokens.json` when testing fetch/delete routes or validating URL and AWS credential formatting without generating new tokens each time.

### Quick workflow

```text
1. Start Redis + API (see Setup Guide above)
2. POST /canary/generate-token → save Token_ID and auth_string
3. Import canary_generation_tests.json into Postman → run generation, then lifecycle tests
4. Walk through canary_test_cases.md for fetch / trigger / delete (with auth_string in URLs)
5. Compare responses with canaryTokens.json when validating output shape
```

Full details, file descriptions, and tips: [test-fixtures README](test-fixtures/README.md).

---

## Tech stack

- [FastAPI](https://fastapi.tiangolo.com/) — HTTP API framework
- [Redis](https://redis.io/) — Token storage, name indexing, rate limiting
- [Resend](https://resend.com/) — Breach notification emails
- [Pydantic](https://docs.pydantic.dev/) — Request and storage model validation
- [Uvicorn](https://www.uvicorn.org/) — ASGI server

---

## Project structure

```text
sentinel-api/
├── main.py                 # Application entry point
├── config.py               # Redis client and rate limiter
├── models/                 # Pydantic models
├── routes/                 # API route modules
├── logger_config/          # Logging setup
├── DOCS/                   # Project documentation
├── test-fixtures/          # Postman collection, sample payloads, manual test cases
└── requirements.txt
```

---

## License

See repository settings for license information.
