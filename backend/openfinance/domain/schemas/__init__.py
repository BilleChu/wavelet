"""
Domain Schemas - ORM Models for database storage.

Provides generic storage models that store dynamic attributes as JSONB,
allowing schema evolution without database migrations.

Fully compatible with legacy models in datacenter/models/orm.py.
"""

from .generic_model import (
    Base,
    GenericEntityModel,
    GenericRelationModel,
    GenericFactorModel,
    GenericStrategyModel,
)

__all__ = [
    "Base",
    "GenericEntityModel",
    "GenericRelationModel",
    "GenericFactorModel",
    "GenericStrategyModel",
]
