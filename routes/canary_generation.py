import logging
import os
from uuid import uuid4

import dotenv
from fastapi import APIRouter, Body, Depends, HTTPException,status

from config import ratelimiter, redis_connect
from models.canary_model import CanaryToken, CanaryTokenCreate

# Load environment variables
dotenv.load_dotenv()

# Setup route logging
logger = logging.getLogger("app")

# Initialize router with clean metadata mappings
router = APIRouter(
    prefix="/canary",
    tags=["canary", "token generator"],
    responses={
    404: {"description": "Not found"},
    200: {"description": "Canary Token Handler"}
    }
)

# ==========================================
# 2. TOKEN GENERATION ENDPOINT
# ==========================================
@router.post('/generate-token', dependencies=[Depends(ratelimiter)], status_code=status.HTTP_201_CREATED)
def generate_token(data: CanaryTokenCreate = Body(...)):
    """Validates input payload and generates specific high-fidelity decoy configurations."""

    logger.info("A request for creating a new token has been made")
    logger.info(f"Retreving canary model {CanaryTokenCreate}")
    
    token_type_clean = data.token_type.strip().lower()

    # Unique identification token assignment
    token_id = str(uuid4())
    auth_string = str(uuid4())

    logger.info(f"Created canary token ID {token_id}")
    
    # Enforce validation on supported honeypot structures
    allowed_types = ["http", "https", "aws", "web", "url"]
    if token_type_clean not in allowed_types:
        logger.warning(f"Invalid token type attempted: {token_type_clean}")
        raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid token type. Choose from: {', '.join(allowed_types)}"
        )
        
    generated_auth = ""

    # Construct specific payloads depending on honey token classification
    if token_type_clean in ["http","https","web","url"]:
        # Construct the tracking link the attacker will accidentally click
        base_domain = os.getenv('DOMAIN', 'http://127.0.0.1:8000').rstrip('/')
        generated_auth = f"{base_domain}/canary/trigger/{token_id}"

    elif token_type_clean == "aws":
        # Construct a fake AWS credential block using the ID so you can track it
        generated_auth = f"aws_access_key_id=AKIA_{token_id[:16].upper()}\naws_secret_access_key=fake_secret_{token_id}"

    # Initialize the final model instance with system-generated IDs and payload metadata
    newCanary = CanaryToken(
        token_ID=token_id,
        token_type=token_type_clean,
        name=data.name,
        alert_email=data.alert_email,
        auth_string=auth_string,
        CanaryToken=generated_auth
    )
    
    # Redis Primary Key Storage
    token_key = f"canary:token:{token_id}"
    redis_connect.set(token_key, newCanary.model_dump_json())

    # Redis Secondary Index Lookup Mapping
    name_key = f"canary:name:{data.name.replace(' ', '_').lower()}"
    redis_connect.set(name_key, token_id)

    return {
        "message": "your token has been generated successfully",
        "Canary_Token": generated_auth,
        "Token_ID": token_id,
        "Token_Name": data.name,
        "auth_string":auth_string
    }
