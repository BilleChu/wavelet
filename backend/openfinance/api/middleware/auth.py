"""
Authentication and Authorization Middleware.

Provides API key and JWT authentication for data service endpoints.
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
BEARER_SECURITY = HTTPBearer(auto_error=False)


class AuthContext(BaseModel):
    """Authentication context for a request."""

    user_id: str | None = Field(default=None, description="User identifier")
    api_key: str | None = Field(default=None, description="API key used")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    subscription_tier: str = Field(default="free", description="Subscription tier")
    rate_limit: int = Field(default=60, description="Rate limit per minute")
    authenticated: bool = Field(default=False, description="Whether authenticated")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class APIKeyAuth:
    """API Key authentication handler."""

    def __init__(self) -> None:
        self._api_keys: dict[str, dict[str, Any]] = {}
        self._load_api_keys()

    def _load_api_keys(self) -> None:
        """Load API keys from environment or database."""
        default_keys = {
            "test_api_key_001": {
                "user_id": "test_user_001",
                "roles": ["user"],
                "permissions": ["read:analysis", "read:graph", "read:quant"],
                "subscription_tier": "professional",
                "rate_limit": 100,
            },
            "test_api_key_002": {
                "user_id": "test_user_002",
                "roles": ["admin"],
                "permissions": ["read:*", "write:*"],
                "subscription_tier": "enterprise",
                "rate_limit": 1000,
            },
        }
        
        env_api_key = os.getenv("DATASERVICE_API_KEY")
        if env_api_key:
            default_keys[env_api_key] = {
                "user_id": "env_user",
                "roles": ["admin"],
                "permissions": ["read:*", "write:*"],
                "subscription_tier": "enterprise",
                "rate_limit": 1000,
            }
        
        self._api_keys = default_keys

    def validate(self, api_key: str) -> AuthContext | None:
        """Validate an API key and return auth context."""
        if api_key not in self._api_keys:
            return None
        
        key_info = self._api_keys[api_key]
        return AuthContext(
            user_id=key_info.get("user_id"),
            api_key=api_key,
            roles=key_info.get("roles", []),
            permissions=key_info.get("permissions", []),
            subscription_tier=key_info.get("subscription_tier", "free"),
            rate_limit=key_info.get("rate_limit", 60),
            authenticated=True,
        )

    def generate_key(self, user_id: str, **kwargs: Any) -> str:
        """Generate a new API key for a user."""
        key = f"sk_{secrets.token_hex(24)}"
        self._api_keys[key] = {
            "user_id": user_id,
            "roles": kwargs.get("roles", ["user"]),
            "permissions": kwargs.get("permissions", ["read:analysis"]),
            "subscription_tier": kwargs.get("subscription_tier", "free"),
            "rate_limit": kwargs.get("rate_limit", 60),
        }
        return key

    def revoke_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        if api_key in self._api_keys:
            del self._api_keys[api_key]
            return True
        return False


class JWTAuth:
    """JWT authentication handler."""

    def __init__(self) -> None:
        self._secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self._algorithm = "HS256"
        self._expire_minutes = 60

    def create_token(
        self,
        user_id: str,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT token for a user."""
        import jwt
        
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=self._expire_minutes)
        )
        
        payload = {
            "sub": user_id,
            "roles": roles or ["user"],
            "permissions": permissions or ["read:analysis"],
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def validate(self, token: str) -> AuthContext | None:
        """Validate a JWT token and return auth context."""
        import jwt
        
        try:
            payload = jwt.decode(
                token, self._secret_key, algorithms=[self._algorithm]
            )
            
            return AuthContext(
                user_id=payload.get("sub"),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                authenticated=True,
            )
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None


_api_key_auth = APIKeyAuth()
_jwt_auth = JWTAuth()


async def authenticate_request(
    request: Request,
    api_key: str | None = Depends(API_KEY_HEADER),
    bearer: HTTPAuthorizationCredentials | None = Depends(BEARER_SECURITY),
) -> AuthContext:
    """
    Authenticate a request using API key or JWT token.
    
    Returns an AuthContext with user information.
    """
    if api_key:
        context = _api_key_auth.validate(api_key)
        if context:
            return context
    
    if bearer:
        context = _jwt_auth.validate(bearer.credentials)
        if context:
            return context
    
    return AuthContext(
        authenticated=False,
        roles=["anonymous"],
        permissions=["read:public"],
    )


async def get_current_user(
    auth: AuthContext = Depends(authenticate_request),
) -> AuthContext:
    """Get the current authenticated user or raise an error."""
    if not auth.authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth


def require_permission(permission: str) -> Callable:
    """
    Decorator to require a specific permission.
    
    Usage:
        @require_permission("read:analysis")
        async def get_analysis_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, auth: AuthContext = None, **kwargs: Any) -> Any:
            if auth is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            
            if not auth.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required",
                )
            
            return await func(*args, auth=auth, **kwargs)
        return wrapper
    return decorator


def check_permission(auth: AuthContext, permission: str) -> bool:
    """Check if the auth context has a specific permission."""
    if "*" in auth.permissions:
        return True
    
    if permission in auth.permissions:
        return True
    
    resource, action = permission.split(":", 1) if ":" in permission else (permission, "*")
    
    for perm in auth.permissions:
        if perm == f"{resource}:*":
            return True
        if perm == f"*:{action}":
            return True
    
    return False
