import logging
import os

import dotenv
from fastapi import APIRouter, Depends, HTTPException, status

# Import both authentication dependencies
from utils.canary_verify import verify_token_owner, verify_token_owner_by_name
from config import ratelimiter, redis_connect

# Load environment variables
dotenv.load_dotenv()

# Setup route logging
logger = logging.getLogger("app")

# Initialize router with clean metadata mappings
router = APIRouter(
     prefix="/canary",
     tags=["canary", "token management"],
     responses={
          404: {"description": "Not found"},
          200: {"description": "Canary Token Handler"}
     }
)

# ==========================================
# 1. DELETE BY TOKEN ID
# ==========================================
@router.delete('/delete/id/{token_id}/{auth_string}', dependencies=[Depends(ratelimiter)])
def delete_canary_by_id(token_id: str,auth_string:str): 
    """
    Deletes token configuration and its secondary name index safely.
    The verify_token_owner dependency handles ownership checks and drops 404s automatically.
    """
    token_data = verify_token_owner(token_id, auth_string)
    try:    
        logger.info(f"Authorized delete request running for Token ID: {token_id}")
        
        # 1. Run validation outside of the try block so 404/403 exceptions pass through cleanly
       
        # Extract the name from token_data (which the dependency already looked up and parsed for us!)
        token_name = token_data.get("name")
        name_key = f"canary:name:{token_name.replace(' ', '_').lower()}"
        token_key = f"canary:token:{token_id}"

        # Clean delete both keys out of Redis storage
        redis_connect.delete(token_key)
        redis_connect.delete(name_key)
             
        logger.info(f"Token {token_id} and index {name_key} successfully dropped.")
        return {"message": f"Token with ID {token_id} deleted successfully."}

    except Exception as e:
        logger.error(f"Failed to execute database delete operation for ID {token_id}. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred during deletion"
        )


# ==========================================
# 2. DELETE BY TOKEN NAME
# ==========================================
@router.delete('/delete/name/{name}/{auth_string}', dependencies=[Depends(ratelimiter)])
def delete_canary_by_name(name: str,auth_string:str ):
    """
    Resolves name mappings securely via secondary index lookups, 
    verifies ownership, and wipes target configuration parameters cleanly out of memory.
    """
    token_data = verify_token_owner_by_name(name,auth_string)
    try:
        logger.info(f"Authorized delete request running for Token Name: {name}")
             
        # Extract the ID from the payload provided by our name dependency
        
        token_id = token_data.get("token_ID")
        
        name_key = f"canary:name:{name.replace(' ', '_').lower()}"
        token_key = f"canary:token:{token_id}"

        # Clean delete both keys out of Redis storage
        redis_connect.delete(token_key)
        redis_connect.delete(name_key)
             
        logger.info(f"Token {token_id} and index {name_key} successfully dropped.")
        return {"message": f"Token '{name}' deleted successfully."}

    except Exception as e:
        logger.error(f"Failed to execute database delete operation for Name {name}. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred during deletion"
        )