"""
Clarity financial data MCP server.

Exposes tools for reading transaction data and computing
spending signals. Never returns raw transaction descriptions —
only derived signals (category, amount, date).
"""

from fastmcp import FastMCP
from datetime import date, timedelta
from pathlib import Path
import csv
import json

mcp = FastMCP(
    name="clarity-financial"
)


def _load_transactions(csv_path: str) -> list[dict]:
    """Load transactions from CSV. Returns list of dicts."""
    path = Path(csv_path)
    if not path.exists():
        return []

    transactions = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            transactions.append(row)
    return transactions


def _classify_category(description: str) -> str:
    """
    Classify a transaction description into a Clarity category.
    Discards the description after classification — never returned.
    """
    desc = description.lower()

    if any(k in desc for k in ["uber eats", "deliveroo", "doordash",
                                "just eat", "food delivery", "grubhub"]):
        return "food_delivery"
    if any(k in desc for k in ["grocery", "supermarket", "whole foods",
                                "trader joe", "tesco", "sainsbury"]):
        return "groceries"
    if any(k in desc for k in ["rent", "mortgage", "landlord"]):
        return "housing"
    if any(k in desc for k in ["netflix", "spotify", "disney",
                                "apple music", "hulu", "subscription"]):
        return "subscriptions"
    if any(k in desc for k in ["gym", "fitness", "yoga", "crossfit"]):
        return "fitness"
    if any(k in desc for k in ["pharmacy", "doctor", "hospital",
                                "medical", "dental"]):
        return "health"
    if any(k in desc for k in ["bar", "pub", "restaurant", "cafe",
                                "coffee", "dining"]):
        return "dining_out"
    if any(k in desc for k in ["amazon", "ebay", "shopping", "online"]):
        return "shopping"
    if any(k in desc for k in ["transport", "uber", "lyft", "taxi",
                                "train", "bus", "fuel", "petrol"]):
        return "transport"

    return "other"


@mcp.tool()
def get_weekly_spending(
    week_start: str,
    csv_path: str = "data/transactions.csv",
) -> dict:
    """
    Get spending signals for a specific week.

    Args:
        week_start: Monday date of the week (YYYY-MM-DD)
        csv_path: Path to transactions CSV file

    Returns:
        Spending signals by category — never raw descriptions
    """
    try:
        start = date.fromisoformat(week_start)
    except ValueError:
        return {"error": f"Invalid date format: {week_start}. Use YYYY-MM-DD"}

    end = start + timedelta(days=6)
    transactions = _load_transactions(csv_path)

    weekly = [
        t for t in transactions
        if start <= date.fromisoformat(t.get("date", "1900-01-01")) <= end
    ]

    by_category: dict[str, float] = {}
    daily_totals: dict[str, float] = {}

    for t in weekly:
        category = _classify_category(t.get("description", ""))
        amount = float(t.get("amount", 0))
        tx_date = t.get("date", "")
        day = date.fromisoformat(tx_date).strftime("%a") if tx_date else "Unknown"

        by_category[category] = round(by_category.get(category, 0) + amount, 2)
        daily_totals[day] = round(daily_totals.get(day, 0) + amount, 2)

    total = round(sum(by_category.values()), 2)

    return {
        "week_start": week_start,
        "week_end": end.isoformat(),
        "total_spend": total,
        "by_category": by_category,
        "daily_totals": daily_totals,
        "transaction_count": len(weekly),
        "high_spend_categories": [
            cat for cat, amt in by_category.items()
            if amt > total * 0.25  # categories over 25% of weekly spend
        ],
    }


@mcp.tool()
def get_monthly_average(
    csv_path: str = "data/transactions.csv",
    months: int = 3,
) -> dict:
    """
    Get average weekly spending over the last N months.
    Used to compute spend_vs_budget_pct in weekly snapshots.

    Args:
        csv_path: Path to transactions CSV file
        months: Number of months to average over (default 3)

    Returns:
        Average weekly spend by category
    """
    transactions = _load_transactions(csv_path)
    if not transactions:
        return {"error": "No transaction data found", "average_weekly_spend": 0}

    cutoff = date.today() - timedelta(days=months * 30)
    recent = [
        t for t in transactions
        if date.fromisoformat(t.get("date", "1900-01-01")) >= cutoff
    ]

    if not recent:
        return {"average_weekly_spend": 0, "by_category": {}}

    total = sum(float(t.get("amount", 0)) for t in recent)
    weeks = max((months * 30) / 7, 1)
    avg_weekly = round(total / weeks, 2)

    by_category: dict[str, float] = {}
    for t in recent:
        cat = _classify_category(t.get("description", ""))
        by_category[cat] = round(
            by_category.get(cat, 0) + float(t.get("amount", 0)), 2
        )

    avg_by_category = {
        cat: round(amt / weeks, 2)
        for cat, amt in by_category.items()
    }

    return {
        "months_analysed": months,
        "average_weekly_spend": avg_weekly,
        "by_category": avg_by_category,
    }


@mcp.tool()
def get_stress_signals(
    week_start: str,
    csv_path: str = "data/transactions.csv",
) -> dict:
    """
    Get financial stress signals for a specific week.
    Cross-references spending patterns with known stress indicators.

    Args:
        week_start: Monday date of the week (YYYY-MM-DD)
        csv_path: Path to transactions CSV file

    Returns:
        Stress signals — food delivery spikes, late-night purchases, etc.
    """
    weekly = get_weekly_spending(week_start, csv_path)
    monthly_avg = get_monthly_average(csv_path)

    if "error" in weekly:
        return weekly

    signals = []

    # Food delivery spike (strong depletion signal)
    food_delivery = weekly["by_category"].get("food_delivery", 0)
    avg_food_delivery = monthly_avg["by_category"].get("food_delivery", 0)
    if avg_food_delivery > 0 and food_delivery > avg_food_delivery * 1.5:
        signals.append({
            "type": "food_delivery_spike",
            "severity": "HIGH",
            "detail": f"Food delivery {round(food_delivery / avg_food_delivery * 100)}% above average",
        })

    # Overall overspend
    avg_weekly = monthly_avg["average_weekly_spend"]
    total = weekly["total_spend"]
    if avg_weekly > 0:
        pct_over = round((total - avg_weekly) / avg_weekly * 100)
        if pct_over > 40:
            signals.append({
                "type": "overall_overspend",
                "severity": "MEDIUM",
                "detail": f"Total spend {pct_over}% above monthly average",
            })

    return {
        "week_start": week_start,
        "stress_signals": signals,
        "spend_vs_average_pct": round(
            (total - avg_weekly) / avg_weekly * 100
        ) if avg_weekly > 0 else 0,
    }


if __name__ == "__main__":
    mcp.run()