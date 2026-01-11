from fastapi import APIRouter

from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.services.auth import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest):
    tokens = auth_service.register(payload.email, payload.password, payload.full_name)
    return tokens


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    tokens = auth_service.login(payload.email, payload.password)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    tokens = auth_service.refresh(payload.refresh_token)
    return tokens
