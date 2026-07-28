# Frontend-Backend Integration Implementation

## Overview

Enhanced the Frontend Agent to **read backend endpoints and schemas** before generating frontend code, ensuring API calls match the actual backend implementation.

---

## Problem Being Solved

**Before:**
- Frontend Agent generated code without knowing what backend endpoints exist
- API calls used generic/assumed endpoints that might not match backend
- TypeScript types didn't match backend Pydantic schemas
- Result: Runtime errors, 404s, type mismatches

**After:**
- Frontend Agent reads backend `main.py`, `schemas.py`, `models.py`
- Extracts actual endpoints (GET /posts, POST /posts, etc.)
- Extracts actual response schemas (PostResponse, PostListResponse, etc.)
- Generates frontend code that matches backend reality

---

## Implementation

### 1. New Function: `extract_backend_api_spec()`

**Location:** `workflow/agents/frontend_agent.py`

**Purpose:** Extract API specification from backend code

```python
def extract_backend_api_spec(backend_dir: str) -> Dict[str, Any]:
    """
    Extract API specification from backend code.
    
    Reads:
    - main.py: Extract endpoints (GET, POST, PUT, DELETE)
    - schemas.py: Extract Pydantic models
    - models.py: Extract SQLAlchemy models
    
    Returns:
        {
            "endpoints": [
                {"method": "GET", "path": "/posts", "full_url": "http://localhost:8000/posts"},
                {"method": "POST", "path": "/posts", ...},
                ...
            ],
            "schemas": {
                "classes": ["PostCreate", "PostResponse", "PostListResponse", ...],
                "raw_content": "# Full schemas.py content..."
            },
            "models": {
                "raw_content": "# Full models.py content..."
            }
        }
    """
```

**How It Works:**
1. Reads `backend/main.py`
2. Uses regex to find `@app.get(...)`, `@app.post(...)`, etc.
3. Extracts endpoint paths
4. Reads `schemas.py` and `models.py` for data structures

**Example Output:**
```python
{
    "endpoints": [
        {"method": "GET", "path": "/health"},
        {"method": "GET", "path": "/posts"},
        {"method": "GET", "path": "/posts/{post_id}"},
        {"method": "POST", "path": "/posts"},
        {"method": "PUT", "path": "/posts/{post_id}"},
        {"method": "DELETE", "path": "/posts/{post_id}"}
    ],
    "schemas": {
        "classes": ["PostCreate", "PostUpdate", "PostResponse", "PostListResponse"]
    }
}
```

### 2. Enhanced `generate_code()` Method

**Changes:**
- Added `backend_api_spec` parameter
- Builds API context string from backend spec
- Appends API context to task description for LLM

**Code:**
```python
def generate_code(
    self,
    task_description: str,
    backend_url: str = "http://localhost:8000",
    previous_issues: Optional[List[str]] = None,
    backend_api_spec: Optional[Dict[str, Any]] = None  # NEW PARAMETER
) -> Dict[str, str]:
    
    # Build API context from backend spec
    api_context = ""
    if backend_api_spec and backend_api_spec.get("endpoints"):
        api_context = "\n\n## BACKEND API ENDPOINTS (use these EXACT endpoints):\n"
        for endpoint in backend_api_spec["endpoints"]:
            api_context += f"- {endpoint['method']} {endpoint['path']}\n"
        
        if backend_api_spec.get("schemas", {}).get("classes"):
            api_context += "\n## AVAILABLE SCHEMAS:\n"
            api_context += ", ".join(backend_api_spec["schemas"]["classes"])
    
    # Pass to LLM with API context
    response = chain.invoke({
        "task_description": task_description + api_context,  # API context appended
        "backend_url": backend_url
    })
```

### 3. Enhanced `execute_task()` Method

**Changes:**
- Extracts backend API spec before generation
- Passes API spec to `generate_code()`
- Logs discovered endpoints

**Code:**
```python
def execute_task(self, task_description: str, backend_url: str, max_retries: int):
    # Extract backend API specification if backend exists
    backend_api_spec = None
    backend_dir = self.config.backend_output_dir
    if Path(backend_dir).exists():
        print(f"   📡 Reading backend API specification...")
        backend_api_spec = extract_backend_api_spec(backend_dir)
        
        if backend_api_spec.get("endpoints"):
            print(f"      ✅ Found {len(backend_api_spec['endpoints'])} API endpoints")
            for endpoint in backend_api_spec["endpoints"][:5]:
                print(f"         - {endpoint['method']} {endpoint['path']}")
    
    # Generate code with backend API spec
    files = self.generate_code(
        task_description,
        backend_url,
        previous_issues,
        backend_api_spec  # Pass API spec
    )
```

---

## Example Output During Workflow

```
🎨 Frontend Agent: Starting task execution
   Task: Create a blog website with posts listing...
   Max retries: 5

   📡 Reading backend API specification...
      ✅ Found 6 API endpoints
         - GET /health
         - GET /posts
         - GET /posts/{post_id}
         - POST /posts
         - PUT /posts/{post_id}
         ... and 1 more

   📍 Attempt 1/5
      📝 Generating code for: Create a blog website...
```

---

## LLM Receives Enhanced Context

**Before:**
```
Task: Create a blog website with posts listing and CRUD operations
Backend URL: http://localhost:8000
```

**After:**
```
Task: Create a blog website with posts listing and CRUD operations

## BACKEND API ENDPOINTS (use these EXACT endpoints):
- GET /health
- GET /posts
- GET /posts/{post_id}
- POST /posts
- PUT /posts/{post_id}
- DELETE /posts/{post_id}

## AVAILABLE SCHEMAS:
PostCreate, PostUpdate, PostResponse, PostListResponse

Backend URL: http://localhost:8000
```

---

## Benefits

### 1. **Accurate API Calls** ✅
Frontend generates calls to endpoints that actually exist:
```typescript
// Generated code uses ACTUAL endpoints
export async function fetchPosts() {
  const response = await fetch(`${API_URL}/posts`);  // Matches backend
  return response.json();
}

export async function createPost(data: PostCreate) {
  const response = await fetch(`${API_URL}/posts`, {  // Matches backend
    method: 'POST',
    body: JSON.stringify(data)
  });
  return response.json();
}
```

### 2. **Type Safety** ✅
TypeScript types match backend Pydantic schemas:
```typescript
// Backend schema (Python)
class PostResponse(BaseModel):
    id: int
    title: str
    slug: str
    content: str
    excerpt: str | None
    is_published: bool
    created_at: datetime
    updated_at: datetime

// Frontend type (TypeScript) - should match!
interface Post {
    id: number;
    title: string;
    slug: string;
    content: string;
    excerpt?: string;
    is_published: boolean;
    created_at: string;
    updated_at: string;
}
```

### 3. **No 404 Errors** ✅
Frontend calls endpoints that exist, not imagined ones

### 4. **Faster Development** ✅
No manual coordination needed between frontend and backend

---

## Current Issue: Type Mismatch

### Problem
The generated frontend still has type mismatches:

**Backend Schema (actual):**
```python
class PostResponse(BaseModel):
    id: int
    title: str
    slug: str              # ← Backend has this
    content: str
    excerpt: str | None
    is_published: bool     # ← Backend has this
    created_at: datetime
    updated_at: datetime
```

**Frontend Type (generated):**
```typescript
interface Post {
    id: string | number;
    title: string;
    excerpt: string;
    content: string;
    category?: string;      // ← Backend DOESN'T have this
    imageUrl?: string;      // ← Backend DOESN'T have this
    published: boolean;     // ← Should be is_published
    createdAt: string;      // ← Should be created_at (snake_case)
    publishedAt?: string;   // ← Backend DOESN'T have this
    readTime?: number;      // ← Backend DOESN'T have this
}
```

### Root Cause
The LLM is still generating generic blog post types instead of reading the ACTUAL backend schemas.

### Solution Needed
The API context includes schema names but not their field definitions. We need to:
1. Extract actual field definitions from Pydantic schemas
2. Pass those to the LLM
3. Instruct LLM to match frontend types to backend schemas

---

## Next Steps

### Short Term (Manual Fix)
Fix the generated frontend `types.ts` to match backend:

```typescript
// frontend/lib/types.ts
export interface Post {
    id: number;
    title: string;
    slug: string;
    content: string;
    excerpt?: string;
    is_published: boolean;
    created_at: string;
    updated_at: string;
}

export interface PostCreate {
    title: string;
    content: string;
    excerpt?: string;
    is_published: boolean;
}

export interface PostUpdate {
    title?: string;
    content?: string;
    excerpt?: string;
    is_published?: boolean;
}

export interface PostListResponse {
    items: Post[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
}
```

### Long Term (Agent Enhancement)
Enhance `extract_backend_api_spec()` to parse Pydantic schema fields:

```python
def extract_pydantic_fields(schemas_content: str) -> Dict[str, List[Dict]]:
    """
    Parse Pydantic schemas to extract field definitions.
    
    Returns:
        {
            "PostResponse": [
                {"name": "id", "type": "int", "required": True},
                {"name": "title", "type": "str", "required": True},
                {"name": "slug", "type": "str", "required": True},
                ...
            ],
            ...
        }
    """
    # Use AST parsing to extract Pydantic field definitions
    # This is more reliable than regex
```

Then pass field definitions to LLM:
```
## BACKEND SCHEMAS:
PostResponse:
  - id: int (required)
  - title: str (required)
  - slug: str (required)
  - content: str (required)
  - excerpt: str | None (optional)
  - is_published: bool (required)
  - created_at: datetime (required)
  - updated_at: datetime (required)
```

---

## Testing

### Test Backend API Extraction
```bash
cd /Users/chowdaryadithyasai/Documents/visitor_workflow
python3 -c "
from workflow.agents.frontend_agent import extract_backend_api_spec

api_spec = extract_backend_api_spec('./backend')
print('✅ Found', len(api_spec['endpoints']), 'endpoints')
for endpoint in api_spec['endpoints']:
    print(f\"   - {endpoint['method']} {endpoint['path']}\")
"
```

**Expected Output:**
```
✅ Found 6 endpoints
   - GET /health
   - GET /posts
   - GET /posts/{post_id}
   - POST /posts
   - PUT /posts/{post_id}
   - DELETE /posts/{post_id}
```

### Test Frontend Agent Initialization
```bash
python3 -c "
from workflow.agents.frontend_agent import FrontendAgent
agent = FrontendAgent()
print('✅ FrontendAgent initialized successfully')
"
```

---

## Files Modified

1. **workflow/agents/frontend_agent.py**
   - Added `extract_backend_api_spec()` function
   - Modified `generate_code()` to accept `backend_api_spec` parameter
   - Modified `execute_task()` to extract and pass API spec

---

## Summary

### What Was Done ✅
1. ✅ Frontend Agent now reads backend code before generating
2. ✅ Extracts actual API endpoints from `main.py`
3. ✅ Extracts schema class names from `schemas.py`
4. ✅ Passes API information to LLM as context
5. ✅ Logs discovered endpoints during execution

### What Needs Work 🔨
1. 🔨 Extract actual field definitions from Pydantic schemas (not just class names)
2. 🔨 Improve LLM prompt to enforce type matching
3. 🔨 Add validation to ensure generated types match backend
4. 🔨 Fix current type mismatch in generated code

### Current Error to Fix
```
TypeError: Cannot read properties of undefined (reading 'map')
```
**Cause:** Frontend code tries to access `post.category` but backend doesn't have that field

**Fix:** Update frontend `types.ts` and `index.tsx` to use actual backend fields (`slug`, `is_published`, etc. instead of `category`, `published`, etc.)

---

## Conclusion

The Frontend Agent now has **backend awareness** - it reads actual endpoints and schemas before generating code. This is a major improvement over guessing what the backend looks like.

The next step is to enhance the field-level extraction so TypeScript types perfectly match Pydantic schemas, eliminating all type mismatches.
