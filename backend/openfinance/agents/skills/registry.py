"""Skill registry for managing skill instances.

Provides a central registry for skill management.
"""

from pathlib import Path
from typing import Any, Callable

import logging

logger = logging.getLogger(__name__)

from openfinance.agents.skills.base import SkillInfo, SkillMetadata
from openfinance.agents.skills.loader import SkillsLoader


class SkillRegistry:
    """
    Registry for managing skills.
    
    Allows dynamic registration, discovery, and execution of skills.
    """
    
    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.home() / ".openfinance" / "workspace"
        self.loader = SkillsLoader(self.workspace)
        self._handlers: dict[str, Callable] = {}
    
    def register_handler(self, skill_name: str, handler: Callable) -> None:
        """Register a handler function for a skill."""
        self._handlers[skill_name] = handler
        logger.debug(f"Registered skill handler: {skill_name}")
    
    def unregister_handler(self, skill_name: str) -> bool:
        """Unregister a skill handler."""
        if skill_name in self._handlers:
            del self._handlers[skill_name]
            return True
        return False
    
    def get_handler(self, skill_name: str) -> Callable | None:
        """Get a skill handler by name."""
        return self._handlers.get(skill_name)
    
    def list_skills(self, filter_unavailable: bool = True) -> list[SkillInfo]:
        """List all available skills."""
        return self.loader.list_skills(filter_unavailable=filter_unavailable)
    
    def get_skill(self, name: str) -> SkillInfo | None:
        """Get skill info by name."""
        for skill in self.loader.list_skills(filter_unavailable=False):
            if skill.name == name:
                return skill
        return None
    
    def load_skill_content(self, name: str) -> str | None:
        """Load the full content of a skill."""
        return self.loader.load_skill(name)
    
    def build_skills_summary(self) -> str:
        """Build XML summary of all skills for context."""
        return self.loader.build_skills_summary()
    
    def get_always_skills(self) -> list[str]:
        """Get skills that should always be loaded."""
        return self.loader.get_always_skills()
    
    def load_always_skills_content(self) -> str:
        """Load content of always-load skills."""
        always_skills = self.get_always_skills()
        return self.loader.load_skills_for_context(always_skills)
    
    def has_skill(self, name: str) -> bool:
        """Check if a skill exists."""
        return self.get_skill(name) is not None
    
    def get_skill_names(self) -> list[str]:
        """Get list of all skill names."""
        return [s.name for s in self.loader.list_skills(filter_unavailable=False)]
    
    async def execute_skill(
        self,
        skill_name: str,
        context: dict[str, Any],
        **kwargs: Any
    ) -> Any:
        """
        Execute a skill handler.
        
        Args:
            skill_name: Name of the skill to execute.
            context: Execution context.
            **kwargs: Additional arguments for the handler.
        
        Returns:
            Handler result.
        
        Raises:
            ValueError: If skill handler not found.
        """
        handler = self._handlers.get(skill_name)
        if not handler:
            raise ValueError(f"No handler registered for skill: {skill_name}")
        
        import asyncio
        result = handler(context, **kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        
        return result
    
    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        skills = self.loader.list_skills(filter_unavailable=False)
        return {
            "total_skills": len(skills),
            "available_skills": sum(1 for s in skills if s.available),
            "registered_handlers": len(self._handlers),
            "builtin_skills": sum(1 for s in skills if s.source == "builtin"),
            "workspace_skills": sum(1 for s in skills if s.source == "workspace"),
        }
