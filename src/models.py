from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
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


# CSV Upload Models
class UserDataRow(BaseModel):
    user_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    signup_date: Optional[str] = None
    last_active_date: Optional[str] = None


class CSVPreviewResponse(BaseModel):
    status: str
    message: str
    valid_columns: List[str]
    invalid_columns: List[str]
    total_rows: int
    valid_rows: int
    preview_data: List[Dict[str, Any]]
    errors: List[str] = []


class CSVUploadResponse(BaseModel):
    status: str
    message: str
    s3_file_key: Optional[str] = None
    dynamodb_records_written: int = 0
    errors: List[str] = []