import logging
import dotenv
from fastapi import APIRouter, Depends
from utils.canary_verify import verify_token_owner, verify_token_owner_by_name
from config import ratelimiter

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
# 2. FETCH BY ID ENDPOINT
# ==========================================
@router.get("/fetch/id/{token_id}/{auth_string}", dependencies=[Depends(ratelimiter)])
def fetch_canary_token_by_id(token_id: str, auth_string: str):
    """Fetches full token configurations directly via their tracking UUID strings."""
    logger.info("Canary token raw data fetched by ID")

    # Manually calling the verification function with the URL path arguments
    token_data = verify_token_owner(token_id, auth_string)
    return token_data


# ==========================================
# 3. FETCH BY NAME ENDPOINT
# ==========================================
@router.get("/fetch/name/{name}/{auth_string}", dependencies=[Depends(ratelimiter)])
def fetch_canary_token_by_name(name: str, auth_string: str):
    """Resolves name mappings securely to discover the active tracking payload data."""
    logger.info("Canary token raw data fetched by Name")
    
    # Mirroring the ID route exactly: path parameters passed directly into the helper
    token_data = verify_token_owner_by_name(name, auth_string)
    return token_data