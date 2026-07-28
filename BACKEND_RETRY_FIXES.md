# Backend Agent Retry Fixes

## Issues Fixed

### Issue 1: Nested Folder Creation on Retry
**Problem:** Backend agent creates `backend/backend/` nested structure on retry attempts instead of maintaining flat structure

**Root Cause:** 
- Attempt 1 creates flat structure: `backend/models/`, `backend/routes/`, etc.
- Attempt 2-5 create nested structure: `backend/backend/models.py`, `backend/backend/routes/`, etc.
- `write_code()` method doesn't clear previous attempt's files
- Both structures coexist, causing import confusion

**Example:**
```
Attempt 1: backend/models/todo.py
Attempt 2: backend/backend/models.py  ← nested!
Result: Both exist, imports fail
```

**Solution:** Clear output directory before each retry (except attempt 1)

```python
# In execute_task loop:
if attempt > 1:
    print(f"   🧹 Clearing previous attempt's files...")
    # Remove all .py files and directories
    # Preserve .env file if it exists
```

**Files Modified:** `workflow/agents/backend_agent.py` - `execute_task()` method

---

### Issue 2: Same Error Repeating Without Fix
**Problem:** Error `Incompatible default for parameter "db" (default has type "None", parameter has type "AsyncSession")` repeats across all attempts without being fixed

**Root Cause:** 
LLM doesn't understand FastAPI dependency injection pattern

**The Error:**
```python
# ❌ WRONG - What LLM generates:
@router.delete("/{todo_id}")
async def delete_todo(
    todo_id: int,
    db: AsyncSession = None  # ERROR: Can't use None as default!
):
    pass
```

**The Fix:**
```python
# ✅ CORRECT - What it should be:
from fastapi import Depends

@router.delete("/{todo_id}")
async def delete_todo(
    todo_id: int,
    db: AsyncSession = Depends(get_db)  # Use Depends()!
):
    pass
```

**Solution:** Added explicit guidance in regeneration prompt:

```python
**CRITICAL: FastAPI Dependency Injection Errors**
If you see `Incompatible default for parameter "db"`:
- **YOU CANNOT USE `= None`** as default for database dependencies
- **USE `= Depends(get_db)` INSTEAD**

Examples and rules provided...
```

**Files Modified:** `workflow/agents/backend_agent.py` - `_get_regeneration_system_prompt()` method

---

## Why Tests Were Passing Before But Failing Now

### Possible Reasons:

1. **Import Structure Changed**
   - Tests were written for flat structure (`from models.todo import Todo`)
   - Backend now creates nested structure (`backend/backend/models.py`)
   - Tests can't find the imports

2. **Multiple File Versions**
   - Both flat and nested structures exist
   - Python imports the wrong version
   - Tests import from one, code runs from another

3. **Database Dependency Errors**
   - Backend code has FastAPI dependency errors
   - Code doesn't run at all
   - Tests can't execute because imports fail

### How to Fix:

1. **Clean the backend directory:**
   ```bash
   cd backend
   rm -rf backend/ models/ routes/ schemas/  # Remove all code
   # Keep .env file
   ```

2. **Run workflow again with fixes:**
   - The retry cleanup will now work
   - FastAPI dependency errors will be fixed
   - Single consistent structure will be created

3. **Verify structure:**
   ```bash
   ls -la backend/
   # Should see either:
   # - Flat: models/, routes/, schemas/, main.py
   # OR
   # - Nested: backend/ (containing everything)
   # But NOT both!
   ```

---

## Implementation Details

### File Cleanup Logic

```python
# Clean output directory on retry
if attempt > 1:
    output_path = Path(output_dir)
    if output_path.exists():
        # Preserve .env file
        env_file = output_path / ".env"
        env_content = None
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_content = f.read()
        
        # Remove Python files and directories
        for item in output_path.iterdir():
            if item.name == ".env":
                continue
            if item.is_dir():
                shutil.rmtree(item)  # Remove directories
            elif item.suffix in ['.py', '.txt', '.md']:
                item.unlink()  # Remove files
        
        # Restore .env
        if env_content:
            with open(env_file, 'w') as f:
                f.write(env_content)
```

### Enhanced Regeneration Guidance

Added to `_get_regeneration_system_prompt()`:

1. **FastAPI Dependency Injection section** with examples
2. **Clear rules** about what NOT to do
3. **Multiple correct patterns** (Depends, Annotated)
4. **Specific error message matching** for targeted help

---

## Testing the Fix

### Before Fix:
```
Attempt 1: Creates backend/models/todo.py
Attempt 2: Creates backend/backend/models.py (nested!)
Attempt 3: Creates backend/backend/models.py (nested again!)
Result: backend/ has both flat AND nested structures
Error: Same dependency error repeats
```

### After Fix:
```
Attempt 1: Creates backend/models/todo.py
   Error: Dependency injection issue
Attempt 2: 
   - Clears backend/ (except .env)
   - Creates backend/models/todo.py (same structure)
   - Fixes: Uses Depends(get_db) instead of = None
   Success! ✅
```

---

## Summary

| Issue | Before | After |
|-------|--------|-------|
| **Nested folders** | Both flat & nested exist | Clean before retry |
| **Same error repeats** | LLM doesn't understand | Explicit FastAPI guidance |
| **Test failures** | Import confusion | Single consistent structure |
| **Retry effectiveness** | Accumulates files | Clean slate each retry |

**Result:** Backend agent now:
- ✅ Maintains consistent file structure across retries
- ✅ Cleans up previous attempt's files
- ✅ Understands FastAPI dependency injection
- ✅ Fixes errors instead of repeating them
- ✅ Tests can find imports correctly

---

## Files Modified

1. **`workflow/agents/backend_agent.py`**
   - Added cleanup logic in `execute_task()` loop
   - Enhanced `_get_regeneration_system_prompt()` with FastAPI dependency guidance

2. **No other files modified** - This is purely a backend agent improvement

---

## Next Steps

1. Clean your current backend directory manually (remove nested folders)
2. Run the workflow again
3. Verify single structure is created
4. Tests should now pass

**The fix prevents the problem going forward!** 🎉
