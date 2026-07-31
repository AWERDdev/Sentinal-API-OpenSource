from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List, Dict

# 1. This is what you expect from Postman
class CanaryTokenCreate(BaseModel):
    token_type: str = Field(..., description="This decides what kind of token it is")
    name: str = Field(..., description="This is an easy way to find specific tokens")
    alert_email: EmailStr = Field(..., description="where to send the alert message if triggered") 

# 2. This is what you store in Redis
class CanaryToken(BaseModel):
    token_ID: str
    token_type: str
    name: str
    alert_email: EmailStr
    created_at: datetime = Field(default_factory=datetime.utcnow) # Automatically tracks time
    is_active: bool = True
    auth_string: Optional[str] = None
    CanaryToken:str
    status: str = "ACTIVE"
    breach_count: int = 0
    logs: List[Dict] = Field(default_factory=list)