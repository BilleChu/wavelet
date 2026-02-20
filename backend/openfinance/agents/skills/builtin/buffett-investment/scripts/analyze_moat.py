#!/usr/bin/env python
"""
Moat Analysis Script.

Analyzes a company's competitive moat based on:
1. Brand power
2. Network effects
3. Switching costs
4. Cost advantages
5. Intangible assets
"""

import json
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class MoatFactor:
    """A factor in moat analysis."""
    name: str
    score: float  # 0-10
    weight: float
    evidence: list[str]
    concerns: list[str]


def analyze_brand_power(data: dict[str, Any]) -> MoatFactor:
    """Analyze brand power and pricing power."""
    score = 5.0
    evidence = []
    concerns = []
    
    brand_recognition = data.get("brand_recognition", "unknown")
    pricing_power = data.get("pricing_power", "unknown")
    customer_loyalty = data.get("customer_loyalty_score", 5)
    market_share = data.get("market_share", 0)
    
    if brand_recognition == "dominant":
        score += 2.0
        evidence.append("Dominant brand recognition in key markets")
    elif brand_recognition == "strong":
        score += 1.0
        evidence.append("Strong brand recognition")
    elif brand_recognition == "weak":
        score -= 1.0
        concerns.append("Weak brand recognition")
    
    if pricing_power == "high":
        score += 2.0
        evidence.append("Ability to raise prices without losing customers")
    elif pricing_power == "moderate":
        score += 0.5
        evidence.append("Some pricing flexibility")
    elif pricing_power == "low":
        concerns.append("Limited pricing power")
    
    if customer_loyalty > 8:
        score += 1.0
        evidence.append(f"High customer loyalty score ({customer_loyalty}/10)")
    elif customer_loyalty < 4:
        concerns.append(f"Low customer loyalty score ({customer_loyalty}/10)")
    
    if market_share > 0.3:
        score += 1.0
        evidence.append(f"Dominant market share ({market_share*100:.1f}%)")
    
    return MoatFactor(
        name="Brand Power",
        score=max(0, min(10, score)),
        weight=0.25,
        evidence=evidence,
        concerns=concerns,
    )


def analyze_network_effects(data: dict[str, Any]) -> MoatFactor:
    """Analyze network effects."""
    score = 5.0
    evidence = []
    concerns = []
    
    user_growth_rate = data.get("user_growth_rate", 0)
    network_density = data.get("network_density", "unknown")
    platform_users = data.get("platform_users", 0)
    viral_coefficient = data.get("viral_coefficient", 0)
    
    if network_density == "high":
        score += 2.0
        evidence.append("Strong network effects with high user interdependence")
    elif network_density == "moderate":
        score += 1.0
        evidence.append("Moderate network effects")
    
    if user_growth_rate > 0.2:
        score += 1.0
        evidence.append(f"Strong user growth ({user_growth_rate*100:.1f}%)")
    elif user_growth_rate < 0:
        concerns.append(f"Declining user base ({user_growth_rate*100:.1f}%)")
    
    if viral_coefficient > 1.0:
        score += 1.5
        evidence.append(f"Viral growth (coefficient: {viral_coefficient:.2f})")
    
    if platform_users > 1_000_000_000:
        score += 0.5
        evidence.append("Massive user base (1B+)")
    
    return MoatFactor(
        name="Network Effects",
        score=max(0, min(10, score)),
        weight=0.20,
        evidence=evidence,
        concerns=concerns,
    )


def analyze_switching_costs(data: dict[str, Any]) -> MoatFactor:
    """Analyze switching costs."""
    score = 5.0
    evidence = []
    concerns = []
    
    switching_cost_level = data.get("switching_cost_level", "unknown")
    integration_depth = data.get("integration_depth", "unknown")
    data_lock_in = data.get("data_lock_in", False)
    contract_length = data.get("avg_contract_length_months", 0)
    
    if switching_cost_level == "high":
        score += 2.5
        evidence.append("High switching costs for customers")
    elif switching_cost_level == "moderate":
        score += 1.0
        evidence.append("Moderate switching costs")
    elif switching_cost_level == "low":
        concerns.append("Low switching costs - customers can easily leave")
    
    if integration_depth == "deep":
        score += 1.5
        evidence.append("Deep integration into customer workflows")
    elif integration_depth == "shallow":
        concerns.append("Shallow integration - easy to replace")
    
    if data_lock_in:
        score += 1.0
        evidence.append("Customer data creates lock-in")
    
    if contract_length > 24:
        score += 0.5
        evidence.append(f"Long contract terms ({contract_length} months avg)")
    
    return MoatFactor(
        name="Switching Costs",
        score=max(0, min(10, score)),
        weight=0.20,
        evidence=evidence,
        concerns=concerns,
    )


def analyze_cost_advantages(data: dict[str, Any]) -> MoatFactor:
    """Analyze cost advantages."""
    score = 5.0
    evidence = []
    concerns = []
    
    gross_margin = data.get("gross_margin", 0)
    operating_margin = data.get("operating_margin", 0)
    scale_advantage = data.get("scale_advantage", False)
    proprietary_tech = data.get("proprietary_technology", False)
    distribution_advantage = data.get("distribution_advantage", False)
    
    if gross_margin > 0.5:
        score += 1.5
        evidence.append(f"High gross margin ({gross_margin*100:.1f}%)")
    elif gross_margin < 0.25:
        concerns.append(f"Low gross margin ({gross_margin*100:.1f}%)")
    
    if operating_margin > 0.2:
        score += 1.0
        evidence.append(f"Strong operating margin ({operating_margin*100:.1f}%)")
    elif operating_margin < 0.1:
        concerns.append(f"Weak operating margin ({operating_margin*100:.1f}%)")
    
    if scale_advantage:
        score += 1.0
        evidence.append("Scale advantages vs competitors")
    
    if proprietary_tech:
        score += 1.0
        evidence.append("Proprietary technology reduces costs")
    
    if distribution_advantage:
        score += 0.5
        evidence.append("Distribution network advantages")
    
    return MoatFactor(
        name="Cost Advantages",
        score=max(0, min(10, score)),
        weight=0.20,
        evidence=evidence,
        concerns=concerns,
    )


def analyze_intangible_assets(data: dict[str, Any]) -> MoatFactor:
    """Analyze intangible assets."""
    score = 5.0
    evidence = []
    concerns = []
    
    patents_count = data.get("patents_count", 0)
    patents_quality = data.get("patents_quality", "unknown")
    regulatory_moat = data.get("regulatory_moat", False)
    licenses = data.get("exclusive_licenses", False)
    trade_secrets = data.get("trade_secrets_value", "unknown")
    
    if patents_count > 1000:
        score += 1.5
        evidence.append(f"Large patent portfolio ({patents_count} patents)")
    elif patents_count > 100:
        score += 0.5
        evidence.append(f"Significant patent portfolio ({patents_count} patents)")
    
    if patents_quality == "high":
        score += 1.0
        evidence.append("High-quality, defensible patents")
    elif patents_quality == "low":
        concerns.append("Patents may be easily circumvented")
    
    if regulatory_moat:
        score += 2.0
        evidence.append("Regulatory barriers to entry")
    
    if licenses:
        score += 1.5
        evidence.append("Exclusive licenses create barriers")
    
    if trade_secrets == "high":
        score += 1.0
        evidence.append("Valuable trade secrets")
    
    return MoatFactor(
        name="Intangible Assets",
        score=max(0, min(10, score)),
        weight=0.15,
        evidence=evidence,
        concerns=concerns,
    )


def calculate_moat_score(factors: list[MoatFactor]) -> dict[str, Any]:
    """Calculate overall moat score."""
    weighted_score = sum(f.score * f.weight for f in factors)
    
    if weighted_score >= 8:
        rating = "Wide"
        description = "Very durable competitive advantage"
    elif weighted_score >= 6:
        rating = "Narrow"
        description = "Moderate competitive advantage"
    else:
        rating = "None"
        description = "Limited competitive advantage"
    
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
    """Main entry point for moat analysis."""
    company_data = parameters.get("company_data", {})
    
    if not company_data:
        return {
            "success": False,
            "error": "No company data provided",
            "score": 0,
            "rating": "Unknown",
        }
    
    factors = [
        analyze_brand_power(company_data),
        analyze_network_effects(company_data),
        analyze_switching_costs(company_data),
        analyze_cost_advantages(company_data),
        analyze_intangible_assets(company_data),
    ]
    
    result = calculate_moat_score(factors)
    result["success"] = True
    
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        params = json.loads(sys.argv[1])
    else:
        params = {}
    
    result = main(params)
    print(json.dumps(result, indent=2))
