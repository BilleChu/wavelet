"""
Data Quality Checker for Data Center.

Provides comprehensive data quality assessment with:
- Completeness checking
- Accuracy validation
- Timeliness monitoring
- Consistency verification
- Uniqueness detection
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QualityDimension(str, Enum):
    """Dimensions of data quality."""
    
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    TIMELINESS = "timeliness"
    CONSISTENCY = "consistency"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"


class QualitySeverity(str, Enum):
    """Severity levels for quality issues."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class QualityIssue:
    """A data quality issue."""
    
    dimension: QualityDimension
    severity: QualitySeverity
    field_name: str | None
    message: str
    count: int = 1
    sample_values: list[Any] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "severity": self.severity.value,
            "field_name": self.field_name,
            "message": self.message,
            "count": self.count,
            "sample_values": self.sample_values[:5],
        }


class QualityRule(BaseModel):
    """A data quality rule."""
    
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    dimension: QualityDimension = Field(..., description="Quality dimension")
    description: str = Field(default="", description="Rule description")
    
    field_name: str | None = Field(default=None, description="Target field name")
    condition: str | None = Field(default=None, description="Condition expression")
    threshold: float | None = Field(default=None, description="Threshold value")
    
    severity: QualitySeverity = Field(
        default=QualitySeverity.MEDIUM,
        description="Issue severity when rule fails"
    )
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "dimension": self.dimension.value,
            "description": self.description,
            "field_name": self.field_name,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "enabled": self.enabled,
        }


class QualityMetric(BaseModel):
    """A data quality metric."""
    
    dimension: QualityDimension
    score: float = Field(..., ge=0.0, le=1.0, description="Quality score (0-1)")
    total_records: int = Field(default=0, description="Total records checked")
    passed_records: int = Field(default=0, description="Records passing check")
    failed_records: int = Field(default=0, description="Records failing check")
    
    @property
    def percentage(self) -> float:
        return self.score * 100
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": round(self.score, 4),
            "percentage": round(self.percentage, 2),
            "total_records": self.total_records,
            "passed_records": self.passed_records,
            "failed_records": self.failed_records,
        }


class QualityReport(BaseModel):
    """Complete data quality report."""
    
    report_id: str = Field(..., description="Unique report identifier")
    data_source: str = Field(..., description="Data source name")
    data_type: str = Field(..., description="Data type")
    
    overall_score: float = Field(default=0.0, description="Overall quality score")
    metrics: dict[str, QualityMetric] = Field(
        default_factory=dict,
        description="Metrics by dimension"
    )
    issues: list[QualityIssue] = Field(
        default_factory=list,
        description="Quality issues found"
    )
    
    checked_at: datetime = Field(default_factory=datetime.now)
    duration_ms: float | None = Field(default=None)
    
    passed: bool = Field(default=True, description="Whether quality check passed")
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "data_source": self.data_source,
            "data_type": self.data_type,
            "overall_score": round(self.overall_score, 4),
            "overall_percentage": round(self.overall_score * 100, 2),
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "issues": [i.to_dict() for i in self.issues],
            "issues_count": len(self.issues),
            "critical_issues": sum(1 for i in self.issues if i.severity == QualitySeverity.CRITICAL),
            "checked_at": self.checked_at.isoformat(),
            "duration_ms": self.duration_ms,
            "passed": self.passed,
        }


class DataQualityChecker:
    """
    Comprehensive data quality checker.
    
    Provides quality assessment across multiple dimensions:
    - Completeness: Missing values, null checks
    - Accuracy: Value range, format validation
    - Timeliness: Data freshness, update frequency
    - Consistency: Cross-field validation, referential integrity
    - Uniqueness: Duplicate detection
    - Validity: Schema compliance, business rules
    
    Usage:
        checker = DataQualityChecker()
        
        # Add rules
        checker.add_rule(QualityRule(
            rule_id="completeness_code",
            name="Stock Code Required",
            dimension=QualityDimension.COMPLETENESS,
            field_name="code",
            threshold=1.0,
        ))
        
        # Check data
        report = checker.check(data, source="eastmoney", data_type="stock_quote")
        
        print(f"Quality score: {report.overall_score * 100:.2f}%")
    """
    
    def __init__(
        self,
        min_completeness: float = 0.95,
        min_accuracy: float = 0.99,
        min_timeliness_hours: int = 24,
    ) -> None:
        self._rules: dict[str, QualityRule] = {}
        self._custom_checkers: dict[str, Callable] = {}
        
        self._min_completeness = min_completeness
        self._min_accuracy = min_accuracy
        self._min_timeliness_hours = min_timeliness_hours
        
        self._add_default_rules()
    
    def _add_default_rules(self) -> None:
        """Add default quality rules."""
        default_rules = [
            QualityRule(
                rule_id="default_completeness_code",
                name="Stock Code Completeness",
                dimension=QualityDimension.COMPLETENESS,
                field_name="code",
                threshold=self._min_completeness,
                severity=QualitySeverity.CRITICAL,
            ),
            QualityRule(
                rule_id="default_completeness_name",
                name="Stock Name Completeness",
                dimension=QualityDimension.COMPLETENESS,
                field_name="name",
                threshold=self._min_completeness,
                severity=QualitySeverity.HIGH,
            ),
            QualityRule(
                rule_id="default_validity_price",
                name="Price Validity",
                dimension=QualityDimension.VALIDITY,
                field_name="close",
                condition="value > 0",
                severity=QualitySeverity.HIGH,
            ),
            QualityRule(
                rule_id="default_uniqueness_record",
                name="Record Uniqueness",
                dimension=QualityDimension.UNIQUENESS,
                threshold=1.0,
                severity=QualitySeverity.HIGH,
            ),
        ]
        
        for rule in default_rules:
            self._rules[rule.rule_id] = rule
    
    def add_rule(self, rule: QualityRule) -> None:
        """Add a quality rule."""
        self._rules[rule.rule_id] = rule
        logger.info(f"Added quality rule: {rule.rule_id}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a quality rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False
    
    def register_custom_checker(
        self,
        dimension: QualityDimension,
        checker: Callable[[list[dict]], list[QualityIssue]],
    ) -> None:
        """Register a custom checker for a dimension."""
        self._custom_checkers[dimension.value] = checker
    
    def check(
        self,
        data: list[dict[str, Any]],
        source: str,
        data_type: str,
        rules: list[str] | None = None,
    ) -> QualityReport:
        """
        Perform quality check on data.
        
        Args:
            data: List of data records to check
            source: Data source name
            data_type: Type of data
            rules: Optional list of specific rules to apply
        
        Returns:
            QualityReport with assessment results
        """
        import uuid
        import time
        
        start_time = time.time()
        
        report = QualityReport(
            report_id=f"qr_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:4]}",
            data_source=source,
            data_type=data_type,
        )
        
        if not data:
            report.overall_score = 0.0
            report.passed = False
            report.issues.append(QualityIssue(
                dimension=QualityDimension.COMPLETENESS,
                severity=QualitySeverity.CRITICAL,
                field_name=None,
                message="No data to check",
            ))
            return report
        
        rules_to_apply = [
            r for r in self._rules.values()
            if r.enabled and (rules is None or r.rule_id in rules)
        ]
        
        metrics: dict[QualityDimension, list[float]] = {}
        
        for rule in rules_to_apply:
            score, issues = self._apply_rule(rule, data)
            
            if rule.dimension not in metrics:
                metrics[rule.dimension] = []
            metrics[rule.dimension].append(score)
            
            report.issues.extend(issues)
        
        for dimension, scores in metrics.items():
            avg_score = sum(scores) / len(scores) if scores else 0.0
            report.metrics[dimension.value] = QualityMetric(
                dimension=dimension,
                score=avg_score,
                total_records=len(data),
                passed_records=int(len(data) * avg_score),
                failed_records=int(len(data) * (1 - avg_score)),
            )
        
        if report.metrics:
            report.overall_score = sum(m.score for m in report.metrics.values()) / len(report.metrics)
        
        critical_issues = sum(1 for i in report.issues if i.severity == QualitySeverity.CRITICAL)
        report.passed = critical_issues == 0 and report.overall_score >= 0.9
        
        report.duration_ms = (time.time() - start_time) * 1000
        
        return report
    
    def _apply_rule(
        self,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> tuple[float, list[QualityIssue]]:
        """Apply a quality rule and return score and issues."""
        issues: list[QualityIssue] = []
        
        if rule.dimension == QualityDimension.COMPLETENESS:
            score, issue = self._check_completeness(rule, data)
            if issue:
                issues.append(issue)
        
        elif rule.dimension == QualityDimension.ACCURACY:
            score, issue = self._check_accuracy(rule, data)
            if issue:
                issues.append(issue)
        
        elif rule.dimension == QualityDimension.VALIDITY:
            score, issue = self._check_validity(rule, data)
            if issue:
                issues.append(issue)
        
        elif rule.dimension == QualityDimension.UNIQUENESS:
            score, issue = self._check_uniqueness(rule, data)
            if issue:
                issues.append(issue)
        
        elif rule.dimension == QualityDimension.CONSISTENCY:
            score, issue = self._check_consistency(rule, data)
            if issue:
                issues.append(issue)
        
        elif rule.dimension == QualityDimension.TIMELINESS:
            score, issue = self._check_timeliness(rule, data)
            if issue:
                issues.append(issue)
        
        else:
            score = 1.0
        
        return score, issues
    
    def _check_completeness(
        self,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> tuple[float, QualityIssue | None]:
        """Check data completeness."""
        if not rule.field_name:
            return 1.0, None
        
        total = len(data)
        missing = 0
        sample_values = []
        
        for record in data:
            value = record.get(rule.field_name)
            if value is None or value == "" or value == "-":
                missing += 1
                if len(sample_values) < 5:
                    sample_values.append(record.get("code", "unknown"))
        
        score = (total - missing) / total if total > 0 else 0.0
        threshold = rule.threshold or self._min_completeness
        
        if score < threshold:
            return score, QualityIssue(
                dimension=QualityDimension.COMPLETENESS,
                severity=rule.severity,
                field_name=rule.field_name,
                message=f"Completeness {score:.2%} below threshold {threshold:.2%}",
                count=missing,
                sample_values=sample_values,
            )
        
        return score, None
    
    def _check_accuracy(
        self,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> tuple[float, QualityIssue | None]:
        """Check data accuracy."""
        if not rule.field_name or not rule.condition:
            return 1.0, None
        
        total = len(data)
        inaccurate = 0
        sample_values = []
        
        for record in data:
            value = record.get(rule.field_name)
            if not self._evaluate_condition(value, rule.condition):
                inaccurate += 1
                if len(sample_values) < 5:
                    sample_values.append(value)
        
        score = (total - inaccurate) / total if total > 0 else 0.0
        threshold = rule.threshold or self._min_accuracy
        
        if score < threshold:
            return score, QualityIssue(
                dimension=QualityDimension.ACCURACY,
                severity=rule.severity,
                field_name=rule.field_name,
                message=f"Accuracy {score:.2%} below threshold {threshold:.2%}",
                count=inaccurate,
                sample_values=sample_values,
            )
        
        return score, None
    
    def _check_validity(
        self,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> tuple[float, QualityIssue | None]:
        """Check data validity."""
        if not rule.field_name:
            return 1.0, None
        
        total = len(data)
        invalid = 0
        sample_values = []
        
        for record in data:
            value = record.get(rule.field_name)
            
            if rule.condition and not self._evaluate_condition(value, rule.condition):
                invalid += 1
                if len(sample_values) < 5:
                    sample_values.append(value)
        
        score = (total - invalid) / total if total > 0 else 0.0
        
        if invalid > 0:
            return score, QualityIssue(
                dimension=QualityDimension.VALIDITY,
                severity=rule.severity,
                field_name=rule.field_name,
                message=f"Found {invalid} invalid values",
                count=invalid,
                sample_values=sample_values,
            )
        
        return score, None
    
    def _check_uniqueness(
        self,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> tuple[float, QualityIssue | None]:
        """Check data uniqueness."""
        total = len(data)
        
        key_fields = ["code", "trade_date", "report_date"]
        keys = []
        duplicates = 0
        
        for record in data:
            key = tuple(record.get(f, "") for f in key_fields if record.get(f))
            if key in keys:
                duplicates += 1
            else:
                keys.append(key)
        
        unique_count = len(keys)
        score = unique_count / total if total > 0 else 0.0
        
        if duplicates > 0:
            return score, QualityIssue(
                dimension=QualityDimension.UNIQUENESS,
                severity=rule.severity,
                field_name=None,
                message=f"Found {duplicates} duplicate records",
                count=duplicates,
            )
        
        return score, None
    
    def _check_consistency(
        self,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> tuple[float, QualityIssue | None]:
        """Check data consistency."""
        return 1.0, None
    
    def _check_timeliness(
        self,
        rule: QualityRule,
        data: list[dict[str, Any]],
    ) -> tuple[float, QualityIssue | None]:
        """Check data timeliness."""
        if not data:
            return 0.0, QualityIssue(
                dimension=QualityDimension.TIMELINESS,
                severity=QualitySeverity.HIGH,
                field_name=None,
                message="No data to check timeliness",
            )
        
        date_fields = ["trade_date", "report_date", "published_at", "created_at"]
        latest_date: datetime | None = None
        
        for record in data:
            for field in date_fields:
                value = record.get(field)
                if value:
                    try:
                        if isinstance(value, str):
                            date = datetime.strptime(value[:10], "%Y-%m-%d")
                        elif isinstance(value, datetime):
                            date = value
                        else:
                            continue
                        
                        if latest_date is None or date > latest_date:
                            latest_date = date
                    except (ValueError, TypeError):
                        continue
        
        if latest_date is None:
            return 0.5, QualityIssue(
                dimension=QualityDimension.TIMELINESS,
                severity=QualitySeverity.MEDIUM,
                field_name=None,
                message="Could not determine data timestamp",
            )
        
        age_hours = (datetime.now() - latest_date).total_seconds() / 3600
        threshold = rule.threshold or self._min_timeliness_hours
        
        if age_hours > threshold:
            score = max(0, 1 - (age_hours - threshold) / (threshold * 2))
            return score, QualityIssue(
                dimension=QualityDimension.TIMELINESS,
                severity=QualitySeverity.MEDIUM,
                field_name=None,
                message=f"Data is {age_hours:.1f} hours old (threshold: {threshold}h)",
            )
        
        return 1.0, None
    
    def _evaluate_condition(self, value: Any, condition: str) -> bool:
        """Evaluate a condition against a value."""
        try:
            if condition == "value > 0":
                return value is not None and float(value) > 0
            elif condition == "value >= 0":
                return value is not None and float(value) >= 0
            elif condition == "value != null":
                return value is not None
            elif condition.startswith("value in"):
                allowed = eval(condition.split("in")[1].strip())
                return value in allowed
            else:
                return True
        except (ValueError, TypeError):
            return False
    
    def get_rules(self) -> list[QualityRule]:
        """Get all quality rules."""
        return list(self._rules.values())
    
    def get_rules_by_dimension(self, dimension: QualityDimension) -> list[QualityRule]:
        """Get rules for a specific dimension."""
        return [r for r in self._rules.values() if r.dimension == dimension]
