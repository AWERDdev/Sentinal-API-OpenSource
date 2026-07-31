import time
import logging
from fastapi import Request, HTTPException, status
import redis
from models.redis_settings_model import redis_Settings

redis_logger = logging.getLogger("app.redis")
rate_limiter_logger = logging.getLogger("app.rate_limiter")

settings = redis_Settings()

try:
    redis_connect = redis.from_url(
        url=settings.URL,  
        decode_responses=settings.DECODE_RESPONSES,
        encoding=settings.ENCODING
    )
    redis_logger.info(f"Successfully connected to Redis on port {settings.PORT}")
except Exception as e:
    redis_logger.error(f"Connecting to Redis failed {e}")

def ratelimiter(request: Request):
    # 1. Hierarchical Identity Resolution (API Key > Raw IP)
    api_key = request.headers.get("X-API-Key")
    
    if api_key:
        identifier = f"key:{api_key.strip()}"
    else:
        # Fallback to IP tracking if no API key is passed
        forwarded_for = request.headers.get("X-Forwarded-For")
        client_IP = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
        identifier = f"ip:{client_IP}"

    # 2. Add Route-Level Fingerprinting
    # Protects specific expensive routes from being targeted while keeping others open
    route_path = request.url.path
    redis_key = f"rate_limit:{identifier}:{route_path}"

    MAX_REQUESTS = settings.MAX_REQUESTS
    WINDOW_SECONDS = settings.WINDOW_SECONDS

    try:
        # 3. Atomic Redis Pipeline (Fixes the race condition bug)
        pipe = redis_connect.pipeline()
        pipe.incr(redis_key)
        pipe.ttl(redis_key)
        current_requests, current_ttl = pipe.execute()

        # If the key was just created (or missing an expiration due to an edge case), set it safely
        if current_requests == 1 or current_ttl == -1:
            redis_connect.expire(redis_key, WINDOW_SECONDS)

    except Exception as e:
        rate_limiter_logger.error(f"Redis rate limit check failed: {e}")
        # Fail Open / Closed depending on security preference
        return 

    # 4. Trigger Throttling Actions
    if current_requests > MAX_REQUESTS:
        rate_limiter_logger.warning(f"Throttling target {identifier} on route {route_path}")
        
        # TARPIT: Intentionally delay our response to tie up the attacker's resources
        # An asynchronous app handles idle sleeps with zero overhead, but scripts will hang.
        time.sleep(5) 
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )