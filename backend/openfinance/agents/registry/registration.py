"""
Skill Registry for OpenFinance.

Provides dynamic skill discovery and registration.
"""

import importlib
import inspect
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from openfinance.domain.models.skill import (
    SkillMetadata,
    SkillCapability,
    SkillConfig,
)

logger = logging.getLogger(__name__)


class DiscoveryResult(BaseModel):
    """Result of skill discovery."""

    discovered_count: int = Field(..., description="Number of skills discovered")
    registered_count: int = Field(..., description="Number of skills registered")
    failed_count: int = Field(..., description="Number of failures")
    details: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Discovery details",
    )


class SkillRegistry:
    """Registry for skill management.

    Provides:
    - Skill registration and unregistration
    - Skill lookup by ID, name, or capability
    - Metadata management
    - Dependency resolution
    """

    def __init__(self) -> None:
        self._skills: dict[str, SkillMetadata] = {}
        self._handlers: dict[str, Callable] = {}
        self._configs: dict[str, SkillConfig] = {}
        self._capability_index: dict[str, set[str]] = {}
        self._tag_index: dict[str, set[str]] = {}

    def register(
        self,
        metadata: SkillMetadata,
        handler: Callable,
        config: SkillConfig | None = None,
    ) -> bool:
        """Register a skill with its handler."""
        skill_id = metadata.skill_id

        if skill_id in self._skills:
            logger.warning(f"Skill already registered: {skill_id}")
            return False

        self._skills[skill_id] = metadata
        self._handlers[skill_id] = handler
        if config:
            self._configs[skill_id] = config

        for capability in metadata.capabilities:
            cap_name = capability.name
            if cap_name not in self._capability_index:
                self._capability_index[cap_name] = set()
            self._capability_index[cap_name].add(skill_id)

        for tag in metadata.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(skill_id)

        logger.info(f"Registered skill: {skill_id}")
        return True

    def unregister(self, skill_id: str) -> bool:
        """Unregister a skill."""
        if skill_id not in self._skills:
            return False

        metadata = self._skills[skill_id]

        for capability in metadata.capabilities:
            cap_name = capability.name
            if cap_name in self._capability_index:
                self._capability_index[cap_name].discard(skill_id)

        for tag in metadata.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(skill_id)

        del self._skills[skill_id]
        del self._handlers[skill_id]
        if skill_id in self._configs:
            del self._configs[skill_id]

        logger.info(f"Unregistered skill: {skill_id}")
        return True

    def get(self, skill_id: str) -> SkillMetadata | None:
        """Get skill metadata by ID."""
        return self._skills.get(skill_id)

    def get_handler(self, skill_id: str) -> Callable | None:
        """Get skill handler by ID."""
        return self._handlers.get(skill_id)

    def get_config(self, skill_id: str) -> SkillConfig | None:
        """Get skill config by ID."""
        return self._configs.get(skill_id)

    def find_by_name(self, name: str) -> list[SkillMetadata]:
        """Find skills by name (partial match)."""
        return [
            m for m in self._skills.values()
            if name.lower() in m.name.lower()
        ]

    def find_by_capability(self, capability: str) -> list[SkillMetadata]:
        """Find skills by capability name."""
        skill_ids = self._capability_index.get(capability, set())
        return [self._skills[sid] for sid in skill_ids if sid in self._skills]

    def find_by_tag(self, tag: str) -> list[SkillMetadata]:
        """Find skills by tag."""
        skill_ids = self._tag_index.get(tag, set())
        return [self._skills[sid] for sid in skill_ids if sid in self._skills]

    def find_by_category(self, category: str) -> list[SkillMetadata]:
        """Find skills by category."""
        return [
            m for m in self._skills.values()
            if m.category == category
        ]

    def list_all(self) -> list[SkillMetadata]:
        """List all registered skills."""
        return list(self._skills.values())

    def get_dependencies(self, skill_id: str) -> list[str]:
        """Get dependencies for a skill."""
        metadata = self._skills.get(skill_id)
        return metadata.dependencies if metadata else []

    def check_dependencies(self, skill_id: str) -> tuple[bool, list[str]]:
        """Check if all dependencies are satisfied."""
        metadata = self._skills.get(skill_id)
        if not metadata:
            return False, []

        missing = []
        for dep_id in metadata.dependencies:
            if dep_id not in self._skills:
                missing.append(dep_id)

        return len(missing) == 0, missing

    def check_conflicts(self, skill_id: str) -> list[str]:
        """Check for conflicting skills."""
        metadata = self._skills.get(skill_id)
        if not metadata:
            return []

        conflicts = []
        for conflict_id in metadata.conflicts:
            if conflict_id in self._skills:
                conflicts.append(conflict_id)

        return conflicts

    def update_metadata(
        self,
        skill_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update skill metadata."""
        if skill_id not in self._skills:
            return False

        metadata = self._skills[skill_id]
        
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        metadata.updated_at = datetime.now()
        return True

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        categories: dict[str, int] = {}
        for metadata in self._skills.values():
            categories[metadata.category] = categories.get(metadata.category, 0) + 1

        return {
            "total_skills": len(self._skills),
            "total_capabilities": len(self._capability_index),
            "total_tags": len(self._tag_index),
            "categories": categories,
        }


class SkillDiscovery:
    """Discovers skills from modules and directories.

    Provides:
    - Module scanning
    - Decorator-based registration
    - Automatic validation
    """

    SKILL_DECORATOR = "__openfinance_skill__"

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry
        self._discovered_modules: set[str] = set()

    def discover_from_module(self, module_path: str) -> DiscoveryResult:
        """Discover skills from a Python module."""
        result = DiscoveryResult(
            discovered_count=0,
            registered_count=0,
            failed_count=0,
        )

        try:
            module = importlib.import_module(module_path)
            self._discovered_modules.add(module_path)

            for name, obj in inspect.getmembers(module):
                if hasattr(obj, self.SKILL_DECORATOR):
                    result.discovered_count += 1
                    
                    skill_info = getattr(obj, self.SKILL_DECORATOR)
                    
                    try:
                        metadata = SkillMetadata(**skill_info.get("metadata", {}))
                        config = SkillConfig(**skill_info.get("config", {}))
                        
                        if self.registry.register(metadata, obj, config):
                            result.registered_count += 1
                            result.details.append({
                                "skill_id": metadata.skill_id,
                                "status": "registered",
                            })
                        else:
                            result.failed_count += 1
                            result.details.append({
                                "skill_id": metadata.skill_id,
                                "status": "failed",
                                "error": "Registration failed",
                            })

                    except Exception as e:
                        result.failed_count += 1
                        result.details.append({
                            "name": name,
                            "status": "failed",
                            "error": str(e),
                        })

        except Exception as e:
            logger.exception(f"Failed to discover from module: {module_path}")
            result.details.append({
                "module": module_path,
                "status": "failed",
                "error": str(e),
            })

        return result

    def discover_from_directory(
        self,
        directory: str,
        recursive: bool = True,
    ) -> DiscoveryResult:
        """Discover skills from a directory."""
        result = DiscoveryResult(
            discovered_count=0,
            registered_count=0,
            failed_count=0,
        )

        path = Path(directory)
        if not path.exists():
            return result

        pattern = "**/*.py" if recursive else "*.py"

        for file_path in path.glob(pattern):
            if file_path.name.startswith("_"):
                continue

            module_path = self._path_to_module(file_path)
            module_result = self.discover_from_module(module_path)

            result.discovered_count += module_result.discovered_count
            result.registered_count += module_result.registered_count
            result.failed_count += module_result.failed_count
            result.details.extend(module_result.details)

        return result

    def _path_to_module(self, file_path: Path) -> str:
        """Convert file path to module path."""
        parts = list(file_path.parts)
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        return ".".join(parts)


def skill(
    metadata: dict[str, Any],
    config: dict[str, Any] | None = None,
):
    """Decorator to mark a function as a skill.

    Usage:
        @skill(
            metadata={
                "skill_id": "stock_analysis",
                "name": "Stock Analysis",
                "category": "analysis",
            },
            config={"timeout_seconds": 30}
        )
        async def analyze_stock(query: str) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        setattr(func, SkillDiscovery.SKILL_DECORATOR, {
            "metadata": metadata,
            "config": config or {},
        })
        return func

    return decorator
