from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, status

from app.models.store import TokenPair, store


ACCESS_TOKEN_TTL = timedelta(minutes=45)
REFRESH_TOKEN_TTL = timedelta(days=7)


class AuthService:
    def register(self, email: str, password: str, full_name: Optional[str]) -> TokenPair:
        try:
            user = store.create_user(email=email, password=password, full_name=full_name)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return store.issue_tokens(user.id, ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL)

    def login(self, email: str, password: str) -> TokenPair:
        user = store.verify_user(email, password)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return store.issue_tokens(user.id, ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL)

    def refresh(self, refresh_token: str) -> TokenPair:
        token_pair = store.refresh(refresh_token, ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL)
        if not token_pair:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
        return token_pair


auth_service = AuthService()

