"""
Skills API Routes for OpenFinance.
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openfinance.agents.registry.registration import SkillRegistry
from openfinance.agents.lifecycle.manager import SkillLifecycleManager
from openfinance.agents.component import SkillLoader, ScriptExecutor
from openfinance.agents.skills.loader import SkillsLoader, BUILTIN_SKILLS_DIR
from openfinance.domain.models.skill import SkillMetadata, SkillConfig

logger = logging.getLogger(__name__)

router = APIRouter()

registry = SkillRegistry()
lifecycle_manager = SkillLifecycleManager()

SKILLS_ROOT = Path(__file__).parent.parent.parent / "agents" / "skills" / "builtin"
SKILLS_WORKSPACE = Path.home() / ".openfinance" / "workspace"
_skill_loader = SkillLoader(SKILLS_ROOT)
_script_executor = ScriptExecutor()
_skills_loader = SkillsLoader(SKILLS_WORKSPACE, BUILTIN_SKILLS_DIR)


class ExecuteScriptRequest(BaseModel):
    """Request to execute a skill script."""
    skill_id: str = Field(..., description="Skill ID")
    script_name: str = Field(..., description="Script name")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Script parameters")


class InstallSkillRequest(BaseModel):
    """Request to install a skill."""
    skill_id: str = Field(..., description="Skill ID to install")
    source: str = Field(default="local", description="Installation source")


@router.get("/skills")
async def list_skills(category: str | None = None) -> dict[str, Any]:
    """List all registered skills."""
    skills = _skills_loader.list_skills(filter_unavailable=False)

    return {
        "skills": [
            {
                "skill_id": s.name,
                "name": s.metadata.name if s.metadata else s.name,
                "version": s.metadata.version if s.metadata else "1.0.0",
                "description": s.metadata.description if s.metadata else "",
                "category": s.metadata.category if s.metadata else "",
                "tags": s.metadata.tags if s.metadata else [],
                "triggers": s.metadata.triggers if s.metadata else [],
                "available": s.available,
                "source": s.source,
            }
            for s in skills
        ],
        "total": len(skills),
    }


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str) -> dict[str, Any]:
    """Get details of a specific skill."""
    metadata = registry.get(skill_id)
    if not metadata:
        component = _skill_loader.load_skill(skill_id)
        if component:
            return {
                "skill_id": component.skill_id,
                "name": component.name,
                "version": component.definition.version,
                "description": component.definition.description,
                "author": component.definition.author,
                "category": component.definition.category,
                "tags": component.definition.tags or [],
                "status": component.definition.status or "active",
                "has_scripts": len(component.scripts) > 0,
                "has_references": len(component.references) > 0,
                "definition": component.definition.model_dump(),
                "scripts": [
                    {
                        "name": s.name,
                        "type": s.script_type.value,
                        "description": s.description,
                        "timeout_seconds": s.timeout_seconds,
                    }
                    for s in component.scripts
                ],
                "references": [
                    {
                        "name": r.name,
                        "content_type": r.content_type,
                        "size_bytes": r.size_bytes,
                    }
                    for r in component.references
                ],
                "assets": [
                    {
                        "name": a.name,
                        "asset_type": a.asset_type,
                        "size_bytes": a.size_bytes,
                    }
                    for a in component.assets
                ],
                "is_valid": component.is_valid,
                "validation_errors": component.validation_errors or [],
            }
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

    return {
        "skill_id": metadata.skill_id,
        "name": metadata.name,
        "version": metadata.version,
        "description": metadata.description,
        "author": metadata.author,
        "category": metadata.category,
        "tags": metadata.tags or [],
        "status": metadata.status or "active",
        "has_scripts": False,
        "has_references": False,
        "definition": metadata.model_dump(),
        "scripts": [],
        "references": [],
        "assets": [],
        "is_valid": True,
        "validation_errors": [],
    }


@router.get("/skills/stats/summary")
async def get_skills_stats() -> dict[str, Any]:
    """Get skill statistics summary."""
    return {
        "registry": registry.get_stats(),
        "lifecycle": lifecycle_manager.get_stats(),
    }


@router.get("/marketplace")
async def list_marketplace_skills(
    category: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """List all skills available in the marketplace."""
    skill_ids = _skill_loader.discover_skills()
    skills = []
    
    for skill_id in skill_ids:
        component = _skill_loader.load_skill(skill_id)
        if component and component.is_valid:
            if category and component.definition.category != category:
                continue
            if search:
                search_lower = search.lower()
                if (search_lower not in component.name.lower() and
                    search_lower not in component.definition.description.lower() and
                    search_lower not in skill_id.lower()):
                    continue
            
            skills.append({
                "skill_id": component.skill_id,
                "name": component.name,
                "version": component.definition.version,
                "description": component.definition.description,
                "author": component.definition.author,
                "category": component.definition.category,
                "tags": component.definition.tags,
                "has_scripts": component.has_scripts,
                "has_references": component.has_references,
                "status": component.definition.status.value,
            })
    
    return {
        "skills": skills,
        "total": len(skills),
    }


@router.get("/marketplace/categories")
async def get_marketplace_categories() -> dict[str, Any]:
    """Get all skill categories."""
    skill_ids = _skill_loader.discover_skills()
    categories: dict[str, int] = {}
    
    for skill_id in skill_ids:
        component = _skill_loader.load_skill(skill_id)
        if component and component.is_valid:
            cat = component.definition.category
            categories[cat] = categories.get(cat, 0) + 1
    
    return {
        "categories": [
            {"name": name, "count": count}
            for name, count in sorted(categories.items())
        ]
    }


@router.get("/marketplace/tags")
async def get_marketplace_tags() -> dict[str, Any]:
    """Get all skill tags."""
    skill_ids = _skill_loader.discover_skills()
    tags: dict[str, int] = {}
    
    for skill_id in skill_ids:
        component = _skill_loader.load_skill(skill_id)
        if component and component.is_valid:
            for tag in component.definition.tags:
                tags[tag] = tags.get(tag, 0) + 1
    
    return {
        "tags": [
            {"name": name, "count": count}
            for name, count in sorted(tags.items(), key=lambda x: -x[1])
        ]
    }


@router.post("/execute")
async def execute_skill_script(request: ExecuteScriptRequest) -> dict[str, Any]:
    """Execute a skill script."""
    component = _skill_loader.load_skill(request.skill_id)
    if not component:
        raise HTTPException(status_code=404, detail=f"Skill not found: {request.skill_id}")
    
    script = None
    for s in component.scripts:
        if s.name == request.script_name:
            script = s
            break
    
    if not script:
        raise HTTPException(
            status_code=404,
            detail=f"Script not found: {request.script_name}"
        )
    
    result = _script_executor.execute(script, request.parameters)
    
    return {
        "skill_id": request.skill_id,
        "script_name": request.script_name,
        "result": result,
    }


@router.post("/install")
async def install_skill(request: InstallSkillRequest) -> dict[str, Any]:
    """Install a skill from marketplace."""
    component = _skill_loader.load_skill(request.skill_id)
    if not component:
        raise HTTPException(status_code=404, detail=f"Skill not found: {request.skill_id}")
    
    if not component.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Skill validation failed: {component.validation_errors}"
        )
    
    return {
        "skill_id": request.skill_id,
        "status": "installed",
        "name": component.name,
        "version": component.definition.version,
    }


@router.post("/uninstall/{skill_id}")
async def uninstall_skill(skill_id: str) -> dict[str, Any]:
    """Uninstall a skill."""
    _skill_loader.reload_skill(skill_id)
    
    return {
        "skill_id": skill_id,
        "status": "uninstalled",
    }


@router.post("/reload/{skill_id}")
async def reload_skill(skill_id: str) -> dict[str, Any]:
    """Reload a skill from disk."""
    component = _skill_loader.reload_skill(skill_id)
    if not component:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    
    return {
        "skill_id": skill_id,
        "status": "reloaded",
        "is_valid": component.is_valid,
    }


class UpdateSkillRequest(BaseModel):
    """Request to update skill metadata."""
    name: str | None = None
    description: str | None = None
    version: str | None = None
    author: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    status: str | None = None
    parameters: dict[str, Any] | None = None


@router.put("/skills/{skill_id}")
async def update_skill(skill_id: str, request: UpdateSkillRequest) -> dict[str, Any]:
    """Update skill metadata."""
    component = _skill_loader.load_skill(skill_id)
    if not component:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    
    skill_dir = SKILLS_ROOT / skill_id
    skill_file = skill_dir / "SKILL.md"
    
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail=f"SKILL.md not found for {skill_id}")
    
    content = skill_file.read_text(encoding="utf-8")
    
    lines = content.split("\n")
    in_frontmatter = False
    frontmatter_lines = []
    body_lines = []
    frontmatter_end = -1
    
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                frontmatter_end = i
                in_frontmatter = False
                continue
        
        if in_frontmatter:
            frontmatter_lines.append(line)
        elif frontmatter_end >= 0:
            body_lines.append(line)
    
    updated_frontmatter = {}
    for line in frontmatter_lines:
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"\'')
            updated_frontmatter[key] = value
    
    if request.name is not None:
        updated_frontmatter["name"] = request.name
    if request.description is not None:
        updated_frontmatter["description"] = request.description
    if request.version is not None:
        updated_frontmatter["version"] = request.version
    if request.author is not None:
        updated_frontmatter["author"] = request.author
    if request.category is not None:
        updated_frontmatter["category"] = request.category
    if request.tags is not None:
        updated_frontmatter["tags"] = request.tags
    if request.status is not None:
        updated_frontmatter["status"] = request.status
    if request.parameters is not None:
        updated_frontmatter["parameters"] = request.parameters
    
    new_content = "---\n"
    for key, value in updated_frontmatter.items():
        if isinstance(value, list):
            new_content += f"{key}:\n"
            for item in value:
                new_content += f"  - {item}\n"
        elif isinstance(value, dict):
            import json
            new_content += f'{key}: {json.dumps(value)}\n'
        else:
            new_content += f'{key}: "{value}"\n'
    new_content += "---\n\n"
    new_content += "\n".join(body_lines)
    
    skill_file.write_text(new_content, encoding="utf-8")
    
    _skill_loader.reload_skill(skill_id)
    
    return {
        "skill_id": skill_id,
        "status": "updated",
        "updated_fields": list(request.model_dump(exclude_none=True).keys()),
    }


@router.get("/skills/{skill_id}/content")
async def get_skill_content(skill_id: str) -> dict[str, Any]:
    """Get the raw SKILL.md content."""
    skill_dir = SKILLS_ROOT / skill_id
    skill_file = skill_dir / "SKILL.md"
    
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail=f"SKILL.md not found for {skill_id}")
    
    content = skill_file.read_text(encoding="utf-8")
    
    return {
        "skill_id": skill_id,
        "content": content,
        "path": str(skill_file),
    }


@router.put("/skills/{skill_id}/content")
async def update_skill_content(skill_id: str, content: str) -> dict[str, Any]:
    """Update the raw SKILL.md content."""
    skill_dir = SKILLS_ROOT / skill_id
    skill_file = skill_dir / "SKILL.md"
    
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail=f"SKILL.md not found for {skill_id}")
    
    skill_file.write_text(content, encoding="utf-8")
    
    _skill_loader.reload_skill(skill_id)
    
    return {
        "skill_id": skill_id,
        "status": "updated",
    }
