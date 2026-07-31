import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the directory where this current file lives
current_dir = os.path.dirname(os.path.abspath(__file__))

class redis_Settings(BaseSettings):
    HOST: str = "localhost"
    PORT: int = 6379
    DECODE_RESPONSES: bool = True
    ENCODING: str = "utf-8"
    MAX_REQUESTS: int = 5
    WINDOW_SECONDS: int = 60
    URL: str = "redis://localhost:7001/"
    
    model_config = SettingsConfigDict(env_file=".env", env_prefix="REDIS_", extra="ignore")

    # Force absolute path resolution to your .env file
    # model_config = SettingsConfigDict(
    #     env_file=os.path.join(current_dir, "../.env"), # Adjust paths ('../' or './') based on your folder structure
    #     env_prefix="REDIS_",
    #     extra="ignore" # Prevents crashing if other unrelated variables are in .env
    # )