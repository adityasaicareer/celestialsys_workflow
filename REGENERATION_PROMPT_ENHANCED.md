# Backend Agent Regeneration Prompt Enhanced

## Problem
Backend agent was repeating the same errors across attempts without fixing them:
1. SQLAlchemy sessionmaker type error
2. Incomplete CRUD operations  
3. Low pylint scores

## Solution
Enhanced `_get_regeneration_system_prompt()` with specific guidance for the exact errors encountered.

## New Guidance Added

### 1. SQLAlchemy 2.0 sessionmaker Fix
**Error:** `No overload variant of "sessionmaker" matches argument types`

**Guidance Added:**
```python
# ❌ WRONG - Old SQLAlchemy 1.4 syntax:
from sqlalchemy.orm import sessionmaker
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ✅ CORRECT - SQLAlchemy 2.0+ async syntax:
from sqlalchemy.ext.asyncio import async_sessionmaker
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

### 2. Complete CRUD Operations
**Error:** `CRUD operations incomplete`

**Guidance Added:**
- Explicitly states that GET alone is NOT sufficient
- Provides template for all 5 CRUD operations:
  - CREATE (POST)
  - READ (GET list + GET single)
  - UPDATE (PUT)
  - DELETE (DELETE)

### 3. Pylint Score Improvements
**Error:** `Pylint score 7.73 below threshold 8.0`

**Guidance Added:**
- Missing docstrings (add to ALL functions/classes)
- Unused imports (remove them)
- Lines too long (break at 100 chars)
- Missing type hints (add to ALL parameters and returns)
- Inconsistent naming (use snake_case for functions)

## Testing
✅ Backend Agent imports successfully
✅ Enhanced prompt compiles correctly
✅ No syntax errors in prompt strings

## Expected Behavior
On retry attempts (2-5), the LLM will now:
1. Use `async_sessionmaker` instead of `sessionmaker` with AsyncSession
2. Generate complete CRUD endpoints (POST, GET, PUT, DELETE)
3. Add proper docstrings and type hints to improve pylint score

## Files Modified
- `workflow/agents/backend_agent.py`
  - Enhanced `_get_regeneration_system_prompt()` method
  - Added 3 new critical error sections with examples

## Status
✅ **READY FOR TESTING**

The backend agent should now fix these specific errors on retry attempts instead of repeating them.

## Next Steps
Run the workflow again and monitor if:
1. Attempt 2 fixes the sessionmaker issue
2. Attempt 2 adds complete CRUD operations
3. Pylint score improves above 8.0
4. Agent successfully passes quality gates within 5 attempts
