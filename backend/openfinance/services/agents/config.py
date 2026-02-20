"""Configuration management for OpenFinance agents.

Provides configuration schema using Pydantic.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class AgentDefaults(BaseModel):
    """Default agent configuration."""
    workspace: str = "~/.openfinance/workspace"
    model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.7
    max_tool_iterations: int = 20


class AgentsConfig(BaseModel):
    """Agent configuration."""
    defaults: AgentDefaults = Field(default_factory=AgentDefaults)


class ToolsConfig(BaseModel):
    """Tools configuration."""
    restrict_to_workspace: bool = False
    exec_timeout: int = 60


class Config(BaseSettings):
    """Root configuration for OpenFinance agents."""
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    
    @property
    def workspace_path(self) -> Path:
        """Get expanded workspace path."""
        return Path(self.agents.defaults.workspace).expanduser()
    
    class Config:
        env_prefix = "OPENFINANCE_"
        env_nested_delimiter = "__"


def get_config() -> Config:
    """Get the global configuration instance."""
    return Config()
