# Sentinel API — Setup Guide

This guide walks through environment configuration, dependency installation, local execution, and Redis connectivity verification for the Sentinel (CanaryBox) API.

---

## Prerequisites

| Requirement | Version / notes |
|-------------|-----------------|
| Python | 3.10+ recommended |
| Redis | Running instance reachable from the API host (local or remote) |
| Resend account | Optional for development; required for breach email alerts |
| Uvicorn | ASGI server (install separately — see below) |

Pinned dependencies in `requirements.txt`: FastAPI 0.110.0, Pydantic 2.6.4, redis 5.0.3, resend 0.8.0.

---

## 1. Clone and Install Dependencies

```bash
git clone https://github.com/AWERDdev/sentinel-api.git
cd sentinel-api
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
pip install uvicorn python-dotenv
```

`requirements.txt` includes `email-validator` (required for Pydantic `EmailStr`). Route modules import `python-dotenv` at runtime — install it explicitly if not already present.

---

## 2. Environment Variables

Create a `.env` file in the project root (same directory as `main.py`). Route modules load it via `dotenv.load_dotenv()`. Redis settings load via Pydantic `BaseSettings` with the `REDIS_` prefix.

### Application variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DOMAIN` | No | `http://127.0.0.1:8000` | Base URL used when generating `http`/`https`/`web`/`url` tripwire links. **Set this in production** to your public API hostname. |
| `RESEND_API_KEY` | Yes (for alerts) | — | API key for [Resend](https://resend.com). Used by `routes/canary_trigger.py` to send breach notification emails. Without it, triggers still update Redis but emails fail (errors are logged). |

### Redis variables (`REDIS_` prefix)

Loaded by `redis_Settings` in `models/redis_settings_model.py`. The application connects via **`REDIS_URL`** using `redis.from_url()` in `config.py`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | No | `redis://localhost:7001/` | Full Redis connection URL (primary — used by `config.py`) |
| `REDIS_HOST` | No | `localhost` | Documented for reference; not used directly when `REDIS_URL` is set |
| `REDIS_PORT` | No | `6379` | Logged on successful connection; default URL port may differ |
| `REDIS_DECODE_RESPONSES` | No | `true` | Decode Redis byte responses to strings |
| `REDIS_ENCODING` | No | `utf-8` | String encoding for Redis client |
| `REDIS_MAX_REQUESTS` | No | `5` | Max requests per IP per rate-limit window |
| `REDIS_WINDOW_SECONDS` | No | `60` | Rate-limit window length in seconds |

> **Important:** The code default for `REDIS_URL` is `redis://localhost:7001/`, which does not match a typical local Redis install on port `6379`. Always set `REDIS_URL` explicitly in your `.env`.

### Example `.env`

```env
# Public base URL for generated tripwire links
DOMAIN=http://127.0.0.1:8000

# Resend email API key
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx

# Redis connection (adjust port/host for your setup)
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_REQUESTS=10
REDIS_WINDOW_SECONDS=60
```

> **Security:** Never commit `.env` to version control. The project's `.gitignore` excludes it.

---

## 3. Start Redis

### Option A — Local Redis (Docker)

```bash
docker run -d --name sentinel-redis -p 6379:6379 redis:7-alpine
```

Set `REDIS_URL=redis://localhost:6379/0` in `.env`.

### Option B — Local Redis (native)

Install Redis for your OS and start the server on port `6379` (or update `REDIS_URL` accordingly).

### Option C — Managed Redis (e.g., Upstash)

Set `REDIS_URL` to your provider's connection string (includes host, port, password, and TLS as needed).

---

## 4. Start the Application

From the project root with your virtual environment activated:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

| Flag | Purpose |
|------|---------|
| `--reload` | Auto-restart on code changes (development only) |
| `--host 127.0.0.1` | Bind to localhost |
| `--port 8000` | Default port referenced in `DOMAIN` fallback |

On startup:

- `setupLogger()` writes to `app.log`, `redis.log`, `rate_limiter.log`, and the console (or `/tmp/` on Vercel).
- `config.py` attempts a Redis connection and logs success or failure to `redis.log`.

---

## 5. Verify the API Is Running

### Health check

```bash
curl http://127.0.0.1:8000/
```

Expected:

```json
{"message": "welcome to canary token generator API", "status": 200}
```

### Interactive API docs

Open in a browser:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Custom docs pointer: `http://127.0.0.1:8000/canary/docs`

---

## 6. Verify Redis Connectivity

### Method 1 — Application logs

After starting Uvicorn, check `redis.log` or console output for:

```text
Successfully connected to Redis on port 6379
```

If connection fails, you will see:

```text
Connecting to Redis failed <error details>
```

> If Redis fails at startup, the app still boots but all Redis-dependent routes will error at runtime.

### Method 2 — End-to-end token round-trip

Generate a token (writes to Redis), then fetch it with the returned owner secret:

```bash
# Create token
curl -X POST http://127.0.0.1:8000/canary/generate-token \
  -H "Content-Type: application/json" \
  -d '{
    "token_type": "http",
    "name": "redis connectivity test",
    "alert_email": "you@example.com"
  }'
```

Copy `Token_ID` and `auth_string` from the response, then:

```bash
curl "http://127.0.0.1:8000/canary/fetch/id/{Token_ID}/{auth_string}"
```

A `200` response with the full token object confirms Redis read/write is working. A `403` means the wrong `auth_string` was used.

### Method 3 — Redis CLI inspection

```bash
redis-cli ping
# Expected: PONG

# After generating a token:
redis-cli KEYS "canary:*"
redis-cli GET "canary:token:<your-token-id>"
```

You should see keys matching:

- `canary:token:{uuid}`
- `canary:name:redis_connectivity_test`
- `rate_limit:127.0.0.1` (after API requests)

### Method 4 — Python one-liner

```bash
python -c "from config import redis_connect; print(redis_connect.ping())"
```

Expected output: `True`

---

## 7. Verify Email Alerts (Optional)

1. Set a valid `RESEND_API_KEY` in `.env`.
2. Generate a token with your Resend-verified recipient email as `alert_email`.
3. Trigger the tripwire:

```bash
curl http://127.0.0.1:8000/canary/trigger/{Token_ID}
```

4. Check your inbox for subject `🚨 BREACH DETECTED: {token_name}`.
5. Confirm `app.log` contains: `Security alert email successfully dispatched to ...`

> **Resend sandbox:** On free-tier accounts, emails may only deliver to the address you registered with. See [`routes/localEmail_testing.md`](../routes/localEmail_testing.md) for details. The default sender is `CanaryBox <onboarding@resend.dev>`.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Connecting to Redis failed` on startup | Redis not running or wrong URL | Start Redis; set `REDIS_URL=redis://localhost:6379/0` |
| Runtime errors on all routes after startup | Redis connection failed silently | Check `redis.log`; verify `REDIS_URL` |
| `429 Too Many Requests` during testing | Rate limit hit (default 5/min) | Wait 60s or raise `REDIS_MAX_REQUESTS` |
| `403` on fetch after create | Wrong `auth_string` in URL | Use the exact `auth_string` from the generation response |
| `404` on fetch after create | Redis write failed or wrong token ID | Check Redis logs; verify keys with `redis-cli` |
| No email received | Missing/invalid `RESEND_API_KEY` or unverified recipient | Check `app.log`; see `localEmail_testing.md` |
| HTTP links point to localhost in production | `DOMAIN` not set | Set `DOMAIN` to your public API URL |

---

## 9. Log Files

| File | Contents |
|------|----------|
| `app.log` | General application events, token lifecycle, email dispatch |
| `redis.log` | Redis connection status |
| `rate_limiter.log` | Rate-limit violations by IP |

On Vercel (`VERCEL` environment variable set), these files are written to `/tmp/` instead of the project root.

---

## 10. Deploying to Vercel

The repo includes `vercel.json` routing all requests to `main.py` via `@vercel/python`.

1. Set environment variables in the Vercel dashboard (`REDIS_URL`, `RESEND_API_KEY`, `DOMAIN`).
2. Use a managed Redis provider (e.g., Upstash) reachable from Vercel's network.
3. Set `DOMAIN` to your Vercel deployment URL so generated tripwire links resolve correctly.

Background email tasks run in-process within the same serverless invocation.

---

## Next Steps

- Review [authentication.md](./authentication.md) for per-token `auth_string` usage on fetch and delete routes.
- Review [architecture.md](./architecture.md) for system design and request flow.
- Review [api-reference.md](./api-reference.md) for full endpoint specifications.
- Review [design-decisions.md](./design-decisions.md) for engineering rationale.
- Use [test-fixtures/](../test-fixtures/) for Postman collections and manual test scenarios.
