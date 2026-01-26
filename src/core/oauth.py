"""
OAuth 2.0 Authentication System for CursorBot

Provides:
- OAuth 2.0 authorization flow
- Token management
- Provider integration (GitHub, Google, etc.)
- Session security
"""

import asyncio
import base64
import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from urllib.parse import urlencode

from ..utils.logger import logger


class OAuthProvider(Enum):
    """Supported OAuth providers."""
    GITHUB = "github"
    GOOGLE = "google"
    DISCORD = "discord"
    TELEGRAM = "telegram"  # Login Widget
    CUSTOM = "custom"


@dataclass
class OAuthConfig:
    """Configuration for an OAuth provider."""
    provider: OAuthProvider
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str] = field(default_factory=list)
    authorize_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    
    def __post_init__(self):
        """Set default URLs based on provider."""
        if self.provider == OAuthProvider.GITHUB:
            self.authorize_url = self.authorize_url or "https://github.com/login/oauth/authorize"
            self.token_url = self.token_url or "https://github.com/login/oauth/access_token"
            self.userinfo_url = self.userinfo_url or "https://api.github.com/user"
            self.scopes = self.scopes or ["read:user", "user:email"]
            
        elif self.provider == OAuthProvider.GOOGLE:
            self.authorize_url = self.authorize_url or "https://accounts.google.com/o/oauth2/v2/auth"
            self.token_url = self.token_url or "https://oauth2.googleapis.com/token"
            self.userinfo_url = self.userinfo_url or "https://www.googleapis.com/oauth2/v2/userinfo"
            self.scopes = self.scopes or ["openid", "email", "profile"]
            
        elif self.provider == OAuthProvider.DISCORD:
            self.authorize_url = self.authorize_url or "https://discord.com/api/oauth2/authorize"
            self.token_url = self.token_url or "https://discord.com/api/oauth2/token"
            self.userinfo_url = self.userinfo_url or "https://discord.com/api/users/@me"
            self.scopes = self.scopes or ["identify", "email"]


@dataclass
class OAuthToken:
    """OAuth access token."""
    access_token: str
    token_type: str = "Bearer"
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    scope: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_in:
            return False
        expires_at = self.created_at + timedelta(seconds=self.expires_in)
        return datetime.now() >= expires_at
    
    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
            "is_expired": self.is_expired,
        }


@dataclass
class OAuthUser:
    """OAuth user information."""
    id: str
    provider: OAuthProvider
    username: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    raw_data: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider.value,
            "username": self.username,
            "email": self.email,
            "avatar_url": self.avatar_url,
        }


@dataclass
class OAuthState:
    """OAuth authorization state for CSRF protection."""
    state: str
    created_at: datetime = field(default_factory=datetime.now)
    redirect_to: Optional[str] = None
    user_id: Optional[int] = None
    expires_in: int = 600  # 10 minutes
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() >= self.created_at + timedelta(seconds=self.expires_in)


class OAuthClient:
    """
    OAuth 2.0 client for a specific provider.
    """
    
    def __init__(self, config: OAuthConfig):
        self.config = config
    
    def generate_state(self, redirect_to: str = None, user_id: int = None) -> OAuthState:
        """Generate a state token for CSRF protection."""
        state = secrets.token_urlsafe(32)
        return OAuthState(
            state=state,
            redirect_to=redirect_to,
            user_id=user_id,
        )
    
    def get_authorize_url(self, state: str) -> str:
        """
        Get the authorization URL to redirect the user to.
        
        Args:
            state: State token for CSRF protection
        
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
            "response_type": "code",
        }
        
        # Provider-specific params
        if self.config.provider == OAuthProvider.GOOGLE:
            params["access_type"] = "offline"
            params["prompt"] = "consent"
        
        return f"{self.config.authorize_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> OAuthToken:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from callback
        
        Returns:
            OAuthToken
        """
        import httpx
        
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
        }
        
        headers = {"Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data=data,
                headers=headers,
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                raise ValueError(f"Token exchange failed: {response.status_code}")
            
            token_data = response.json()
            
            return OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                refresh_token=token_data.get("refresh_token"),
                expires_in=token_data.get("expires_in"),
                scope=token_data.get("scope"),
            )
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: Refresh token
        
        Returns:
            New OAuthToken
        """
        import httpx
        
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
            
            if response.status_code != 200:
                raise ValueError(f"Token refresh failed: {response.status_code}")
            
            token_data = response.json()
            
            return OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                refresh_token=token_data.get("refresh_token", refresh_token),
                expires_in=token_data.get("expires_in"),
                scope=token_data.get("scope"),
            )
    
    async def get_user_info(self, token: OAuthToken) -> OAuthUser:
        """
        Get user information using the access token.
        
        Args:
            token: OAuth access token
        
        Returns:
            OAuthUser
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_url,
                headers={
                    "Authorization": f"{token.token_type} {token.access_token}",
                    "Accept": "application/json",
                },
            )
            
            if response.status_code != 200:
                raise ValueError(f"User info request failed: {response.status_code}")
            
            data = response.json()
            
            # Parse user data based on provider
            return self._parse_user_data(data)
    
    def _parse_user_data(self, data: dict) -> OAuthUser:
        """Parse provider-specific user data."""
        if self.config.provider == OAuthProvider.GITHUB:
            return OAuthUser(
                id=str(data["id"]),
                provider=self.config.provider,
                username=data.get("login"),
                email=data.get("email"),
                avatar_url=data.get("avatar_url"),
                raw_data=data,
            )
        
        elif self.config.provider == OAuthProvider.GOOGLE:
            return OAuthUser(
                id=data["id"],
                provider=self.config.provider,
                username=data.get("name"),
                email=data.get("email"),
                avatar_url=data.get("picture"),
                raw_data=data,
            )
        
        elif self.config.provider == OAuthProvider.DISCORD:
            avatar = None
            if data.get("avatar"):
                avatar = f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.png"
            
            return OAuthUser(
                id=data["id"],
                provider=self.config.provider,
                username=data.get("username"),
                email=data.get("email"),
                avatar_url=avatar,
                raw_data=data,
            )
        
        else:
            return OAuthUser(
                id=str(data.get("id", data.get("sub", "unknown"))),
                provider=self.config.provider,
                username=data.get("username") or data.get("name"),
                email=data.get("email"),
                raw_data=data,
            )


# ============================================
# API Token Management
# ============================================

@dataclass
class APIToken:
    """API token for bot authentication."""
    token: str
    name: str
    user_id: int
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    scopes: list[str] = field(default_factory=list)
    last_used: Optional[datetime] = None
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "scopes": self.scopes,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_expired": self.is_expired,
        }


class APITokenManager:
    """Manages API tokens for authentication."""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_hex(32)
        self._tokens: dict[str, APIToken] = {}
    
    def generate_token(
        self,
        name: str,
        user_id: int,
        scopes: list[str] = None,
        expires_in_days: int = None,
    ) -> APIToken:
        """
        Generate a new API token.
        
        Args:
            name: Token name/description
            user_id: User ID
            scopes: Token scopes
            expires_in_days: Expiration in days
        
        Returns:
            APIToken
        """
        # Generate secure token
        token_bytes = secrets.token_bytes(32)
        token = base64.urlsafe_b64encode(token_bytes).decode("utf-8").rstrip("=")
        
        # Add signature for validation
        signature = hmac.new(
            self.secret_key.encode(),
            token.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        
        full_token = f"cb_{token}_{signature}"
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        api_token = APIToken(
            token=full_token,
            name=name,
            user_id=user_id,
            scopes=scopes or ["read", "write"],
            expires_at=expires_at,
        )
        
        self._tokens[full_token] = api_token
        return api_token
    
    def validate_token(self, token: str) -> Optional[APIToken]:
        """
        Validate an API token.
        
        Args:
            token: Token string
        
        Returns:
            APIToken if valid, None otherwise
        """
        # Check format
        if not token.startswith("cb_"):
            return None
        
        api_token = self._tokens.get(token)
        if not api_token:
            return None
        
        if api_token.is_expired:
            return None
        
        # Update last used
        api_token.last_used = datetime.now()
        
        return api_token
    
    def revoke_token(self, token: str) -> bool:
        """Revoke an API token."""
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False
    
    def list_tokens(self, user_id: int = None) -> list[dict]:
        """List tokens, optionally filtered by user."""
        tokens = self._tokens.values()
        if user_id:
            tokens = [t for t in tokens if t.user_id == user_id]
        return [t.to_dict() for t in tokens]


# ============================================
# OAuth Manager
# ============================================

class OAuthManager:
    """
    Manages OAuth authentication across multiple providers.
    """
    
    def __init__(self):
        self._clients: dict[OAuthProvider, OAuthClient] = {}
        self._states: dict[str, OAuthState] = {}
        self._users: dict[str, OAuthUser] = {}  # provider_id -> user
        self._tokens: dict[str, OAuthToken] = {}  # user_key -> token
    
    def register_provider(self, config: OAuthConfig) -> None:
        """Register an OAuth provider."""
        self._clients[config.provider] = OAuthClient(config)
        logger.info(f"Registered OAuth provider: {config.provider.value}")
    
    def get_client(self, provider: OAuthProvider) -> Optional[OAuthClient]:
        """Get OAuth client for a provider."""
        return self._clients.get(provider)
    
    def start_auth(
        self,
        provider: OAuthProvider,
        redirect_to: str = None,
        user_id: int = None,
    ) -> str:
        """
        Start OAuth authorization flow.
        
        Args:
            provider: OAuth provider
            redirect_to: URL to redirect after auth
            user_id: Optional user ID to associate
        
        Returns:
            Authorization URL
        """
        client = self._clients.get(provider)
        if not client:
            raise ValueError(f"Provider not registered: {provider}")
        
        # Generate state
        state = client.generate_state(redirect_to, user_id)
        self._states[state.state] = state
        
        # Cleanup old states
        self._cleanup_expired_states()
        
        return client.get_authorize_url(state.state)
    
    async def handle_callback(
        self,
        provider: OAuthProvider,
        code: str,
        state: str,
    ) -> tuple[OAuthUser, OAuthToken, OAuthState]:
        """
        Handle OAuth callback.
        
        Args:
            provider: OAuth provider
            code: Authorization code
            state: State token
        
        Returns:
            Tuple of (OAuthUser, OAuthToken, OAuthState)
        """
        # Validate state
        oauth_state = self._states.get(state)
        if not oauth_state:
            raise ValueError("Invalid state token")
        
        if oauth_state.is_expired:
            del self._states[state]
            raise ValueError("State token expired")
        
        # Get client
        client = self._clients.get(provider)
        if not client:
            raise ValueError(f"Provider not registered: {provider}")
        
        # Exchange code for token
        token = await client.exchange_code(code)
        
        # Get user info
        user = await client.get_user_info(token)
        
        # Store user and token
        user_key = f"{provider.value}_{user.id}"
        self._users[user_key] = user
        self._tokens[user_key] = token
        
        # Remove used state
        del self._states[state]
        
        logger.info(f"OAuth login successful: {user.username} via {provider.value}")
        
        return user, token, oauth_state
    
    def get_user(self, provider: OAuthProvider, provider_id: str) -> Optional[OAuthUser]:
        """Get cached user by provider and ID."""
        return self._users.get(f"{provider.value}_{provider_id}")
    
    def _cleanup_expired_states(self) -> None:
        """Remove expired states."""
        expired = [s for s, state in self._states.items() if state.is_expired]
        for s in expired:
            del self._states[s]


# ============================================
# Global Instances
# ============================================

_oauth_manager: Optional[OAuthManager] = None
_api_token_manager: Optional[APITokenManager] = None


def get_oauth_manager() -> OAuthManager:
    """Get the global OAuth manager instance."""
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthManager()
    return _oauth_manager


def get_api_token_manager(secret_key: str = None) -> APITokenManager:
    """Get the global API token manager instance."""
    global _api_token_manager
    if _api_token_manager is None:
        _api_token_manager = APITokenManager(secret_key)
    return _api_token_manager


__all__ = [
    "OAuthProvider",
    "OAuthConfig",
    "OAuthToken",
    "OAuthUser",
    "OAuthState",
    "OAuthClient",
    "OAuthManager",
    "APIToken",
    "APITokenManager",
    "get_oauth_manager",
    "get_api_token_manager",
]
