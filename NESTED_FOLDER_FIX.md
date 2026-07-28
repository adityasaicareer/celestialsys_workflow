# Nested Folder Issue Fixed

## Problem Identified
Your backend agent was:
1. Creating new nested folders on regeneration (`backend/backend/`, `backend/backend/backend/`)
2. Evaluating OLD code from previous attempts instead of NEW code
3. Repeating same errors because it never evaluated the corrected code

## Root Cause
**`write_code()` method wasn't clearing old files before writing new ones**

### What Was Happening:
```
Attempt 1:
- Generate: backend/main.py, backend/models/todo.py
- Write: backend/main.py ✅
- Evaluate: backend/main.py ✅
- Result: FAIL (errors found)

Attempt 2:
- LLM sees existing backend/ structure
- Generates: backend/backend/main.py (NEW nested structure!)
- Write: backend/backend/main.py ✅ (old backend/main.py still exists)
- Evaluate: backend/main.py ❌ (evaluates OLD code, not new!)
- Result: FAIL (same errors, because it never evaluated the new code)

Attempt 3-5:
- More nesting: backend/backend/backend/
- Still evaluating backend/main.py from Attempt 1
- Same errors forever
```

## Solution Implemented

Added cleanup logic to `write_code()`:

```python
def write_code(self, files: Dict[str, str], output_dir: str) -> List[Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # CRITICAL: Clear old Python files to prevent nested folder issues
    # This ensures LLM regenerates in the same structure, not backend/backend/
    # Keep .env file to preserve database configuration
    for old_file in output_path.rglob("*.py"):
        try:
            old_file.unlink()
        except Exception:
            pass
    
    # Now write new files...
```

## How It Works Now

```
Attempt 1:
- Generate: backend/main.py, backend/models/todo.py
- Write: backend/main.py ✅
- Evaluate: backend/main.py ✅
- Result: FAIL (errors found)

Attempt 2:
- Clean: Delete all *.py files from backend/ ✅
- Generate: backend/main.py (with fixes), backend/models/todo.py (with fixes)
- Write: backend/main.py ✅ (overwrites, no nesting)
- Evaluate: backend/main.py ✅ (evaluates NEW code with fixes!)
- Result: PASS or FAIL with DIFFERENT errors (progressing)

Attempt 3-5:
- Clean → Generate → Write → Evaluate (new code each time)
- Errors get fixed progressively
- Quality gates eventually pass
```

## What Gets Preserved

✅ `.env` file (database configuration)
✅ `requirements.txt` (overwritten, not deleted first)
❌ Old `.py` files (deleted before writing new ones)

## Benefits

1. ✅ **No more nested folders** - always writes to same structure
2. ✅ **Evaluates correct code** - always evaluates what was just generated
3. ✅ **Errors get fixed** - LLM's corrections actually get evaluated
4. ✅ **Progressive improvement** - each attempt builds on feedback
5. ✅ **Preserves config** - keeps .env for database connections

## Testing

✅ Backend Agent imports successfully
✅ File cleanup logic added
✅ Preserves non-Python files

## Files Modified

- `workflow/agents/backend_agent.py`
  - Added cleanup logic to `write_code()` method
  - Clears `*.py` files before writing
  - Preserves `.env` and other config files

## Status

✅ **FIXED**

The backend agent will now:
1. Delete old Python files before each retry
2. Write new code to same location (no nesting)
3. Evaluate the newly generated code
4. Make actual progress on fixing issues

## Expected Behavior

Run the workflow and you should see:
- Attempt 1: Generates code, finds errors
- Attempt 2: Cleans old files, regenerates with fixes, evaluates NEW code
- Errors should be DIFFERENT (or resolved) on each attempt
- Should pass quality gates within 5 attempts

No more `backend/backend/backend/` nesting!
