#!/usr/bin/env python
"""
Intrinsic Value Calculator.

Calculates intrinsic value using multiple methods:
1. Discounted Cash Flow (DCF)
2. Dividend Discount Model (DDM)
3. Earnings Power Value (EPV)
"""

import json
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class DCFInputs:
    """Inputs for DCF calculation."""
    current_fcf: float
    growth_rate: float
    terminal_growth: float
    discount_rate: float
    years: int


@dataclass
class DDMInputs:
    """Inputs for DDM calculation."""
    current_dividend: float
    growth_rate: float
    required_return: float


def calculate_dcf(inputs: DCFInputs) -> dict[str, Any]:
    """Calculate intrinsic value using DCF."""
    fcf_projections = []
    cumulative_pv = 0.0
    
    current_fcf = inputs.current_fcf
    
    for year in range(1, inputs.years + 1):
        projected_fcf = current_fcf * ((1 + inputs.growth_rate) ** year)
        discount_factor = (1 + inputs.discount_rate) ** year
        pv_fcf = projected_fcf / discount_factor
        
        fcf_projections.append({
            "year": year,
            "fcf": round(projected_fcf, 2),
            "pv": round(pv_fcf, 2),
        })
        cumulative_pv += pv_fcf
    
    terminal_fcf = current_fcf * ((1 + inputs.growth_rate) ** inputs.years)
    terminal_fcf_growth = terminal_fcf * (1 + inputs.terminal_growth)
    terminal_value = terminal_fcf_growth / (inputs.discount_rate - inputs.terminal_growth)
    pv_terminal = terminal_value / ((1 + inputs.discount_rate) ** inputs.years)
    
    enterprise_value = cumulative_pv + pv_terminal
    
    return {
        "method": "DCF",
        "projected_fcf": fcf_projections,
        "terminal_value": round(terminal_value, 2),
        "pv_terminal": round(pv_terminal, 2),
        "pv_operating": round(cumulative_pv, 2),
        "enterprise_value": round(enterprise_value, 2),
        "assumptions": {
            "initial_fcf": inputs.current_fcf,
            "growth_rate": inputs.growth_rate,
            "terminal_growth": inputs.terminal_growth,
            "discount_rate": inputs.discount_rate,
            "projection_years": inputs.years,
        },
    }


def calculate_ddm(inputs: DDMInputs) -> dict[str, Any]:
    """Calculate intrinsic value using DDM."""
    if inputs.required_return <= inputs.growth_rate:
        return {
            "method": "DDM",
            "error": "Required return must exceed growth rate",
            "intrinsic_value": 0,
        }
    
    intrinsic_value = inputs.current_dividend * (1 + inputs.growth_rate) / (inputs.required_return - inputs.growth_rate)
    
    return {
        "method": "DDM",
        "intrinsic_value": round(intrinsic_value, 2),
        "assumptions": {
            "current_dividend": inputs.current_dividend,
            "growth_rate": inputs.growth_rate,
            "required_return": inputs.required_return,
        },
    }


def calculate_epv(
    normalized_earnings: float,
    discount_rate: float,
    growth_rate: float = 0.0,
) -> dict[str, Any]:
    """Calculate Earnings Power Value."""
    if growth_rate > 0:
        epv = normalized_earnings * (1 + growth_rate) / (discount_rate - growth_rate)
    else:
        epv = normalized_earnings / discount_rate
    
    return {
        "method": "EPV",
        "epv": round(epv, 2),
        "assumptions": {
            "normalized_earnings": normalized_earnings,
            "discount_rate": discount_rate,
            "growth_rate": growth_rate,
        },
    }


def calculate_intrinsic_value(
    financial_data: dict[str, Any],
    method: str = "dcf",
) -> dict[str, Any]:
    """Calculate intrinsic value per share."""
    results = {}
    
    shares_outstanding = financial_data.get("shares_outstanding", 1)
    net_debt = financial_data.get("net_debt", 0)
    cash = financial_data.get("cash", 0)
    
    if method in ["dcf", "all"]:
        dcf_inputs = DCFInputs(
            current_fcf=financial_data.get("free_cash_flow", 0),
            growth_rate=financial_data.get("growth_rate", 0.05),
            terminal_growth=financial_data.get("terminal_growth", 0.025),
            discount_rate=financial_data.get("wacc", 0.10),
            years=financial_data.get("projection_years", 10),
        )
        
        if dcf_inputs.current_fcf > 0:
            dcf_result = calculate_dcf(dcf_inputs)
            equity_value = dcf_result["enterprise_value"] - net_debt + cash
            dcf_result["equity_value"] = round(equity_value, 2)
            dcf_result["intrinsic_value_per_share"] = round(equity_value / shares_outstanding, 2)
            results["dcf"] = dcf_result
    
    if method in ["ddm", "all"]:
        dividend = financial_data.get("dividend_per_share", 0)
        if dividend > 0:
            ddm_inputs = DDMInputs(
                current_dividend=dividend,
                growth_rate=financial_data.get("dividend_growth_rate", 0.03),
                required_return=financial_data.get("required_return", 0.10),
            )
            ddm_result = calculate_ddm(ddm_inputs)
            results["ddm"] = ddm_result
    
    if method in ["epv", "all"]:
        normalized_earnings = financial_data.get("normalized_eps", 0)
        if normalized_earnings > 0:
            epv_result = calculate_epv(
                normalized_earnings=normalized_earnings,
                discount_rate=financial_data.get("required_return", 0.10),
            )
            results["epv"] = epv_result
    
    if results:
        values = []
        if "dcf" in results and "intrinsic_value_per_share" in results["dcf"]:
            values.append(results["dcf"]["intrinsic_value_per_share"])
        if "ddm" in results and "intrinsic_value" in results["ddm"]:
            values.append(results["ddm"]["intrinsic_value"])
        if "epv" in results and "epv" in results["epv"]:
            values.append(results["epv"]["epv"])
        
        if values:
            avg_value = sum(values) / len(values)
            results["average_intrinsic_value"] = round(avg_value, 2)
    
    return results


def calculate_margin_of_safety(
    intrinsic_value: float,
    current_price: float,
) -> dict[str, Any]:
    """Calculate margin of safety."""
    if current_price <= 0:
        return {
            "margin_of_safety": 0,
            "discount_to_intrinsic": 0,
            "upside_potential": 0,
        }
    
    margin = (intrinsic_value - current_price) / intrinsic_value
    discount = (intrinsic_value - current_price) / current_price
    
    return {
        "intrinsic_value": round(intrinsic_value, 2),
        "current_price": round(current_price, 2),
        "margin_of_safety": round(margin * 100, 2),
        "discount_to_intrinsic": round(discount * 100, 2),
        "upside_potential": round(discount * 100, 2),
        "is_undervalued": margin > 0.25,
    }


def main(parameters: dict[str, Any]) -> dict[str, Any]:
    """Main entry point for intrinsic value calculation."""
    financial_data = parameters.get("financial_data", {})
    current_price = parameters.get("current_price", 0)
    method = parameters.get("method", "all")
    
    if not financial_data:
        return {
            "success": False,
            "error": "No financial data provided",
        }
    
    results = calculate_intrinsic_value(financial_data, method)
    
    if "average_intrinsic_value" in results:
        mos = calculate_margin_of_safety(
            results["average_intrinsic_value"],
            current_price,
        )
        results["margin_of_safety_analysis"] = mos
    
    results["success"] = True
    
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        params = json.loads(sys.argv[1])
    else:
        params = {}
    
    result = main(params)
    print(json.dumps(result, indent=2))
