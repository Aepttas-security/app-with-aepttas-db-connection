# app/models/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Dict


# Advanced Feature #1: Pydantic input sanitization and verification rules
class ParentRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Parent display name")
    email: EmailStr = Field(..., description="Valid parent email address")
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")

class ParentLoginRequest(BaseModel):
    email: str
    password: str

class UserProfileResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

class RegistrationResponse(BaseModel):
    message: str
    user: UserProfileResponse

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    user_name: str
    assigned_role: str  # <-- CRITICAL: Will return 'PARENT' or 'CHILD' just add this

# In-memory user table data store simulation
MOCK_USERS_DB: Dict[str, dict] = {}
USER_ID_COUNTER = 1