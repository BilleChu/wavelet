"""
Pipeline Builder - Build DAG from pipeline configuration.

Uses DAGEngine from task module to create executable DAGs.
"""

from __future__ import annotations

from typing import Any, Callable

from openfinance.datacenter.task.dag_engine import (
    DAG,
    DAGBuilder,
    DAGNode,
    DAGEdge,
    DAGEngine,
    NodeType,
    TaskPriority as DAGPriority,
    TaskStatus,
)
from openfinance.datacenter.task.queue import TaskPriority
from openfinance.datacenter.task.pipeline.pipeline_config import (
    PipelineConfig,
    PipelineTaskConfig,
)


def _convert_priority(priority: TaskPriority) -> DAGPriority:
    """Convert queue TaskPriority to DAG TaskPriority."""
    mapping = {
        TaskPriority.CRITICAL: DAGPriority.CRITICAL,
        TaskPriority.HIGH: DAGPriority.HIGH,
        TaskPriority.NORMAL: DAGPriority.NORMAL,
        TaskPriority.LOW: DAGPriority.LOW,
        TaskPriority.BACKGROUND: DAGPriority.BACKGROUND,
    }
    return mapping.get(priority, DAGPriority.NORMAL)


class PipelineBuilder:
    """
    Builder for creating DAGs from pipeline configurations.
    
    Example:
        builder = PipelineBuilder()
        dag = builder.build(pipeline_config)
        dag_engine.register_dag(dag)
        await dag_engine.execute_dag(dag.dag_id)
    """
    
    def __init__(self, dag_engine: DAGEngine | None = None):
        self.dag_engine = dag_engine or DAGEngine()
    
    def build(
        self,
        config: PipelineConfig,
        dag_id: str | None = None,
    ) -> DAG:
        """
        Build a DAG from pipeline configuration.
        
        Args:
            config: Pipeline configuration
            dag_id: Optional custom DAG ID
        
        Returns:
            DAG ready for execution
        """
        builder = DAGBuilder(config.name)
        builder.description(config.description)
        
        for task in config.tasks:
            builder.add_task(
                task_id=task.task_id,
                name=task.name,
                task_type=task.task_type,
                params=task.params,
                depends_on=task.dependencies if task.dependencies else None,
                priority=_convert_priority(task.priority),
                timeout=task.timeout_seconds,
                max_retries=task.max_retries,
            )
        
        dag = builder.build(dag_id or config.pipeline_id)
        
        dag.metadata = {
            **config.metadata,
            "pipeline_id": config.pipeline_id,
            "schedule_type": config.schedule.type.value,
            "schedule_expr": config.schedule.expression,
            "max_concurrent_tasks": config.max_concurrent_tasks,
        }
        
        return dag
    
    def build_and_register(
        self,
        config: PipelineConfig,
        dag_id: str | None = None,
    ) -> DAG:
        """
        Build a DAG and register it with the DAG engine.
        
        Args:
            config: Pipeline configuration
            dag_id: Optional custom DAG ID
        
        Returns:
            Registered DAG
        """
        dag = self.build(config, dag_id)
        self.dag_engine.register_dag(dag)
        return dag
    
    def get_engine(self) -> DAGEngine:
        """Get the DAG engine."""
        return self.dag_engine


def build_dag_from_config(
    config: PipelineConfig,
    dag_engine: DAGEngine | None = None,
) -> DAG:
    """
    Convenience function to build a DAG from configuration.
    
    Args:
        config: Pipeline configuration
        dag_engine: Optional DAG engine to register with
    
    Returns:
        DAG ready for execution
    """
    builder = PipelineBuilder(dag_engine)
    return builder.build(config)
