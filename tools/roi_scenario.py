"""Hypothetical scenario arithmetic only; no measured savings or business recommendation."""

import argparse
import json
import math


def scenario(cases, minutes_saved, hourly_cost, monthly_cost, implementation_cost, months):
    values = (cases, minutes_saved, hourly_cost, monthly_cost, implementation_cost, months)
    if (
        not all(math.isfinite(v) for v in values)
        or min(cases, hourly_cost, monthly_cost, implementation_cost) < 0
        or months <= 0
    ):
        raise ValueError("Finite assumptions and nonnegative costs/cases, positive months required")
    monthly_value = cases * minutes_saved / 60 * hourly_cost
    total_cost = implementation_cost + monthly_cost * months
    net_value = monthly_value * months - total_cost
    return {
        "status": "HYPOTHETICAL_ASSUMPTIONS_NOT_OBSERVED_ROI",
        "assumptions": dict(
            cases_per_month=cases,
            minutes_saved_per_case=minutes_saved,
            hourly_cost=hourly_cost,
            monthly_operating_cost=monthly_cost,
            implementation_cost=implementation_cost,
            months=months,
        ),
        "currency": "same user-chosen currency for every cost input",
        "monthly_labor_value_assumed": monthly_value,
        "total_cost_assumed": total_cost,
        "net_value_assumed": net_value,
        "roi_fraction_assumed": net_value / total_cost if total_cost else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "cases",
        "minutes-saved",
        "hourly-cost",
        "monthly-cost",
        "implementation-cost",
        "months",
    ):
        parser.add_argument("--" + name, type=float, required=True)
    a = parser.parse_args()
    print(
        json.dumps(
            scenario(
                a.cases,
                a.minutes_saved,
                a.hourly_cost,
                a.monthly_cost,
                a.implementation_cost,
                a.months,
            ),
            indent=2,
        )
    )
