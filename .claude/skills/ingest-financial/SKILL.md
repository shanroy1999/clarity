---
name: ingest-financial
description: >
  Processes financial data from the clarity-financial MCP server into
  Clarity's spending signals schema. Use after get_weekly_spending and
  get_stress_signals have been called. Triggers automatically when
  financial MCP data is present in context.
invocation: auto
allowed-tools:
  - Read
  - Write
  - mcp__clarity-financial__get_weekly_spending
  - mcp__clarity-financial__get_monthly_average
  - mcp__clarity-financial__get_stress_signals
---

# Financial ingestion playbook

## Privacy rule
Never store merchant names, transaction descriptions, or any raw
transaction content. Store only derived signals: category totals,
percentages, and stress flags.

## Steps

1. Fetch weekly spending via MCP
   Call mcp__clarity-financial__get_weekly_spending with the
   current week_start date.

2. Fetch monthly average via MCP
   Call mcp__clarity-financial__get_monthly_average to get baseline.

3. Fetch stress signals via MCP
   Call mcp__clarity-financial__get_stress_signals for the week.

4. Compute spend_vs_budget_pct
   Formula: ((weekly_total - monthly_avg) / monthly_avg) * 100
   Round to 1 decimal place.

5. Write output
   Write to .clarity-cache/finance-{YYYY-MM-DD}.json

## Output schema

```json
{
  "week_start": "YYYY-MM-DD",
  "total_spend": 0.00,
  "spend_vs_budget_pct": 0.0,
  "by_category": {
    "food_delivery": 0.00,
    "groceries": 0.00,
    "dining_out": 0.00,
    "transport": 0.00,
    "subscriptions": 0.00,
    "shopping": 0.00,
    "health": 0.00,
    "fitness": 0.00,
    "housing": 0.00,
    "other": 0.00
  },
  "high_spend_categories": [],
  "stress_signals": [],
  "transaction_count": 0
}
```

## Never store
- Merchant names or descriptions
- Individual transaction amounts
- Any free-text from the transaction data
