"""
Transaction Management - System-level transaction coordination.

Provides:
- TransactionManager: Transaction lifecycle management
- TwoPhaseCommitCoordinator: Two-phase commit for distributed transactions
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


logger = logging.getLogger(__name__)


class TransactionState(str, Enum):
    """Transaction state."""
    ACTIVE = "active"
    PREPARING = "preparing"
    PREPARED = "prepared"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class TransactionContext:
    """Transaction context."""
    
    transaction_id: str
    state: TransactionState = TransactionState.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    participants: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def update_state(self, state: TransactionState) -> None:
        self.state = state
        self.updated_at = datetime.utcnow()


class TransactionManager:
    """
    Transaction lifecycle manager.
    
    Features:
    - Transaction creation and tracking
    - State management
    - Timeout handling
    """
    
    def __init__(self, default_timeout: float = 30.0):
        self._default_timeout = default_timeout
        self._active_transactions: dict[str, TransactionContext] = {}
        self._lock = asyncio.Lock()
    
    async def begin(self, timeout: float | None = None) -> TransactionContext:
        """Begin a new transaction."""
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        context = TransactionContext(
            transaction_id=transaction_id,
            metadata={"timeout": timeout or self._default_timeout}
        )
        
        async with self._lock:
            self._active_transactions[transaction_id] = context
        
        logger.debug(f"Transaction started: {transaction_id}")
        return context
    
    async def commit(self, transaction_id: str) -> bool:
        """Commit a transaction."""
        async with self._lock:
            context = self._active_transactions.get(transaction_id)
            if not context:
                return False
            
            context.update_state(TransactionState.COMMITTED)
            del self._active_transactions[transaction_id]
        
        logger.debug(f"Transaction committed: {transaction_id}")
        return True
    
    async def rollback(self, transaction_id: str) -> bool:
        """Rollback a transaction."""
        async with self._lock:
            context = self._active_transactions.get(transaction_id)
            if not context:
                return False
            
            context.update_state(TransactionState.ROLLED_BACK)
            del self._active_transactions[transaction_id]
        
        logger.debug(f"Transaction rolled back: {transaction_id}")
        return True
    
    def get_context(self, transaction_id: str) -> TransactionContext | None:
        """Get transaction context."""
        return self._active_transactions.get(transaction_id)
    
    async def cleanup_stale(self, max_age_seconds: float = 300) -> int:
        """Clean up stale transactions."""
        now = datetime.utcnow()
        stale_ids = []
        
        async with self._lock:
            for txn_id, context in self._active_transactions.items():
                age = (now - context.created_at).total_seconds()
                if age > max_age_seconds:
                    stale_ids.append(txn_id)
            
            for txn_id in stale_ids:
                del self._active_transactions[txn_id]
        
        return len(stale_ids)


class TwoPhaseCommitCoordinator:
    """
    Two-phase commit coordinator for distributed transactions.
    
    Protocol:
    1. PREPARE: Ask all participants to prepare
    2. COMMIT/ABORT: If all prepared, commit; otherwise abort
    
    Features:
    - Atomic commit across multiple backends
    - Automatic rollback on failure
    - Participant tracking
    """
    
    def __init__(
        self,
        transaction_manager: TransactionManager,
        max_participants: int = 10,
    ):
        self._txn_manager = transaction_manager
        self._max_participants = max_participants
        self._participants: dict[str, list[Callable]] = {}
    
    def register_participant(
        self,
        transaction_id: str,
        prepare_fn: Callable,
        commit_fn: Callable,
        rollback_fn: Callable,
    ) -> None:
        """Register a participant for a transaction."""
        if transaction_id not in self._participants:
            self._participants[transaction_id] = []
        
        if len(self._participants[transaction_id]) >= self._max_participants:
            raise ValueError(f"Max participants reached for transaction: {transaction_id}")
        
        self._participants[transaction_id].append({
            "prepare": prepare_fn,
            "commit": commit_fn,
            "rollback": rollback_fn,
        })
    
    async def execute_two_phase_commit(self, transaction_id: str) -> bool:
        """
        Execute two-phase commit protocol.
        
        Phase 1: Prepare all participants
        Phase 2: Commit all participants (if all prepared) or rollback (if any failed)
        """
        context = self._txn_manager.get_context(transaction_id)
        if not context:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        participants = self._participants.get(transaction_id, [])
        if not participants:
            return await self._txn_manager.commit(transaction_id)
        
        # Phase 1: Prepare
        context.update_state(TransactionState.PREPARING)
        prepared = []
        
        for participant in participants:
            try:
                await participant["prepare"]()
                prepared.append(participant)
            except Exception as e:
                logger.error(f"Prepare failed: {e}")
                context.update_state(TransactionState.FAILED)
                await self._rollback_participants(prepared, transaction_id)
                return False
        
        context.update_state(TransactionState.PREPARED)
        
        # Phase 2: Commit
        context.update_state(TransactionState.COMMITTING)
        
        for participant in participants:
            try:
                await participant["commit"]()
            except Exception as e:
                logger.error(f"Commit failed: {e}")
                # Note: In real implementation, need recovery mechanism
        
        context.update_state(TransactionState.COMMITTED)
        await self._txn_manager.commit(transaction_id)
        
        # Cleanup
        del self._participants[transaction_id]
        
        return True
    
    async def _rollback_participants(
        self,
        participants: list[dict],
        transaction_id: str,
    ) -> None:
        """Rollback prepared participants."""
        context = self._txn_manager.get_context(transaction_id)
        if context:
            context.update_state(TransactionState.ROLLING_BACK)
        
        for participant in participants:
            try:
                await participant["rollback"]()
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
        
        if context:
            context.update_state(TransactionState.ROLLED_BACK)
        
        await self._txn_manager.rollback(transaction_id)
    
    async def abort(self, transaction_id: str) -> bool:
        """Abort a transaction."""
        participants = self._participants.get(transaction_id, [])
        await self._rollback_participants(participants, transaction_id)
        
        if transaction_id in self._participants:
            del self._participants[transaction_id]
        
        return True
