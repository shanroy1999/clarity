# Backend rules — FastAPI + Python 3.11

## Route conventions
- All routes in src/routes/ one file per domain
- Always use Pydantic models for request and response
- Return consistent error shapes: {error: str, detail: str}
- Log every request with structlog

## Database
- All DB operations through src/db/ layer — never raw SQL in routes
- Use Supabase client from src/db/client.py
- Always use transactions for multi-step operations

## Testing
- Every route needs at least one happy path and one error test
- Use pytest-asyncio for async tests
- Test file mirrors source file: src/routes/reports.py → tests/routes/test_reports.py
