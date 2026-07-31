import json
from fastapi import HTTPException,status
from config import redis_connect

def verify_token_owner(token_id:str,auth_string:str):
    
    raw_token_data = redis_connect.get(f"canary:token:{token_id}")

    if not raw_token_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cannary token not found"
        )
    
    if isinstance(raw_token_data,bytes):
        raw_token_data = raw_token_data.decode("utf-8")
    
    token_data = json.loads(raw_token_data)

    expected_auth_string = token_data.get("auth_string")
    
    # 3. Enforce the match
    if not expected_auth_string or auth_string != expected_auth_string:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Invalid X-API-Key for this token ID."
        )
    
    # Optimization: return the token data so your endpoint doesn't have to fetch it from Redis a second time!
    return token_data


def verify_token_owner_by_name(name: str,auth_string: str):
    # Step 1: Resolve the name to the ID
    name_key = f"canary:name:{name.replace(' ', '_').lower()}"
    token_id = redis_connect.get(name_key) 
    
    if not token_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canary token name not found."
        )

    # Convert bytes to string if necessary
    token_id_str = token_id.decode('utf-8') if isinstance(token_id, bytes) else token_id

    # Step 2: Use the resolved ID to get the actual payload
    raw_token_data = redis_connect.get(f"canary:token:{token_id_str}")
    
    if not raw_token_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canary token payload data missing."
        )
        
    if isinstance(raw_token_data, bytes):
        raw_token_data = raw_token_data.decode('utf-8')
        
    token_data = json.loads(raw_token_data)
    
    # Step 3: Auth check
    expected_auth_string = token_data.get("auth_string")
    if not expected_auth_string or auth_string != expected_auth_string:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Invalid X-API-Key for this token name."
        )
    
    return token_data