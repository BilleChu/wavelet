"""
Skill Priority Sorter for OpenFinance.

Provides dynamic priority calculation and skill ordering.
"""

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from openfinance.models.skill import (
    SkillPriority,
    PriorityRule,
    PriorityContext,
)

logger = logging.getLogger(__name__)


class PriorityScore(BaseModel):
    """Calculated priority score for a skill."""

    skill_id: str = Field(..., description="Skill ID")
    base_priority: int = Field(..., description="Base priority value")
    adjustments: int = Field(default=0, description="Priority adjustments")
    final_priority: int = Field(..., description="Final priority score")
    reasons: list[str] = Field(default_factory=list, description="Reasons for adjustments")


class SkillPrioritySorter:
    """Sorts skills by priority based on rules and context.

    Provides:
    - Rule-based priority calculation
    - Context-aware adjustments
    - Historical usage weighting
    - Dynamic reordering
    """

    DEFAULT_RULES: list[PriorityRule] = [
        PriorityRule(
            name="intent_match",
            condition="intent_type == skill.intent_type",
            priority_adjustment=50,
            weight=1.0,
        ),
        PriorityRule(
            name="recent_success",
            condition="skill.success_rate > 0.8",
            priority_adjustment=20,
            weight=0.8,
        ),
        PriorityRule(
            name="low_latency",
            condition="skill.avg_latency_ms < 100",
            priority_adjustment=10,
            weight=0.5,
        ),
        PriorityRule(
            name="user_preference",
            condition="skill_id in user_preferences.favorite_skills",
            priority_adjustment=30,
            weight=1.0,
        ),
    ]

    def __init__(
        self,
        rules: list[PriorityRule] | None = None,
    ) -> None:
        self.rules = rules or self.DEFAULT_RULES
        self._skill_stats: dict[str, dict[str, Any]] = {}

    def update_skill_stats(
        self,
        skill_id: str,
        stats: dict[str, Any],
    ) -> None:
        """Update statistics for a skill."""
        self._skill_stats[skill_id] = stats

    def calculate_priority(
        self,
        skill_id: str,
        base_priority: int,
        context: PriorityContext,
        skill_metadata: dict[str, Any] | None = None,
    ) -> PriorityScore:
        """Calculate priority score for a skill."""
        adjustments = 0
        reasons = []

        skill_stats = self._skill_stats.get(skill_id, {})
        skill_info = {
            **skill_stats,
            **(skill_metadata or {}),
        }

        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                if self._evaluate_condition(rule.condition, skill_id, context, skill_info):
                    adjustment = int(rule.priority_adjustment * rule.weight)
                    adjustments += adjustment
                    reasons.append(f"{rule.name}: +{adjustment}")

            except Exception as e:
                logger.warning(f"Rule evaluation failed: {rule.name} - {e}")

        usage_bonus = self._calculate_usage_bonus(skill_id, context)
        if usage_bonus != 0:
            adjustments += usage_bonus
            reasons.append(f"usage_bonus: +{usage_bonus}")

        time_bonus = self._calculate_time_bonus(skill_id)
        if time_bonus != 0:
            adjustments += time_bonus
            reasons.append(f"time_bonus: +{time_bonus}")

        final_priority = base_priority + adjustments

        return PriorityScore(
            skill_id=skill_id,
            base_priority=base_priority,
            adjustments=adjustments,
            final_priority=final_priority,
            reasons=reasons,
        )

    def sort_skills(
        self,
        skills: list[dict[str, Any]],
        context: PriorityContext,
    ) -> list[dict[str, Any]]:
        """Sort skills by calculated priority."""
        scored_skills = []

        for skill in skills:
            skill_id = skill.get("skill_id", "")
            base_priority = skill.get("priority", 0)

            score = self.calculate_priority(
                skill_id,
                base_priority,
                context,
                skill,
            )

            scored_skills.append({
                **skill,
                "_priority_score": score,
            })

        scored_skills.sort(
            key=lambda s: s["_priority_score"].final_priority,
            reverse=True,
        )

        return scored_skills

    def _evaluate_condition(
        self,
        condition: str,
        skill_id: str,
        context: PriorityContext,
        skill_info: dict[str, Any],
    ) -> bool:
        """Evaluate a priority condition."""
        if "intent_type ==" in condition:
            expected_intent = condition.split("==")[1].strip().strip('"\'')
            return context.intent_type == expected_intent

        if "success_rate >" in condition:
            threshold = float(condition.split(">")[1].strip())
            return skill_info.get("success_rate", 0) > threshold

        if "avg_latency_ms <" in condition:
            threshold = float(condition.split("<")[1].strip())
            return skill_info.get("avg_latency_ms", float("inf")) < threshold

        if "in user_preferences" in condition:
            return skill_id in context.user_preferences.get("favorite_skills", [])

        return False

    def _calculate_usage_bonus(
        self,
        skill_id: str,
        context: PriorityContext,
    ) -> int:
        """Calculate bonus based on historical usage."""
        usage_count = context.historical_usage.get(skill_id, 0)
        
        if usage_count == 0:
            return 5
        
        if usage_count < 5:
            return 3
        
        if usage_count < 20:
            return 0
        
        return -2

    def _calculate_time_bonus(self, skill_id: str) -> int:
        """Calculate bonus based on time of day."""
        hour = datetime.now().hour

        if 9 <= hour <= 15:
            if "market" in skill_id.lower() or "stock" in skill_id.lower():
                return 10

        if 8 <= hour <= 10:
            if "news" in skill_id.lower():
                return 5

        return 0

    def add_rule(self, rule: PriorityRule) -> None:
        """Add a new priority rule."""
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name."""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules.pop(i)
                return True
        return False

    def enable_rule(self, rule_name: str) -> bool:
        """Enable a rule."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                return True
        return False

    def disable_rule(self, rule_name: str) -> bool:
        """Disable a rule."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                return True
        return False

    def get_rules(self) -> list[PriorityRule]:
        """Get all rules."""
        return list(self.rules)
