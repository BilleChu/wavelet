#!/usr/bin/env python
"""
Management Evaluation Script.

Evaluates management quality based on:
1. Capital allocation
2. Shareholder communication
3. Track record
4. Compensation alignment
5. Integrity and transparency
"""

import json
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class ManagementFactor:
    """A factor in management evaluation."""
    name: str
    score: float
    weight: float
    evidence: list[str]
    concerns: list[str]


def evaluate_capital_allocation(data: dict[str, Any]) -> ManagementFactor:
    """Evaluate capital allocation decisions."""
    score = 5.0
    evidence = []
    concerns = []
    
    roe = data.get("roe", 0)
    roic = data.get("roic", 0)
    dividend_policy = data.get("dividend_policy", "")
    buyback_history = data.get("buyback_history", {})
    acquisition_quality = data.get("acquisition_quality", "unknown")
    
    if roe > 0.20:
        score += 1.5
        evidence.append(f"Excellent ROE ({roe*100:.1f}%)")
    elif roe > 0.15:
        score += 0.5
        evidence.append(f"Good ROE ({roe*100:.1f}%)")
    elif roe < 0.10:
        concerns.append(f"Low ROE ({roe*100:.1f}%)")
    
    if roic > 0.15:
        score += 1.0
        evidence.append(f"Strong ROIC ({roic*100:.1f}%)")
    elif roic < 0.10:
        concerns.append(f"Weak ROIC ({roic*100:.1f}%)")
    
    if dividend_policy == "growing":
        score += 0.5
        evidence.append("Consistent dividend growth")
    elif dividend_policy == "stable":
        evidence.append("Stable dividend policy")
    
    if buyback_history.get("disciplined", False):
        score += 0.5
        evidence.append("Disciplined share repurchases")
    elif buyback_history.get("overpaid", False):
        concerns.append("Share repurchases at high valuations")
    
    if acquisition_quality == "excellent":
        score += 1.0
        evidence.append("Excellent acquisition track record")
    elif acquisition_quality == "poor":
        score -= 1.0
        concerns.append("Poor acquisition history")
    
    return ManagementFactor(
        name="Capital Allocation",
        score=max(0, min(10, score)),
        weight=0.25,
        evidence=evidence,
        concerns=concerns,
    )


def evaluate_shareholder_communication(data: dict[str, Any]) -> ManagementFactor:
    """Evaluate shareholder communication quality."""
    score = 5.0
    evidence = []
    concerns = []
    
    annual_report_quality = data.get("annual_report_quality", "standard")
    ceo_letter_transparency = data.get("ceo_letter_transparency", "standard")
    investor_day_frequency = data.get("investor_day_frequency", 0)
    guidance_accuracy = data.get("guidance_accuracy", 0)
    
    if annual_report_quality == "excellent":
        score += 1.5
        evidence.append("Exceptional annual report quality")
    elif annual_report_quality == "poor":
        concerns.append("Poor annual report quality")
    
    if ceo_letter_transparency == "high":
        score += 1.5
        evidence.append("Highly transparent CEO communications")
    elif ceo_letter_transparency == "low":
        concerns.append("Lack of transparency in communications")
    
    if investor_day_frequency >= 1:
        score += 0.5
        evidence.append("Regular investor days")
    
    if guidance_accuracy > 0.8:
        score += 0.5
        evidence.append("Accurate financial guidance")
    elif guidance_accuracy < 0.5:
        concerns.append("Inaccurate financial guidance")
    
    return ManagementFactor(
        name="Shareholder Communication",
        score=max(0, min(10, score)),
        weight=0.15,
        evidence=evidence,
        concerns=concerns,
    )


def evaluate_track_record(data: dict[str, Any]) -> ManagementFactor:
    """Evaluate management track record."""
    score = 5.0
    evidence = []
    concerns = []
    
    ceo_tenure_years = data.get("ceo_tenure_years", 0)
    revenue_growth_cagr = data.get("revenue_growth_cagr", 0)
    eps_growth_cagr = data.get("eps_growth_cagr", 0)
    crisis_handling = data.get("crisis_handling", "unknown")
    industry_experience = data.get("industry_experience_years", 0)
    
    if ceo_tenure_years > 10:
        score += 1.5
        evidence.append(f"Long-serving CEO ({ceo_tenure_years} years)")
    elif ceo_tenure_years < 3:
        concerns.append(f"New CEO ({ceo_tenure_years} years)")
    
    if revenue_growth_cagr > 0.10:
        score += 1.0
        evidence.append(f"Strong revenue growth ({revenue_growth_cagr*100:.1f}% CAGR)")
    elif revenue_growth_cagr < 0:
        concerns.append(f"Declining revenue ({revenue_growth_cagr*100:.1f}% CAGR)")
    
    if eps_growth_cagr > 0.12:
        score += 1.0
        evidence.append(f"Excellent EPS growth ({eps_growth_cagr*100:.1f}% CAGR)")
    elif eps_growth_cagr < 0.05:
        concerns.append(f"Weak EPS growth ({eps_growth_cagr*100:.1f}% CAGR)")
    
    if crisis_handling == "excellent":
        score += 1.0
        evidence.append("Excellent crisis management")
    elif crisis_handling == "poor":
        score -= 1.0
        concerns.append("Poor crisis management")
    
    if industry_experience > 20:
        score += 0.5
        evidence.append(f"Deep industry experience ({industry_experience} years)")
    
    return ManagementFactor(
        name="Track Record",
        score=max(0, min(10, score)),
        weight=0.25,
        evidence=evidence,
        concerns=concerns,
    )


def evaluate_compensation_alignment(data: dict[str, Any]) -> ManagementFactor:
    """Evaluate compensation alignment with shareholders."""
    score = 5.0
    evidence = []
    concerns = []
    
    ceo_ownership_pct = data.get("ceo_ownership_pct", 0)
    insider_ownership_pct = data.get("insider_ownership_pct", 0)
    compensation_structure = data.get("compensation_structure", "standard")
    performance_metrics = data.get("performance_metrics", [])
    
    if ceo_ownership_pct > 0.05:
        score += 1.5
        evidence.append(f"High CEO ownership ({ceo_ownership_pct*100:.1f}%)")
    elif ceo_ownership_pct < 0.001:
        concerns.append(f"Low CEO ownership ({ceo_ownership_pct*100:.2f}%)")
    
    if insider_ownership_pct > 0.10:
        score += 1.0
        evidence.append(f"High insider ownership ({insider_ownership_pct*100:.1f}%)")
    
    if compensation_structure == "performance_based":
        score += 1.0
        evidence.append("Performance-based compensation")
    elif compensation_structure == "excessive":
        score -= 1.0
        concerns.append("Excessive compensation")
    
    if "roe" in performance_metrics or "roic" in performance_metrics:
        score += 0.5
        evidence.append("Compensation tied to returns")
    
    if "share_price" in performance_metrics or "tsr" in performance_metrics:
        score += 0.5
        evidence.append("Compensation tied to shareholder returns")
    
    return ManagementFactor(
        name="Compensation Alignment",
        score=max(0, min(10, score)),
        weight=0.20,
        evidence=evidence,
        concerns=concerns,
    )


def evaluate_integrity(data: dict[str, Any]) -> ManagementFactor:
    """Evaluate management integrity and transparency."""
    score = 5.0
    evidence = []
    concerns = []
    
    accounting_quality = data.get("accounting_quality", "standard")
    regulatory_issues = data.get("regulatory_issues", [])
    related_party_transactions = data.get("related_party_transactions", "none")
    governance_rating = data.get("governance_rating", "standard")
    
    if accounting_quality == "conservative":
        score += 2.0
        evidence.append("Conservative accounting practices")
    elif accounting_quality == "aggressive":
        score -= 2.0
        concerns.append("Aggressive accounting practices")
    
    if regulatory_issues:
        score -= len(regulatory_issues) * 0.5
        concerns.extend([f"Regulatory issue: {issue}" for issue in regulatory_issues])
    else:
        score += 0.5
        evidence.append("No regulatory issues")
    
    if related_party_transactions == "none":
        score += 0.5
        evidence.append("No related party transactions")
    elif related_party_transactions == "significant":
        score -= 1.0
        concerns.append("Significant related party transactions")
    
    if governance_rating == "excellent":
        score += 1.0
        evidence.append("Excellent governance rating")
    elif governance_rating == "poor":
        score -= 1.0
        concerns.append("Poor governance rating")
    
    return ManagementFactor(
        name="Integrity & Transparency",
        score=max(0, min(10, score)),
        weight=0.15,
        evidence=evidence,
        concerns=concerns,
    )


def calculate_management_score(factors: list[ManagementFactor]) -> dict[str, Any]:
    """Calculate overall management score."""
    weighted_score = sum(f.score * f.weight for f in factors)
    
    if weighted_score >= 8:
        rating = "Excellent"
        description = "Management demonstrates exceptional quality and alignment"
    elif weighted_score >= 6:
        rating = "Good"
        description = "Management shows solid quality with some areas for improvement"
    elif weighted_score >= 4:
        rating = "Average"
        description = "Management quality is acceptable but not exceptional"
    else:
        rating = "Poor"
        description = "Management quality raises significant concerns"
    
    all_evidence = []
    all_concerns = []
    for f in factors:
        all_evidence.extend(f.evidence)
        all_concerns.extend(f.concerns)
    
    return {
        "score": round(weighted_score, 2),
        "rating": rating,
        "description": description,
        "strengths": all_evidence,
        "concerns": all_concerns,
        "factors": [
            {
                "name": f.name,
                "score": f.score,
                "weight": f.weight,
                "evidence": f.evidence,
                "concerns": f.concerns,
            }
            for f in factors
        ],
    }


def main(parameters: dict[str, Any]) -> dict[str, Any]:
    """Main entry point for management evaluation."""
    management_data = parameters.get("management_data", {})
    
    if not management_data:
        return {
            "success": False,
            "error": "No management data provided",
            "score": 0,
            "rating": "Unknown",
        }
    
    factors = [
        evaluate_capital_allocation(management_data),
        evaluate_shareholder_communication(management_data),
        evaluate_track_record(management_data),
        evaluate_compensation_alignment(management_data),
        evaluate_integrity(management_data),
    ]
    
    result = calculate_management_score(factors)
    result["success"] = True
    
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        params = json.loads(sys.argv[1])
    else:
        params = {}
    
    result = main(params)
    print(json.dumps(result, indent=2))
