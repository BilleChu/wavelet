"""
Data Provider Module for OpenFinance.

Provides data source abstraction and MCP-based service architecture.

Components:
- data_provider: Data source abstraction (Tushare, Akshare, Mock)
- mcp: Microservice framework (server, registry)
"""

from openfinance.datacenter.provider.mcp.server import MCPService, MCPServerConfig
from openfinance.datacenter.provider.mcp.registry import ServiceRegistry
from openfinance.datacenter.provider.data_provider import (
    BaseDataProvider,
    DataProviderError,
    create_data_provider,
)

__all__ = [
    "MCPService",
    "MCPServerConfig",
    "ServiceRegistry",
    "BaseDataProvider",
    "DataProviderError",
    "create_data_provider",
]
