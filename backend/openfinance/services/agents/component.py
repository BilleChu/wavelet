"""
Skill Component Structure.

Defines the standardized structure for skill components:
- SKILL.md (required): Skill definition and metadata
- /scripts (optional): Executable scripts
- /references (optional): Reference documents
- /assets (optional): Resource files
"""

import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SkillComponentType(str, Enum):
    """Types of skill components."""
    SKILL_MD = "skill_md"
    SCRIPT = "script"
    REFERENCE = "reference"
    ASSET = "asset"


class ScriptType(str, Enum):
    """Types of executable scripts."""
    PYTHON = "python"
    SHELL = "shell"
    JAVASCRIPT = "javascript"
    SQL = "sql"
    CUSTOM = "custom"


class SkillStatus(str, Enum):
    """Skill status."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class ScriptInfo:
    """Information about a script."""
    name: str
    path: Path
    script_type: ScriptType
    description: str = ""
    entry_point: str = "main"
    parameters: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 60.0
    requires_confirmation: bool = False


@dataclass
class ReferenceInfo:
    """Information about a reference document."""
    name: str
    path: Path
    content_type: str
    description: str = ""
    size_bytes: int = 0


@dataclass
class AssetInfo:
    """Information about an asset file."""
    name: str
    path: Path
    asset_type: str
    description: str = ""
    size_bytes: int = 0


class SkillDefinition(BaseModel):
    """Complete skill definition from SKILL.md."""
    
    skill_id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Skill display name")
    version: str = Field(default="1.0.0", description="Skill version")
    description: str = Field(..., description="Skill description")
    author: str | None = Field(default=None, description="Skill author")
    tags: list[str] = Field(default_factory=list, description="Search tags")
    category: str = Field(default="general", description="Skill category")
    
    status: SkillStatus = Field(default=SkillStatus.ACTIVE, description="Skill status")
    
    triggers: list[str] = Field(
        default_factory=list,
        description="Keywords or patterns that trigger this skill",
    )
    
    dependencies: list[str] = Field(
        default_factory=list,
        description="Required skill dependencies",
    )
    
    required_tools: list[str] = Field(
        default_factory=list,
        description="Required tools for this skill",
    )
    
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Skill parameters with defaults",
    )
    
    examples: list[dict[str, str]] = Field(
        default_factory=list,
        description="Usage examples",
    )
    
    scripts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Script configurations",
    )
    
    prompts: dict[str, str] = Field(
        default_factory=dict,
        description="Prompt templates",
    )
    
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
    
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp",
    )


class SkillComponent(BaseModel):
    """Complete skill component with all parts."""
    
    definition: SkillDefinition = Field(..., description="Skill definition")
    skill_path: Path = Field(..., description="Path to skill directory")
    
    scripts: list[ScriptInfo] = Field(
        default_factory=list,
        description="Available scripts",
    )
    references: list[ReferenceInfo] = Field(
        default_factory=list,
        description="Reference documents",
    )
    assets: list[AssetInfo] = Field(
        default_factory=list,
        description="Asset files",
    )
    
    is_valid: bool = Field(default=True, description="Whether skill is valid")
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Validation errors",
    )
    
    @property
    def skill_id(self) -> str:
        return self.definition.skill_id
    
    @property
    def name(self) -> str:
        return self.definition.name
    
    @property
    def has_scripts(self) -> bool:
        return len(self.scripts) > 0
    
    @property
    def has_references(self) -> bool:
        return len(self.references) > 0
    
    @property
    def has_assets(self) -> bool:
        return len(self.assets) > 0


class SkillLoader:
    """
    Loader for skill components from file system.
    
    Skill directory structure:
    ```
    skill_name/
    ├── SKILL.md          # Required: Skill definition
    ├── scripts/          # Optional: Executable scripts
    │   ├── main.py
    │   └── helper.sh
    ├── references/       # Optional: Reference documents
    │   └── guide.md
    └── assets/           # Optional: Resource files
        └── template.json
    ```
    """
    
    SKILL_FILE = "SKILL.md"
    SCRIPTS_DIR = "scripts"
    REFERENCES_DIR = "references"
    ASSETS_DIR = "assets"
    
    SCRIPT_EXTENSIONS = {
        ".py": ScriptType.PYTHON,
        ".sh": ScriptType.SHELL,
        ".bash": ScriptType.SHELL,
        ".js": ScriptType.JAVASCRIPT,
        ".mjs": ScriptType.JAVASCRIPT,
        ".sql": ScriptType.SQL,
    }
    
    def __init__(self, skills_root: Path | str):
        self.skills_root = Path(skills_root)
        self._cache: dict[str, SkillComponent] = {}
    
    def discover_skills(self) -> list[str]:
        """Discover all skill directories."""
        if not self.skills_root.exists():
            return []
        
        skill_ids = []
        for item in self.skills_root.iterdir():
            if item.is_dir():
                skill_file = item / self.SKILL_FILE
                if skill_file.exists():
                    skill_ids.append(item.name)
        
        return skill_ids
    
    def load_skill(self, skill_id: str) -> SkillComponent | None:
        """Load a skill component by ID."""
        if skill_id in self._cache:
            return self._cache[skill_id]
        
        skill_path = self.skills_root / skill_id
        if not skill_path.exists():
            return None
        
        skill_file = skill_path / self.SKILL_FILE
        if not skill_file.exists():
            logger.warning(f"SKILL.md not found for skill: {skill_id}")
            return None
        
        try:
            definition = self._parse_skill_md(skill_file)
            scripts = self._load_scripts(skill_path)
            references = self._load_references(skill_path)
            assets = self._load_assets(skill_path)
            
            component = SkillComponent(
                definition=definition,
                skill_path=skill_path,
                scripts=scripts,
                references=references,
                assets=assets,
                is_valid=True,
            )
            
            self._cache[skill_id] = component
            return component
            
        except Exception as e:
            logger.error(f"Failed to load skill {skill_id}: {e}")
            return SkillComponent(
                definition=SkillDefinition(
                    skill_id=skill_id,
                    name=skill_id,
                    description="Failed to load skill",
                ),
                skill_path=skill_path,
                is_valid=False,
                validation_errors=[str(e)],
            )
    
    def _parse_skill_md(self, skill_file: Path) -> SkillDefinition:
        """Parse SKILL.md file."""
        content = skill_file.read_text(encoding="utf-8")
        
        frontmatter = {}
        body = content
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1].strip()
                frontmatter = yaml.safe_load(frontmatter_text) or {}
                body = parts[2].strip()
        
        skill_id = frontmatter.get("id", skill_file.parent.name)
        
        definition = SkillDefinition(
            skill_id=skill_id,
            name=frontmatter.get("name", skill_id),
            version=frontmatter.get("version", "1.0.0"),
            description=frontmatter.get("description", body[:200] if body else ""),
            author=frontmatter.get("author"),
            tags=frontmatter.get("tags", []),
            category=frontmatter.get("category", "general"),
            status=SkillStatus(frontmatter.get("status", "active")),
            triggers=frontmatter.get("triggers", []),
            dependencies=frontmatter.get("dependencies", []),
            required_tools=frontmatter.get("required_tools", []),
            parameters=frontmatter.get("parameters", {}),
            examples=frontmatter.get("examples", []),
            scripts=frontmatter.get("scripts", []),
            prompts=frontmatter.get("prompts", {}),
            metadata=frontmatter.get("metadata", {}),
        )
        
        if body and not definition.description:
            definition.description = body
        
        return definition
    
    def _load_scripts(self, skill_path: Path) -> list[ScriptInfo]:
        """Load scripts from skill directory."""
        scripts_dir = skill_path / self.SCRIPTS_DIR
        if not scripts_dir.exists():
            return []
        
        scripts = []
        for file_path in scripts_dir.rglob("*"):
            if file_path.is_file():
                script_info = self._create_script_info(file_path, scripts_dir)
                if script_info:
                    scripts.append(script_info)
        
        return scripts
    
    def _create_script_info(
        self,
        file_path: Path,
        scripts_dir: Path,
    ) -> ScriptInfo | None:
        """Create ScriptInfo from file path."""
        ext = file_path.suffix.lower()
        script_type = self.SCRIPT_EXTENSIONS.get(ext, ScriptType.CUSTOM)
        
        relative_path = file_path.relative_to(scripts_dir)
        name = str(relative_path.with_suffix(""))
        
        return ScriptInfo(
            name=name,
            path=file_path,
            script_type=script_type,
            description=self._extract_script_description(file_path),
            timeout_seconds=60.0,
        )
    
    def _extract_script_description(self, file_path: Path) -> str:
        """Extract description from script file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            
            for line in lines[:10]:
                line = line.strip()
                if line.startswith('"""') or line.startswith("'''"):
                    end_idx = content.find(line[:3], 3)
                    if end_idx > 0:
                        return content[3:end_idx].strip()
                if line.startswith("#"):
                    return line[1:].strip()
            
            return ""
        except Exception:
            return ""
    
    def _load_references(self, skill_path: Path) -> list[ReferenceInfo]:
        """Load reference documents."""
        refs_dir = skill_path / self.REFERENCES_DIR
        if not refs_dir.exists():
            return []
        
        references = []
        for file_path in refs_dir.rglob("*"):
            if file_path.is_file():
                content_type = self._get_content_type(file_path)
                references.append(ReferenceInfo(
                    name=file_path.name,
                    path=file_path,
                    content_type=content_type,
                    size_bytes=file_path.stat().st_size,
                ))
        
        return references
    
    def _load_assets(self, skill_path: Path) -> list[AssetInfo]:
        """Load asset files."""
        assets_dir = skill_path / self.ASSETS_DIR
        if not assets_dir.exists():
            return []
        
        assets = []
        for file_path in assets_dir.rglob("*"):
            if file_path.is_file():
                asset_type = self._get_asset_type(file_path)
                assets.append(AssetInfo(
                    name=file_path.name,
                    path=file_path,
                    asset_type=asset_type,
                    size_bytes=file_path.stat().st_size,
                ))
        
        return assets
    
    def _get_content_type(self, file_path: Path) -> str:
        """Get content type for reference file."""
        ext = file_path.suffix.lower()
        content_types = {
            ".md": "markdown",
            ".txt": "text",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".pdf": "pdf",
            ".html": "html",
        }
        return content_types.get(ext, "unknown")
    
    def _get_asset_type(self, file_path: Path) -> str:
        """Get asset type for file."""
        ext = file_path.suffix.lower()
        asset_types = {
            ".json": "data",
            ".csv": "data",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".svg": "image",
            ".gif": "image",
            ".mp3": "audio",
            ".wav": "audio",
            ".mp4": "video",
        }
        return asset_types.get(ext, "file")
    
    def reload_skill(self, skill_id: str) -> SkillComponent | None:
        """Reload a skill from disk."""
        if skill_id in self._cache:
            del self._cache[skill_id]
        return self.load_skill(skill_id)
    
    def clear_cache(self) -> None:
        """Clear the skill cache."""
        self._cache.clear()


class ScriptExecutor:
    """Executor for skill scripts."""
    
    def __init__(self, timeout_seconds: float = 60.0):
        self.timeout_seconds = timeout_seconds
    
    def execute(
        self,
        script: ScriptInfo,
        parameters: dict[str, Any] | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute a script and return the result."""
        parameters = parameters or {}
        env = env or {}
        
        if script.script_type == ScriptType.PYTHON:
            return self._execute_python(script, parameters, env)
        elif script.script_type == ScriptType.SHELL:
            return self._execute_shell(script, parameters, env)
        else:
            return self._execute_generic(script, parameters, env)
    
    def _execute_python(
        self,
        script: ScriptInfo,
        parameters: dict[str, Any],
        env: dict[str, str],
    ) -> dict[str, Any]:
        """Execute a Python script."""
        import json
        import sys
        
        cmd = [
            sys.executable,
            str(script.path),
            json.dumps(parameters),
        ]
        
        return self._run_command(cmd, script.timeout_seconds, env)
    
    def _execute_shell(
        self,
        script: ScriptInfo,
        parameters: dict[str, Any],
        env: dict[str, str],
    ) -> dict[str, Any]:
        """Execute a shell script."""
        import json
        
        cmd = ["bash", str(script.path), json.dumps(parameters)]
        
        return self._run_command(cmd, script.timeout_seconds, env)
    
    def _execute_generic(
        self,
        script: ScriptInfo,
        parameters: dict[str, Any],
        env: dict[str, str],
    ) -> dict[str, Any]:
        """Execute a generic script."""
        import json
        
        cmd = [str(script.path), json.dumps(parameters)]
        
        return self._run_command(cmd, script.timeout_seconds, env)
    
    def _run_command(
        self,
        cmd: list[str],
        timeout: float,
        env: dict[str, str],
    ) -> dict[str, Any]:
        """Run a command and return the result."""
        import os
        
        full_env = os.environ.copy()
        full_env.update(env)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=full_env,
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Script execution timed out",
                "stdout": "",
                "stderr": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
            }
