"""
Strategy Registry.

Central registry for strategy management and discovery.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .base import BaseStrategy, StrategyType, StrategyMetadata

logger = logging.getLogger(__name__)


@dataclass
class StrategyInfo:
    """Information about a registered strategy."""
    
    strategy_id: str
    name: str
    description: str
    strategy_type: StrategyType
    version: str
    author: str
    tags: list[str]
    factor_ids: list[str]
    required_fields: list[str]
    min_data_points: int
    
    registered_at: datetime = field(default_factory=datetime.now)
    is_builtin: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type.value,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "factor_ids": self.factor_ids,
            "required_fields": self.required_fields,
            "min_data_points": self.min_data_points,
            "registered_at": self.registered_at.isoformat(),
            "is_builtin": self.is_builtin,
        }


class StrategyRegistry:
    """
    Central registry for strategy management.
    
    Features:
    - Strategy registration and discovery
    - Strategy lookup by ID, type, tags
    - Factor dependency checking
    - Strategy metadata management
    """
    
    def __init__(self) -> None:
        self._strategies: dict[str, type[BaseStrategy]] = {}
        self._info: dict[str, StrategyInfo] = {}
        self._factories: dict[str, Callable[[], BaseStrategy]] = {}
    
    def register(
        self,
        strategy_class: type[BaseStrategy],
        is_builtin: bool = False,
    ) -> None:
        """
        Register a strategy class.
        
        Args:
            strategy_class: The strategy class to register
            is_builtin: Whether this is a built-in strategy
        """
        instance = strategy_class()
        metadata = instance.metadata
        
        if metadata.strategy_id in self._strategies:
            logger.warning(f"Overwriting existing strategy: {metadata.strategy_id}")
        
        self._strategies[metadata.strategy_id] = strategy_class
        
        self._info[metadata.strategy_id] = StrategyInfo(
            strategy_id=metadata.strategy_id,
            name=metadata.name,
            description=metadata.description,
            strategy_type=metadata.strategy_type,
            version=metadata.version,
            author=metadata.author,
            tags=metadata.tags,
            factor_ids=metadata.factor_ids,
            required_fields=metadata.required_fields,
            min_data_points=metadata.min_data_points,
            is_builtin=is_builtin,
        )
        
        logger.debug(f"Registered strategy: {metadata.strategy_id}")
    
    def register_factory(
        self,
        strategy_id: str,
        factory: Callable[[], BaseStrategy],
        info: StrategyInfo,
    ) -> None:
        """
        Register a strategy factory function.
        
        Args:
            strategy_id: Strategy identifier
            factory: Factory function that creates strategy instances
            info: Strategy information
        """
        self._factories[strategy_id] = factory
        self._info[strategy_id] = info
    
    def unregister(self, strategy_id: str) -> bool:
        """
        Unregister a strategy.
        
        Args:
            strategy_id: Strategy identifier
        
        Returns:
            True if strategy was unregistered, False if not found
        """
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            del self._info[strategy_id]
            return True
        
        if strategy_id in self._factories:
            del self._factories[strategy_id]
            del self._info[strategy_id]
            return True
        
        return False
    
    def get(self, strategy_id: str) -> BaseStrategy | None:
        """
        Get a strategy instance by ID.
        
        Args:
            strategy_id: Strategy identifier
        
        Returns:
            Strategy instance or None if not found
        """
        if strategy_id in self._strategies:
            return self._strategies[strategy_id]()
        
        if strategy_id in self._factories:
            return self._factories[strategy_id]()
        
        return None
    
    def get_class(self, strategy_id: str) -> type[BaseStrategy] | None:
        """Get the strategy class by ID."""
        return self._strategies.get(strategy_id)
    
    def get_info(self, strategy_id: str) -> StrategyInfo | None:
        """Get strategy information by ID."""
        return self._info.get(strategy_id)
    
    def list_all(self) -> list[str]:
        """List all registered strategy IDs."""
        return list(set(self._strategies.keys()) | set(self._factories.keys()))
    
    def list_by_type(self, strategy_type: StrategyType) -> list[str]:
        """List strategies by type."""
        return [
            sid for sid, info in self._info.items()
            if info.strategy_type == strategy_type
        ]
    
    def list_by_tags(self, tags: list[str], match_all: bool = False) -> list[str]:
        """
        List strategies by tags.
        
        Args:
            tags: Tags to search for
            match_all: If True, all tags must match; if False, any tag matches
        
        Returns:
            List of matching strategy IDs
        """
        results = []
        for sid, info in self._info.items():
            if match_all:
                if all(tag in info.tags for tag in tags):
                    results.append(sid)
            else:
                if any(tag in info.tags for tag in tags):
                    results.append(sid)
        return results
    
    def search(self, query: str) -> list[str]:
        """
        Search strategies by name or description.
        
        Args:
            query: Search query
        
        Returns:
            List of matching strategy IDs
        """
        query_lower = query.lower()
        results = []
        
        for sid, info in self._info.items():
            if (query_lower in info.name.lower() or
                query_lower in info.description.lower() or
                query_lower in sid.lower()):
                results.append(sid)
        
        return results
    
    def get_summary(self) -> dict[str, Any]:
        """Get registry summary."""
        by_type: dict[str, int] = {}
        
        for info in self._info.values():
            t = info.strategy_type.value
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "total_strategies": len(self._info),
            "by_type": by_type,
            "builtin_count": sum(1 for i in self._info.values() if i.is_builtin),
        }


_global_registry: StrategyRegistry | None = None


def get_strategy_registry() -> StrategyRegistry:
    """Get the global strategy registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = StrategyRegistry()
    return _global_registry


def register_strategy(
    strategy_class: type[BaseStrategy] | None = None,
    *,
    is_builtin: bool = False,
) -> Callable[[type[BaseStrategy]], type[BaseStrategy]] | type[BaseStrategy]:
    """
    Decorator to register a strategy class.
    
    Usage:
        @register_strategy
        class MyStrategy(BaseStrategy):
            ...
        
        @register_strategy(is_builtin=True)
        class BuiltInStrategy(BaseStrategy):
            ...
    """
    def decorator(cls: type[BaseStrategy]) -> type[BaseStrategy]:
        registry = get_strategy_registry()
        registry.register(cls, is_builtin=is_builtin)
        return cls
    
    if strategy_class is not None:
        return decorator(strategy_class)
    
    return decorator
