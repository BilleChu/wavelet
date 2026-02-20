"""Skills loader for agent capabilities.

Adapted from nanobot's skill system for OpenFinance agents.
Skills are markdown files (SKILL.md) that teach the agent how to use
specific tools or perform certain tasks.
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

import logging

logger = logging.getLogger(__name__)

from openfinance.agents.skills.base import SkillMetadata, SkillInfo

BUILTIN_SKILLS_DIR = Path(__file__).parent / "builtin"


class SkillsLoader:
    """
    Loader for agent skills.
    
    Skills are markdown files (SKILL.md) that teach the agent how to use
    specific tools or perform certain tasks.
    """
    
    def __init__(self, workspace: Path, builtin_skills_dir: Path | None = None):
        self.workspace = workspace
        self.workspace_skills = workspace / "skills"
        self.builtin_skills = builtin_skills_dir or BUILTIN_SKILLS_DIR
    
    def list_skills(self, filter_unavailable: bool = True) -> list[SkillInfo]:
        """
        List all available skills.
        
        Args:
            filter_unavailable: If True, filter out skills with unmet requirements.
        
        Returns:
            List of SkillInfo objects.
        """
        skills = []
        
        if self.workspace_skills.exists():
            for skill_dir in self.workspace_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        metadata = self._parse_skill_file(skill_file)
                        info = SkillInfo(
                            name=skill_dir.name,
                            path=skill_file,
                            source="workspace",
                            metadata=metadata,
                        )
                        info.available = self._check_requirements(metadata)
                        info.missing_requirements = self._get_missing_requirements(metadata)
                        skills.append(info)
        
        if self.builtin_skills and self.builtin_skills.exists():
            for skill_dir in self.builtin_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists() and not any(s.name == skill_dir.name for s in skills):
                        metadata = self._parse_skill_file(skill_file)
                        info = SkillInfo(
                            name=skill_dir.name,
                            path=skill_file,
                            source="builtin",
                            metadata=metadata,
                        )
                        info.available = self._check_requirements(metadata)
                        info.missing_requirements = self._get_missing_requirements(metadata)
                        skills.append(info)
        
        if filter_unavailable:
            return [s for s in skills if s.available]
        return skills
    
    def load_skill(self, name: str) -> str | None:
        """
        Load a skill by name.
        
        Args:
            name: Skill name (directory name).
        
        Returns:
            Skill content or None if not found.
        """
        workspace_skill = self.workspace_skills / name / "SKILL.md"
        if workspace_skill.exists():
            return workspace_skill.read_text(encoding="utf-8")
        
        if self.builtin_skills:
            builtin_skill = self.builtin_skills / name / "SKILL.md"
            if builtin_skill.exists():
                return builtin_skill.read_text(encoding="utf-8")
        
        return None
    
    def load_skills_for_context(self, skill_names: list[str]) -> str:
        """
        Load specific skills for inclusion in agent context.
        
        Args:
            skill_names: List of skill names to load.
        
        Returns:
            Formatted skills content.
        """
        parts = []
        for name in skill_names:
            content = self.load_skill(name)
            if content:
                content = self._strip_frontmatter(content)
                parts.append(f"### Skill: {name}\n\n{content}")
        
        return "\n\n---\n\n".join(parts) if parts else ""
    
    def build_skills_summary(self) -> str:
        """
        Build a summary of all skills (name, description, path, availability).
        
        This is used for progressive loading - the agent can read the full
        skill content using read_file when needed.
        
        Returns:
            XML-formatted skills summary.
        """
        all_skills = self.list_skills(filter_unavailable=False)
        if not all_skills:
            return ""
        
        lines = ["<skills>"]
        for skill in all_skills:
            lines.append(skill.to_xml())
        lines.append("</skills>")
        
        return "\n".join(lines)
    
    def get_always_skills(self) -> list[str]:
        """Get skills marked as always=true that meet requirements."""
        result = []
        for skill in self.list_skills(filter_unavailable=True):
            if skill.metadata and skill.metadata.is_always_load():
                result.append(skill.name)
        return result
    
    def _parse_skill_file(self, path: Path) -> SkillMetadata | None:
        """Parse a SKILL.md file and extract metadata."""
        content = path.read_text(encoding="utf-8")
        return self._parse_frontmatter(content)
    
    def _parse_frontmatter(self, content: str) -> SkillMetadata | None:
        """Parse YAML frontmatter from markdown content."""
        if not content.startswith("---"):
            return None
        
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return None
        
        frontmatter_text = match.group(1)
        metadata: dict[str, Any] = {}
        current_list_key: str | None = None
        current_list_values: list[str] = []
        
        for line in frontmatter_text.split("\n"):
            stripped = line.strip()
            
            if stripped.startswith("- ") and current_list_key:
                value = stripped[2:].strip().strip('"\'')
                current_list_values.append(value)
                continue
            
            if current_list_key and current_list_values:
                metadata[current_list_key] = current_list_values
                current_list_key = None
                current_list_values = []
            
            if ":" in line and not line.startswith(" "):
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                
                if value == "" and key in ("tags", "triggers"):
                    current_list_key = key
                    current_list_values = []
                elif key == "metadata":
                    try:
                        metadata[key] = json.loads(value)
                    except json.JSONDecodeError:
                        metadata[key] = {}
                else:
                    metadata[key] = value
        
        if current_list_key and current_list_values:
            metadata[current_list_key] = current_list_values
        
        name = metadata.get("name", "")
        description = metadata.get("description", "")
        
        if not name:
            return None
        
        return SkillMetadata(
            name=name,
            description=description,
            homepage=metadata.get("homepage"),
            metadata=metadata,
            triggers=metadata.get("triggers", []),
            version=metadata.get("version", "1.0.0"),
            author=metadata.get("author"),
            category=metadata.get("category"),
            tags=metadata.get("tags", []),
            status=metadata.get("status", "active"),
        )
    
    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter from markdown content."""
        if content.startswith("---"):
            match = re.match(r"^---\n.*?\n---\n", content, re.DOTALL)
            if match:
                return content[match.end():].strip()
        return content
    
    def _check_requirements(self, metadata: SkillMetadata | None) -> bool:
        """Check if skill requirements are met (bins, env vars)."""
        if not metadata:
            return True
        
        requires = metadata.get_requires()
        for b in requires.get("bins", []):
            if not shutil.which(b):
                return False
        for env in requires.get("env", []):
            if not os.environ.get(env):
                return False
        return True
    
    def _get_missing_requirements(self, metadata: SkillMetadata | None) -> list[str]:
        """Get a description of missing requirements."""
        if not metadata:
            return []
        
        missing = []
        requires = metadata.get_requires()
        for b in requires.get("bins", []):
            if not shutil.which(b):
                missing.append(f"CLI: {b}")
        for env in requires.get("env", []):
            if not os.environ.get(env):
                missing.append(f"ENV: {env}")
        return missing
