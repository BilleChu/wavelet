"""
Skill Lifecycle Manager for OpenFinance.

Manages the complete lifecycle of skills including state transitions,
initialization, and cleanup.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, Field

from openfinance.models.skill import (
    SkillState,
    SkillMetadata,
    SkillConfig,
    SkillExecutionContext,
)

logger = logging.getLogger(__name__)


class LifecycleEvent(BaseModel):
    """Event in skill lifecycle."""

    event_id: str = Field(..., description="Event ID")
    skill_id: str = Field(..., description="Skill ID")
    event_type: str = Field(..., description="Event type")
    from_state: SkillState | None = Field(default=None, description="Previous state")
    to_state: SkillState | None = Field(default=None, description="New state")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Event timestamp",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Event metadata")


class StateTransition(BaseModel):
    """Valid state transition rule."""

    from_state: SkillState = Field(..., description="From state")
    to_state: SkillState = Field(..., description="To state")
    condition: str | None = Field(default=None, description="Transition condition")
    on_transition: str | None = Field(default=None, description="Callback name")


VALID_TRANSITIONS: dict[SkillState, set[SkillState]] = {
    SkillState.IDLE: {SkillState.LOADING, SkillState.TERMINATED},
    SkillState.LOADING: {SkillState.READY, SkillState.ERROR},
    SkillState.READY: {SkillState.EXECUTING, SkillState.PAUSED, SkillState.TERMINATED},
    SkillState.EXECUTING: {SkillState.READY, SkillState.ERROR, SkillState.PAUSED},
    SkillState.PAUSED: {SkillState.READY, SkillState.TERMINATED},
    SkillState.ERROR: {SkillState.LOADING, SkillState.TERMINATED},
    SkillState.TERMINATED: set(),
}


class SkillInstance(BaseModel):
    """Runtime instance of a skill."""

    metadata: SkillMetadata = Field(..., description="Skill metadata")
    config: SkillConfig = Field(..., description="Skill configuration")
    state: SkillState = Field(default=SkillState.IDLE, description="Current state")
    execution_count: int = Field(default=0, description="Total executions")
    error_count: int = Field(default=0, description="Total errors")
    last_execution: datetime | None = Field(default=None, description="Last execution time")
    last_error: str | None = Field(default=None, description="Last error message")


class SkillLifecycleManager:
    """Manages skill lifecycle and state transitions.

    Provides:
    - State machine management
    - Event-driven transitions
    - Lifecycle callbacks
    - Health monitoring
    """

    def __init__(self) -> None:
        self._instances: dict[str, SkillInstance] = {}
        self._callbacks: dict[str, dict[str, Callable]] = {}
        self._events: list[LifecycleEvent] = []
        self._lock = asyncio.Lock()

    async def register_skill(
        self,
        metadata: SkillMetadata,
        config: SkillConfig,
    ) -> bool:
        """Register a new skill instance."""
        async with self._lock:
            if metadata.skill_id in self._instances:
                logger.warning(f"Skill already registered: {metadata.skill_id}")
                return False

            instance = SkillInstance(
                metadata=metadata,
                config=config,
                state=SkillState.IDLE,
            )
            self._instances[metadata.skill_id] = instance
            self._callbacks[metadata.skill_id] = {}

            await self._record_event(
                metadata.skill_id,
                "registered",
                None,
                SkillState.IDLE,
            )

            logger.info(f"Registered skill: {metadata.skill_id}")
            return True

    async def unregister_skill(self, skill_id: str) -> bool:
        """Unregister a skill instance."""
        async with self._lock:
            if skill_id not in self._instances:
                return False

            instance = self._instances[skill_id]
            
            if instance.state != SkillState.TERMINATED:
                await self._transition(skill_id, SkillState.TERMINATED)

            del self._instances[skill_id]
            del self._callbacks[skill_id]

            logger.info(f"Unregistered skill: {skill_id}")
            return True

    async def transition(
        self,
        skill_id: str,
        target_state: SkillState,
    ) -> bool:
        """Transition skill to a new state."""
        async with self._lock:
            return await self._transition(skill_id, target_state)

    async def _transition(
        self,
        skill_id: str,
        target_state: SkillState,
    ) -> bool:
        """Internal transition logic."""
        instance = self._instances.get(skill_id)
        if not instance:
            logger.error(f"Skill not found: {skill_id}")
            return False

        current_state = instance.state
        
        if target_state not in VALID_TRANSITIONS.get(current_state, set()):
            logger.warning(
                f"Invalid transition: {current_state} -> {target_state} for {skill_id}"
            )
            return False

        from_state = current_state
        instance.state = target_state

        await self._record_event(
            skill_id,
            "state_change",
            from_state,
            target_state,
        )

        await self._execute_callbacks(skill_id, "on_state_change", {
            "from_state": from_state,
            "to_state": target_state,
        })

        logger.info(f"Skill {skill_id} transitioned: {from_state} -> {target_state}")
        return True

    async def initialize(self, skill_id: str) -> bool:
        """Initialize a skill (IDLE -> LOADING -> READY)."""
        instance = self._instances.get(skill_id)
        if not instance:
            return False

        if instance.state != SkillState.IDLE:
            logger.warning(f"Skill not in IDLE state: {skill_id}")
            return False

        if not await self._transition(skill_id, SkillState.LOADING):
            return False

        try:
            await self._execute_callbacks(skill_id, "on_initialize", {})
            await self._transition(skill_id, SkillState.READY)
            return True

        except Exception as e:
            instance.last_error = str(e)
            await self._transition(skill_id, SkillState.ERROR)
            return False

    async def execute(
        self,
        skill_id: str,
        context: SkillExecutionContext,
    ) -> bool:
        """Execute a skill (READY -> EXECUTING -> READY/ERROR)."""
        instance = self._instances.get(skill_id)
        if not instance:
            return False

        if instance.state != SkillState.READY:
            logger.warning(f"Skill not ready: {skill_id} (state: {instance.state})")
            return False

        if not await self._transition(skill_id, SkillState.EXECUTING):
            return False

        try:
            await self._execute_callbacks(skill_id, "on_execute", {
                "context": context.model_dump(),
            })

            instance.execution_count += 1
            instance.last_execution = datetime.now()

            await self._transition(skill_id, SkillState.READY)
            return True

        except Exception as e:
            instance.error_count += 1
            instance.last_error = str(e)
            await self._transition(skill_id, SkillState.ERROR)
            return False

    async def pause(self, skill_id: str) -> bool:
        """Pause a skill (READY/EXECUTING -> PAUSED)."""
        instance = self._instances.get(skill_id)
        if not instance:
            return False

        if instance.state not in [SkillState.READY, SkillState.EXECUTING]:
            return False

        return await self._transition(skill_id, SkillState.PAUSED)

    async def resume(self, skill_id: str) -> bool:
        """Resume a paused skill (PAUSED -> READY)."""
        instance = self._instances.get(skill_id)
        if not instance:
            return False

        if instance.state != SkillState.PAUSED:
            return False

        return await self._transition(skill_id, SkillState.READY)

    async def recover(self, skill_id: str) -> bool:
        """Recover a skill from error state (ERROR -> LOADING -> READY)."""
        instance = self._instances.get(skill_id)
        if not instance:
            return False

        if instance.state != SkillState.ERROR:
            return False

        if not await self._transition(skill_id, SkillState.LOADING):
            return False

        try:
            await self._execute_callbacks(skill_id, "on_recover", {})
            await self._transition(skill_id, SkillState.READY)
            return True

        except Exception as e:
            instance.last_error = str(e)
            await self._transition(skill_id, SkillState.ERROR)
            return False

    async def terminate(self, skill_id: str) -> bool:
        """Terminate a skill (any -> TERMINATED)."""
        instance = self._instances.get(skill_id)
        if not instance:
            return False

        await self._execute_callbacks(skill_id, "on_terminate", {})
        return await self._transition(skill_id, SkillState.TERMINATED)

    def register_callback(
        self,
        skill_id: str,
        event: str,
        callback: Callable,
    ) -> None:
        """Register a callback for a skill event."""
        if skill_id not in self._callbacks:
            self._callbacks[skill_id] = {}
        self._callbacks[skill_id][event] = callback

    async def _execute_callbacks(
        self,
        skill_id: str,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """Execute registered callbacks."""
        callbacks = self._callbacks.get(skill_id, {})
        callback = callbacks.get(event)
        
        if callback:
            try:
                result = callback(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.exception(f"Callback failed for {skill_id}.{event}")

    async def _record_event(
        self,
        skill_id: str,
        event_type: str,
        from_state: SkillState | None,
        to_state: SkillState | None,
    ) -> None:
        """Record a lifecycle event."""
        event = LifecycleEvent(
            event_id=f"{skill_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            skill_id=skill_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
        )
        self._events.append(event)

    def get_state(self, skill_id: str) -> SkillState | None:
        """Get current state of a skill."""
        instance = self._instances.get(skill_id)
        return instance.state if instance else None

    def get_instance(self, skill_id: str) -> SkillInstance | None:
        """Get skill instance."""
        return self._instances.get(skill_id)

    def list_skills(self, state: SkillState | None = None) -> list[SkillInstance]:
        """List all skills, optionally filtered by state."""
        instances = list(self._instances.values())
        if state:
            instances = [i for i in instances if i.state == state]
        return instances

    def get_events(
        self,
        skill_id: str | None = None,
        limit: int = 100,
    ) -> list[LifecycleEvent]:
        """Get lifecycle events."""
        events = self._events
        if skill_id:
            events = [e for e in events if e.skill_id == skill_id]
        return events[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get lifecycle manager statistics."""
        state_counts = {}
        for instance in self._instances.values():
            state = instance.state.value
            state_counts[state] = state_counts.get(state, 0) + 1

        return {
            "total_skills": len(self._instances),
            "state_distribution": state_counts,
            "total_events": len(self._events),
        }
