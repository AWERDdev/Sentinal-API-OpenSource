import logging
import os

def setupLogger():
    log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    log_dir = "/tmp/" if os.environ.get("VERCEL") else ""
    
    app_handler = logging.FileHandler(f"{log_dir}app.log")
    app_handler.setFormatter(log_format)

    ratelimit_handler = logging.FileHandler(f"{log_dir}rate_limiter.log")
    ratelimit_handler.setFormatter(log_format)

    redis_handler =  logging.FileHandler(f"{log_dir}redis.log")
    redis_handler.setFormatter(log_format)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(app_handler)
    app_logger.addHandler(console_handler)
    app_logger.propagate = False

    ratelimit_logger = logging.getLogger("app.rate_limiter")
    ratelimit_logger.setLevel(logging.INFO)
    ratelimit_logger.addHandler(ratelimit_handler)
    ratelimit_logger.addHandler(console_handler)
    ratelimit_logger.propagate = False

    redis_logger = logging.getLogger("app.redis")
    redis_logger.setLevel(logging.INFO)
    redis_logger.addHandler(redis_handler)
    redis_logger.addHandler(console_handler)
    redis_logger.propagate = False

    
