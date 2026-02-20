"""
Pipeline Registry for Data Center.

Provides centralized management for:
- Pipeline templates
- Pipeline instances
- Pipeline versioning
- Pipeline discovery
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml
from pydantic import BaseModel, Field

from .builder import Pipeline, PipelineStatus, PipelineBuilder

logger = logging.getLogger(__name__)


class PipelineTemplate(BaseModel):
    """Template for creating pipelines."""
    
    template_id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(default="", description="Template description")
    version: str = Field(default="1.0.0", description="Template version")
    
    category: str = Field(default="general", description="Template category")
    tags: list[str] = Field(default_factory=list, description="Template tags")
    
    stages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Stage definitions"
    )
    edges: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Edge definitions"
    )
    
    default_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Default configuration"
    )
    config_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for configuration"
    )
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "tags": self.tags,
            "stages": self.stages,
            "edges": self.edges,
            "default_config": self.default_config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_yaml(cls, path: Path) -> "PipelineTemplate":
        """Load template from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, path: Path) -> None:
        """Save template to YAML file."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(mode="json"), f, allow_unicode=True, default_flow_style=False)


@dataclass
class PipelineInstance:
    """Runtime instance of a pipeline."""
    
    instance_id: str
    pipeline: Pipeline
    template_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    last_run_at: datetime | None = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    def record_run(self, success: bool) -> None:
        self.last_run_at = datetime.now()
        self.run_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "template_id": self.template_id,
            "pipeline_id": self.pipeline.pipeline_id,
            "pipeline_name": self.pipeline.name,
            "status": self.pipeline.status.value,
            "created_at": self.created_at.isoformat(),
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_count / max(self.run_count, 1),
        }


class PipelineRegistry:
    """
    Central registry for pipeline templates and instances.
    
    Features:
    - Template registration and discovery
    - Pipeline instantiation from templates
    - Version management
    - Persistence support
    
    Usage:
        registry = PipelineRegistry()
        
        # Register a template
        registry.register_template(template)
        
        # Create pipeline from template
        pipeline = registry.create_pipeline(
            template_id="daily_collection",
            config={"symbols": ["600000"]}
        )
        
        # List templates
        templates = registry.list_templates(category="collection")
    """
    
    def __init__(
        self,
        template_dir: Path | None = None,
        persistence_enabled: bool = True,
    ) -> None:
        self._templates: dict[str, PipelineTemplate] = {}
        self._instances: dict[str, PipelineInstance] = {}
        self._handlers: dict[str, Callable] = {}
        
        self._template_dir = template_dir
        self._persistence_enabled = persistence_enabled
        
        if template_dir and template_dir.exists():
            self._load_templates_from_dir(template_dir)
    
    def register_template(self, template: PipelineTemplate) -> None:
        """Register a pipeline template."""
        self._templates[template.template_id] = template
        logger.info(f"Registered template: {template.template_id} v{template.version}")
        
        if self._persistence_enabled and self._template_dir:
            self._save_template(template)
    
    def unregister_template(self, template_id: str) -> bool:
        """Unregister a pipeline template."""
        if template_id in self._templates:
            del self._templates[template_id]
            logger.info(f"Unregistered template: {template_id}")
            return True
        return False
    
    def get_template(self, template_id: str) -> PipelineTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def list_templates(
        self,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> list[PipelineTemplate]:
        """
        List templates with optional filters.
        
        Args:
            category: Filter by category
            tags: Filter by tags (any match)
        
        Returns:
            List of matching templates
        """
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if tags:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tags)
            ]
        
        return templates
    
    def register_handler(
        self,
        handler_id: str,
        handler: Callable,
    ) -> None:
        """Register a handler function for use in pipelines."""
        self._handlers[handler_id] = handler
        logger.info(f"Registered handler: {handler_id}")
    
    def get_handler(self, handler_id: str) -> Callable | None:
        """Get a registered handler by ID."""
        return self._handlers.get(handler_id)
    
    def create_pipeline(
        self,
        template_id: str,
        config: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> Pipeline:
        """
        Create a pipeline from a template.
        
        Args:
            template_id: Template to use
            config: Configuration overrides
            name: Optional pipeline name
        
        Returns:
            Configured Pipeline instance
        """
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        merged_config = {**template.default_config, **(config or {})}
        
        builder = PipelineBuilder(
            name=name or template.name,
            description=template.description,
        )
        
        stage_id_map: dict[str, str] = {}
        
        for stage_def in template.stages:
            stage_name = stage_def["name"]
            stage_type = stage_def["type"]
            handler_id = stage_def.get("handler")
            
            handler = None
            if handler_id:
                handler = self._handlers.get(handler_id)
                if not handler:
                    logger.warning(f"Handler not found: {handler_id}")
            
            stage_config = {**stage_def.get("config", {}), **merged_config}
            
            builder._add_stage(
                name=stage_name,
                stage_type=stage_type,
                handler=handler,
                config=stage_config,
            )
            
            stage_id_map[stage_def["id"]] = builder._current_stage
        
        for edge_def in template.edges:
            source_id = stage_id_map.get(edge_def["source"])
            target_id = stage_id_map.get(edge_def["target"])
            
            if source_id and target_id:
                builder._add_edge(source_id, target_id)
        
        pipeline = builder.build()
        
        instance = PipelineInstance(
            instance_id=f"inst_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            pipeline=pipeline,
            template_id=template_id,
        )
        self._instances[instance.instance_id] = instance
        
        logger.info_with_context(
            f"Created pipeline from template: {template_id}",
            context={
                "instance_id": instance.instance_id,
                "pipeline_id": pipeline.pipeline_id,
            }
        )
        
        return pipeline
    
    def create_pipeline_from_builder(
        self,
        builder: PipelineBuilder,
        template_id: str | None = None,
    ) -> Pipeline:
        """Create a pipeline from a builder."""
        pipeline = builder.build()
        
        instance = PipelineInstance(
            instance_id=f"inst_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            pipeline=pipeline,
            template_id=template_id,
        )
        self._instances[instance.instance_id] = instance
        
        return pipeline
    
    def get_instance(self, instance_id: str) -> PipelineInstance | None:
        """Get a pipeline instance by ID."""
        return self._instances.get(instance_id)
    
    def list_instances(
        self,
        template_id: str | None = None,
        status: PipelineStatus | None = None,
    ) -> list[PipelineInstance]:
        """List pipeline instances with optional filters."""
        instances = list(self._instances.values())
        
        if template_id:
            instances = [i for i in instances if i.template_id == template_id]
        
        if status:
            instances = [i for i in instances if i.pipeline.status == status]
        
        return instances
    
    def _load_templates_from_dir(self, directory: Path) -> None:
        """Load all templates from a directory."""
        for yaml_file in directory.glob("**/*.yaml"):
            try:
                template = PipelineTemplate.from_yaml(yaml_file)
                self._templates[template.template_id] = template
                logger.info(f"Loaded template from {yaml_file}: {template.template_id}")
            except Exception as e:
                logger.error(f"Failed to load template from {yaml_file}: {e}")
    
    def _save_template(self, template: PipelineTemplate) -> None:
        """Save a template to the template directory."""
        if not self._template_dir:
            return
        
        self._template_dir.mkdir(parents=True, exist_ok=True)
        path = self._template_dir / f"{template.template_id}.yaml"
        template.to_yaml(path)
    
    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        instances = list(self._instances.values())
        
        total_runs = sum(i.run_count for i in instances)
        total_success = sum(i.success_count for i in instances)
        
        return {
            "templates_count": len(self._templates),
            "instances_count": len(instances),
            "handlers_count": len(self._handlers),
            "total_runs": total_runs,
            "total_success": total_success,
            "success_rate": total_success / max(total_runs, 1),
            "categories": list(set(t.category for t in self._templates.values())),
            "tags": list(set(tag for t in self._templates.values() for tag in t.tags)),
        }
    
    def export_templates(self, path: Path) -> None:
        """Export all templates to a directory."""
        path.mkdir(parents=True, exist_ok=True)
        for template in self._templates.values():
            template.to_yaml(path / f"{template.template_id}.yaml")
        logger.info(f"Exported {len(self._templates)} templates to {path}")
    
    def import_templates(self, path: Path) -> int:
        """Import templates from a directory."""
        count = 0
        for yaml_file in path.glob("**/*.yaml"):
            try:
                template = PipelineTemplate.from_yaml(yaml_file)
                self._templates[template.template_id] = template
                count += 1
            except Exception as e:
                logger.error(f"Failed to import template from {yaml_file}: {e}")
        logger.info(f"Imported {count} templates from {path}")
        return count


def create_default_templates() -> list[PipelineTemplate]:
    """Create default pipeline templates."""
    
    daily_collection = PipelineTemplate(
        template_id="daily_collection",
        name="Daily Data Collection",
        description="Daily stock data collection pipeline",
        category="collection",
        tags=["daily", "stock", "market"],
        stages=[
            {
                "id": "preload",
                "name": "Preload Companies",
                "type": "source",
                "handler": "company_preload",
                "config": {},
            },
            {
                "id": "collect_quotes",
                "name": "Collect Quotes",
                "type": "source",
                "handler": "stock_quote_collector",
                "config": {},
            },
            {
                "id": "collect_financial",
                "name": "Collect Financial",
                "type": "source",
                "handler": "financial_collector",
                "config": {},
            },
            {
                "id": "validate",
                "name": "Validate Data",
                "type": "validate",
                "handler": "data_validator",
                "config": {},
            },
            {
                "id": "save",
                "name": "Save to Database",
                "type": "sink",
                "handler": "database_sink",
                "config": {},
            },
        ],
        edges=[
            {"source": "preload", "target": "collect_quotes"},
            {"source": "preload", "target": "collect_financial"},
            {"source": "collect_quotes", "target": "validate"},
            {"source": "collect_financial", "target": "validate"},
            {"source": "validate", "target": "save"},
        ],
        default_config={
            "batch_size": 500,
            "timeout_seconds": 300,
        },
    )
    
    research_report = PipelineTemplate(
        template_id="research_report",
        name="Research Report Processing",
        description="Process research reports from EastMoney",
        category="processing",
        tags=["research", "report", "nlp"],
        stages=[
            {
                "id": "fetch_reports",
                "name": "Fetch Reports",
                "type": "source",
                "handler": "research_report_fetcher",
                "config": {},
            },
            {
                "id": "parse_content",
                "name": "Parse Content",
                "type": "transform",
                "handler": "content_parser",
                "config": {},
            },
            {
                "id": "extract_entities",
                "name": "Extract Entities",
                "type": "transform",
                "handler": "entity_extractor",
                "config": {},
            },
            {
                "id": "analyze_sentiment",
                "name": "Analyze Sentiment",
                "type": "transform",
                "handler": "sentiment_analyzer",
                "config": {},
            },
            {
                "id": "save",
                "name": "Save Results",
                "type": "sink",
                "handler": "research_sink",
                "config": {},
            },
        ],
        edges=[
            {"source": "fetch_reports", "target": "parse_content"},
            {"source": "parse_content", "target": "extract_entities"},
            {"source": "parse_content", "target": "analyze_sentiment"},
            {"source": "extract_entities", "target": "save"},
            {"source": "analyze_sentiment", "target": "save"},
        ],
        default_config={
            "source": "eastmoney",
            "days_back": 7,
        },
    )
    
    return [daily_collection, research_report]
