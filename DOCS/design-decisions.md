# Sentinel API — Design Decisions

This document explains the engineering rationale behind key choices in the Sentinel (CanaryBox) codebase. Each section ties a decision to the threat model, operational constraints, or implementation trade-offs visible in the current source.

---

## 1. FastAPI as the Application Framework

**Decision:** Use FastAPI with modular `APIRouter` instances rather than a monolithic route file or a heavier framework.

**Why:**

- **Pydantic-native validation** — `CanaryTokenCreate` enforces structure at the HTTP boundary. Invalid `token_type` values and missing fields are rejected before Redis is touched.
- **Dependency injection for cross-cutting policy** — Rate limiting is a `Depends(ratelimiter)` declaration on every route, not duplicated guard code in each handler.
- **Async-ready trigger handler** — The honeypot endpoint is `async` and integrates `BackgroundTasks` without introducing Celery, Redis queues, or a separate worker process.
- **Low operational footprint** — A single Uvicorn process is sufficient for a developer-focused honeypot tool.

**Trade-off:** No built-in admin UI. Token generation is open to any caller; management routes rely on per-token secrets instead of global operator auth.

---

## 2. Redis as the Sole Datastore

**Decision:** Store all token documents, name indexes, and rate-limit counters in Redis with simple string keys.

**Why:**

- **Access pattern fit** — Every operation is a point lookup (`GET`/`SET`/`DEL`/`INCR`) by known key. No relational joins or ad-hoc queries.
- **Speed** — Trigger interception must be fast; Redis keeps read/write latency low so the deceptive response returns quickly.
- **Dual use for rate limiting** — The same client connection performs `INCR` + `EXPIRE` on `rate_limit:{ip}` keys, avoiding a second infrastructure component.
- **Schema flexibility** — Token JSON can accumulate breach `logs` without migrations. The document shape evolves in place.

**Key design:**

```text
canary:token:{uuid}      → full token JSON (primary record)
canary:name:{normalized} → uuid string (secondary index)
rate_limit:{ip}          → integer counter with TTL
```

**Connection:** `config.py` uses `redis.from_url(settings.URL)` where `URL` comes from `REDIS_URL` (default `redis://localhost:7001/`).

**Trade-off:** No durable audit trail beyond what is stored on each token's `logs` array. Redis persistence configuration (RDB/AOF) is a deployment concern, not enforced in code.

---

## 3. Secondary Name Index

**Decision:** Maintain a separate Redis key `canary:name:{normalized_name}` mapping to `token_id`, rather than scanning all token keys.

**Why:**

- **O(1) lookup by name** — Operators think in terms of labels like "Production Database Honey Key", not UUIDs.
- **Normalized keys** — Names are lowercased and spaces replaced with underscores (`name.replace(' ', '_').lower()`), reducing accidental duplicate-index issues from casing differences.

**Trade-off:** Name uniqueness is not enforced atomically. Creating two tokens with names that normalize to the same key would overwrite the index (last write wins). The API treats `name` as a convenience index, not a strict unique constraint.

---

## 4. `token_type` Sanitization and Validation

**Decision:** Apply `data.token_type.strip().lower()` and whitelist `["http", "https", "aws", "web", "url"]`.

**Why:**

- **Input normalization** — Clients may send `"HTTP"`, `" Http "`, etc. Stripping and lowercasing makes validation predictable.
- **Explicit allowlist** — Only supported honeypot formats receive generated payloads. Unknown types fail fast with `400 Bad Request` and a message listing allowed values.
- **Alias types** — `web` and `url` are accepted as aliases that produce the same HTTP tripwire URL as `http`/`https`.

**Relevant code path:**

```python
token_type_clean = data.token_type.strip().lower()
allowed_types = ["http", "https", "aws", "web", "url"]
if token_type_clean not in allowed_types:
    raise HTTPException(status_code=400, ...)
```

**Trade-off:** No extensibility plugin system. Adding a new token type (e.g., `dns`) requires a code change to the allowlist and generation branch.

---

## 5. Type-Specific Decoy Payloads

**Decision:** Generate different decoy formats per `token_type`. The deployable payload is stored in the `CanaryToken` field (returned as `Canary_Token` in the generation response).

| Type | Payload shape (`CanaryToken` field) | Rationale |
|------|-------------------------------------|-----------|
| `http` / `https` / `web` / `url` | Full URL to `/canary/trigger/{id}` | Mimics a leaked admin link; any HTTP client triggers the tripwire |
| `aws` | Fake `aws_access_key_id` / `aws_secret_access_key` block | Mimics credentials in `.env`, CI secrets, or config dumps |

**Separate owner secret:** At generation, a UUID is assigned to the `auth_string` field. This is **not** the decoy — it is the secret operators use on fetch and delete routes. It is returned once in the generation response and must be stored by the operator.

**Why:** High-fidelity decoys match real secret formats attackers already scan for, increasing the chance of interaction compared to generic placeholder strings.

**`DOMAIN` dependency:** HTTP tripwire URLs use `os.getenv('DOMAIN', 'http://127.0.0.1:8000')` so the same codebase works locally and in production without hardcoding hostnames.

---

## 6. BackgroundTasks for Email Processing

**Decision:** Queue `send_security_alert` via FastAPI `BackgroundTasks` instead of sending email synchronously in the trigger handler.

**Why:**

- **Response latency** — The honeypot must return quickly. Waiting on Resend's HTTP API would add hundreds of milliseconds to seconds of delay.
- **Failure isolation** — Email errors are caught and logged inside `send_security_alert`. A Resend outage does not prevent Redis state updates or the deceptive HTTP response.
- **Simplicity** — No message broker, no worker fleet. For low-to-moderate trigger volume, in-process background tasks are sufficient.

```python
background_tasks.add_task(
    send_security_alert,
    user_email,
    token_data.get("name", "Unknown Token"),
    attacker_ip,
    user_agent,
)
```

**Trade-off:** Background tasks run in the same process as the API. On serverless (Vercel), if the invocation terminates immediately after responding, an in-flight email task could be lost.

---

## 7. Honeytoken Deception Strategy

**Decision:** On successful trigger, return HTTP `200 OK` with a JSON body that **mimics a chaotic server failure**, rather than confirming the honeypot fired.

**Deceptive response body:**

```json
{
  "status": "panik",
  "code": "SERVER_HAS_LEFT_THE_CHAT",
  "message": "Something went horribly wrong. We blamed the intern, but honestly, it was probably your payload :).",
  "Your_Problem_not_mine": "It worked on my machine. ¯\\_(ツ)_/¯"
}
```

**Why:**

- **Attacker psychology** — Automated scanners often abandon paths that return obvious "access logged" messages. A bland or humorous error suggests a dead end, not active monitoring.
- **Status code choice** — Using `200` with an error-shaped body avoids some tools deprioritizing `4xx`/`5xx` URLs. Real `500` responses are reserved for genuine handler failures.
- **Contrast with operator endpoints** — Management routes return honest, descriptive messages because they are called by trusted operators.

**What still happens server-side (invisible to attacker):**

1. Token `status` → `COMPROMISED`
2. `breach_count` incremented
3. Attacker IP and `User-Agent` appended to `logs`
4. Email alert dispatched in the background

**Trade-off:** A sophisticated attacker inspecting response bodies across requests might infer monitoring. Deception raises the bar; it does not guarantee invisibility.

---

## 8. Client IP Attribution

**Decision:** Prefer `X-Forwarded-For` (first hop) when present; otherwise use `request.client.host`.

**Why:**

- Deployments behind reverse proxies (nginx, Cloudflare, load balancers) see the proxy IP without `X-Forwarded-For`.
- Taking the first comma-separated value follows common convention for original client IP.

**Trade-off:** Spoofed `X-Forwarded-For` headers can poison logs if the API is exposed directly without a trusted proxy stripping client-supplied values. Production deployments should only trust forwarded headers from known proxies.

---

## 9. IP-Based Rate Limiting on All Routes

**Decision:** Apply `ratelimiter` to root, `/canary/docs`, generation, fetch, trigger, and delete endpoints.

**Why:**

- **Abuse prevention** — Attackers could spam `generate-token` or `trigger` to flood Redis, logs, or Resend quotas.
- **Redis-backed window** — `INCR` on first request sets `EXPIRE`; subsequent requests increment atomically.
- **Configurable thresholds** — `REDIS_MAX_REQUESTS` and `REDIS_WINDOW_SECONDS` tune strictness per environment.

**Trade-off:** Shared NAT IPs (corporate networks) share one bucket. Trigger endpoint rate limiting could theoretically slow repeated breach attempts from the same egress IP — usually acceptable for a honeypot.

---

## 10. Pydantic Models: Input vs. Storage

**Decision:** Separate `CanaryTokenCreate` (API input) from `CanaryToken` (Redis document).

**Why:**

- **Least privilege on input** — Clients cannot set `token_ID`, `breach_count`, `status`, or `logs` at creation time. The server owns those fields.
- **Defaults on storage** — `created_at`, `is_active`, `status`, `breach_count`, and `logs` are initialized server-side with safe defaults.
- **Serialization** — `model_dump_json()` produces consistent JSON for Redis storage on create.

**Trade-off:** Fetch endpoints return the full internal document including `alert_email` and `auth_string`. Operators must treat fetch responses as sensitive.

---

## 11. Per-Token Auth via Path Parameter

**Decision:** Protect fetch and delete routes with a per-token owner secret (`auth_string`) passed as a URL path segment, verified by `utils/canary_verify.py`.

**Why:**

- **Simple API-key model** — No JWT infrastructure, sessions, or global API keys required.
- **Secret returned once** — Generated alongside the token; operators store it like any other credential.
- **Trigger stays open** — The honeypot endpoint cannot require auth without breaking the threat model.

```python
if not expected_auth_string or auth_string != expected_auth_string:
    raise HTTPException(status_code=403, detail="Access Denied: Invalid X-API-Key ...")
```

**Trade-off:**

- Secret in the URL may appear in access logs, browser history, and referrer headers. Header-based auth would be safer for production hardening.
- `POST /generate-token` remains unauthenticated — anyone can create tokens and consume Redis storage.
- Verification is a manual function call, not a FastAPI `Depends`, so OpenAPI docs do not automatically document the auth requirement.

---

## 12. Logging Strategy

**Decision:** Three dedicated loggers (`app`, `app.redis`, `app.rate_limiter`) with separate log files plus console output.

**Why:**

- **Operational separation** — Redis connection issues and rate-limit events can be diagnosed without sifting through all application logs.
- **Security auditing** — Token generation, triggers, deletions, and email dispatch are logged at INFO; failures at WARNING/ERROR.

**Trade-off:** Log files grow unbounded; no rotation is configured in code. On Vercel, logs write to `/tmp/`.

---

## 13. Error Handling Philosophy by Endpoint Class

| Endpoint class | Error style | Rationale |
|----------------|-------------|-----------|
| Operator (generate, fetch, delete) | Honest HTTP status + `detail` string | Operators need actionable feedback |
| Honeypot (trigger) | Deceptive `200` on success; honest `404` only if token missing | Balance attribution with deception |
| Infrastructure failures | `500` with generic detail | Avoid leaking stack traces to clients |

Delete handlers wrap unexpected exceptions in `500` with a generic message while logging the real error server-side.

Fetch/delete auth failures return `403` (not `401`) with a message referencing "X-API-Key" even though the secret is passed as a path parameter.

---

## Summary

Sentinel API optimizes for **simplicity, speed, and deception**:

- FastAPI + Pydantic keep the HTTP layer strict and thin.
- Redis provides fast key-value storage and rate limiting in one service.
- Background email delivery protects trigger response time.
- Sanitized `token_type` validation prevents ambiguous decoy generation.
- Per-token `auth_string` secrets protect management routes while the honeypot stays open.
- The trigger returns fake panic errors so attackers stay unaware while operators receive real alerts.

These choices reflect a developer-tool threat model: operators provision and manage tokens with per-token secrets; untrusted parties trigger tripwires. Global operator authentication and header-based secrets are not implemented in the current codebase.
