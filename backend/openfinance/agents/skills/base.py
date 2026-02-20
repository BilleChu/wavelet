"""Base classes and metadata for skills.

Adapted from nanobot's skill system for OpenFinance agents.
"""

from dataclasses import dataclass, field
from typing import Any
from pathlib import Path


@dataclass
class SkillMetadata:
    """Metadata parsed from SKILL.md frontmatter."""
    name: str
    description: str
    homepage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    triggers: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    status: str = "active"
    
    def get_requires(self) -> dict[str, list[str]]:
        """Get requirements from metadata."""
        nanobot_meta = self.metadata.get("nanobot", {})
        if isinstance(nanobot_meta, dict):
            return nanobot_meta.get("requires", {})
        return {}
    
    def is_always_load(self) -> bool:
        """Check if skill should always be loaded."""
        nanobot_meta = self.metadata.get("nanobot", {})
        if isinstance(nanobot_meta, dict):
            return nanobot_meta.get("always", False) or self.metadata.get("always", False)
        return self.metadata.get("always", False)


@dataclass
class SkillInfo:
    """Information about a skill."""
    name: str
    path: Path
    source: str  # "builtin" or "workspace"
    metadata: SkillMetadata | None = None
    available: bool = True
    missing_requirements: list[str] = field(default_factory=list)
    
    def to_xml(self) -> str:
        """Convert to XML format for context."""
        def escape_xml(s: str) -> str:
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        lines = [f'  <skill available="{str(self.available).lower()}">']
        lines.append(f"    <name>{escape_xml(self.name)}</name>")
        
        if self.metadata:
            lines.append(f"    <description>{escape_xml(self.metadata.description)}</description>")
        
        lines.append(f"    <location>{self.path}</location>")
        
        if not self.available and self.missing_requirements:
            lines.append(f"    <requires>{escape_xml(', '.join(self.missing_requirements))}</requires>")
        
        lines.append("  </skill>")
        return "\n".join(lines)
