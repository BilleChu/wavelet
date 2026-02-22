"""
Source Types - Type definitions for data sources.

Provides enums and type definitions for data source management.
"""

from enum import Enum


class SourceType(str, Enum):
    """Types of data sources."""
    
    API = "api"
    DATABASE = "database"
    FILE = "file"
    STREAM = "stream"
    WEB_SOCKET = "websocket"


class SourceStatus(str, Enum):
    """Status of a data source."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class AuthType(str, Enum):
    """Authentication types for data sources."""
    
    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    BASIC = "basic"
    BEARER = "bearer"
    CUSTOM = "custom"
