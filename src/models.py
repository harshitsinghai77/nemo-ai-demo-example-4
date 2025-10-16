from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class PingResponse(BaseModel):
    message: str
    status: str


class HelloResponse(BaseModel):
    message: str
    name: Optional[str] = None


class StatusResponse(BaseModel):
    status: str
    timestamp: str  # Changed to string
    version: str
    uptime: str
    environment: str


class User(BaseModel):
    id: str
    name: str
    email: str
    active: bool = True
    created_at: Optional[str] = None  # Changed to string
    recent_activity: Optional[List[str]] = None


class CreateUserRequest(BaseModel):
    name: str
    email: str


class CreateUserResponse(BaseModel):
    id: str
    name: str
    email: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str