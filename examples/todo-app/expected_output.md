# Todo Application - Expected Output

This document describes what the Supervised Agentic Workflow System should generate for the Todo Application.

## Workflow Execution Overview

### Phase 1: Planning (5-10 seconds)
The Planning Agent will decompose the requirements into approximately 8-10 tasks:

```
📋 Execution Plan:
  1. Initialize PostgreSQL database (database_agent)
  2. Generate User authentication model and endpoints (backend_agent)
  3. Generate Todo model and CRUD endpoints (backend_agent)
  4. Generate authentication UI components (frontend_agent)
  5. Generate dashboard and todo management UI (frontend_agent)
  6. Generate backend tests (testing_agent)
  7. Generate frontend tests (testing_agent)
  8. Deploy application to Docker (deployment_agent)
```

### Phase 2: Database Setup (15-30 seconds)
The Database Agent will:
- Create PostgreSQL container with secure credentials
- Initialize database schema with users and todos tables
- Validate database connectivity
- Generate migration scripts

**Generated Files:**
```
backend/migrations/
  ├── XXXXXX_init_schema.sql
  └── XXXXXX_init_schema.py
backend/.env
  └── DATABASE_URL=postgresql://user:password@localhost:5432/todoapp
```

### Phase 3: Backend Development (45-90 seconds)
The Backend Agent will generate a complete FastAPI application with self-evaluation.

**Expected Directory Structure:**
```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration and environment variables
├── requirements.txt       # Python dependencies
├── models/
│   ├── __init__.py
│   ├── user.py           # SQLAlchemy User model
│   └── todo.py           # SQLAlchemy Todo model
├── routes/
│   ├── __init__.py
│   ├── auth.py           # Authentication endpoints
│   └── todos.py          # Todo CRUD endpoints
├── services/
│   ├── __init__.py
│   ├── auth_service.py   # JWT and password handling
│   └── todo_service.py   # Business logic for todos
├── schemas/
│   ├── __init__.py
│   ├── user_schema.py    # Pydantic schemas for user
│   └── todo_schema.py    # Pydantic schemas for todo
└── tests/
    ├── __init__.py
    ├── test_auth.py
    └── test_todos.py
```

**Key Generated Code Snippets:**

`backend/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, todos
from config import settings

app = FastAPI(title="Todo API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(todos.router, prefix="/todos", tags=["Todos"])

@app.get("/")
def root():
    return {"message": "Todo API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

`backend/models/user.py`:
```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    todos = relationship("Todo", back_populates="user", cascade="all, delete-orphan")
```

`backend/routes/auth.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.user_schema import UserCreate, UserLogin, UserResponse, Token
from services.auth_service import AuthService
from database import get_db

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    auth_service = AuthService(db)
    user = auth_service.register_user(user_data)
    return user

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    auth_service = AuthService(db)
    token = auth_service.authenticate_user(credentials)
    return token

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    """Logout user (handled on client side)."""
    return None
```

`backend/services/auth_service.py`:
```python
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models.user import User
from schemas.user_schema import UserCreate, UserLogin

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: dict, expires_delta: timedelta = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
    
    def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        # Check if user exists
        existing_user = self.db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = self.hash_password(user_data.password)
        new_user = User(email=user_data.email, password_hash=hashed_password)
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user
    
    def authenticate_user(self, credentials: UserLogin) -> dict:
        """Authenticate user and return token."""
        user = self.db.query(User).filter(User.email == credentials.email).first()
        
        if not user or not self.verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        access_token = self.create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}
```

**Self-Evaluation Results:**
```
✅ Syntax validation: PASSED
✅ Type checking (mypy): PASSED
✅ Code quality (pylint): 8.5/10 - PASSED
✅ Functionality check: PASSED
✅ Error handling: PASSED
```

### Phase 4: Frontend Development (45-90 seconds)
The Frontend Agent will generate a Next.js application with TypeScript.

**Expected Directory Structure:**
```
frontend/
├── package.json
├── next.config.js
├── tsconfig.json
├── .env.local
├── app/
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Home/redirect page
│   ├── login/
│   │   └── page.tsx         # Login page
│   ├── register/
│   │   └── page.tsx         # Registration page
│   └── dashboard/
│       └── page.tsx         # Dashboard (protected)
├── components/
│   ├── Header.tsx           # Navigation header
│   ├── TodoList.tsx         # Todo list display
│   ├── TodoItem.tsx         # Individual todo item
│   ├── TodoForm.tsx         # Add/edit todo form
│   ├── AuthForm.tsx         # Reusable auth form
│   └── LoadingSpinner.tsx   # Loading indicator
├── lib/
│   ├── api.ts               # API client functions
│   ├── auth.ts              # Auth helper functions
│   └── types.ts             # TypeScript types
├── contexts/
│   └── AuthContext.tsx      # Authentication context
└── styles/
    └── globals.css          # Global styles
```

**Key Generated Code Snippets:**

`frontend/app/login/page.tsx`:
```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import Link from 'next/link';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-md">
        <div>
          <h2 className="text-3xl font-bold text-center">Sign In</h2>
          <p className="mt-2 text-center text-gray-600">
            Access your todo list
          </p>
        </div>
        
        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded" role="alert">
              {error}
            </div>
          )}
          
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email Address
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              aria-required="true"
            />
          </div>
          
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              aria-required="true"
            />
          </div>
          
          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        
        <p className="text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <Link href="/register" className="text-blue-600 hover:underline">
            Register here
          </Link>
        </p>
      </div>
    </div>
  );
}
```

`frontend/components/TodoList.tsx`:
```typescript
'use client';

import { useState, useEffect } from 'react';
import { getTodos, deleteTodo, toggleTodoComplete } from '@/lib/api';
import TodoItem from './TodoItem';
import { Todo } from '@/lib/types';

type FilterStatus = 'all' | 'pending' | 'completed';

export default function TodoList() {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [filter, setFilter] = useState<FilterStatus>('all');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadTodos();
  }, [filter]);

  const loadTodos = async () => {
    try {
      setIsLoading(true);
      const data = await getTodos(filter === 'all' ? undefined : filter);
      setTodos(data);
    } catch (error) {
      console.error('Failed to load todos:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this todo?')) return;
    
    try {
      await deleteTodo(id);
      setTodos(todos.filter(todo => todo.id !== id));
    } catch (error) {
      alert('Failed to delete todo');
    }
  };

  const handleToggle = async (id: number) => {
    try {
      const updatedTodo = await toggleTodoComplete(id);
      setTodos(todos.map(todo => todo.id === id ? updatedTodo : todo));
    } catch (error) {
      alert('Failed to update todo');
    }
  };

  const filteredTodos = todos;

  return (
    <div>
      <div className="mb-4 flex gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          All
        </button>
        <button
          onClick={() => setFilter('pending')}
          className={`px-4 py-2 rounded ${filter === 'pending' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Pending
        </button>
        <button
          onClick={() => setFilter('completed')}
          className={`px-4 py-2 rounded ${filter === 'completed' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Completed
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-8">Loading...</div>
      ) : filteredTodos.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No todos found. Create your first todo!
        </div>
      ) : (
        <div className="space-y-2">
          {filteredTodos.map(todo => (
            <TodoItem
              key={todo.id}
              todo={todo}
              onDelete={handleDelete}
              onToggle={handleToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

**Self-Evaluation Results:**
```
✅ ESLint validation: PASSED
✅ TypeScript checking: PASSED
✅ Accessibility (axe-core): PASSED (0 violations)
✅ Responsive design: PASSED
✅ Functionality check: PASSED
```

### Phase 5: Testing (30-60 seconds)
The Testing Agent will generate and execute test suites.

**Generated Test Files:**
```
backend/tests/
  ├── test_auth.py           # 8 tests for authentication
  ├── test_todos.py          # 12 tests for CRUD operations
  └── conftest.py            # Test fixtures and configuration

frontend/tests/
  ├── components/
  │   ├── TodoList.test.tsx
  │   └── TodoItem.test.tsx
  └── pages/
      ├── login.test.tsx
      └── dashboard.test.tsx
```

**Test Execution Results:**
```
Backend Tests:
  ✅ test_user_registration - PASSED
  ✅ test_duplicate_email_registration - PASSED
  ✅ test_user_login - PASSED
  ✅ test_invalid_credentials - PASSED
  ✅ test_create_todo - PASSED
  ✅ test_get_todos - PASSED
  ✅ test_update_todo - PASSED
  ✅ test_delete_todo - PASSED
  ✅ test_toggle_complete - PASSED
  ✅ test_unauthorized_access - PASSED
  
  Coverage: 87% - PASSED

Frontend Tests:
  ✅ Login form renders correctly - PASSED
  ✅ Registration form validation - PASSED
  ✅ TodoList displays todos - PASSED
  ✅ TodoItem toggle completion - PASSED
  
  Coverage: 74% - PASSED

Overall: 14/14 tests passed ✅
```

### Phase 6: Deployment (25-40 seconds)
The Deployment Agent will create Docker configurations and deploy.

**Generated Files:**
```
docker-compose.yml
backend/Dockerfile
frontend/Dockerfile
.dockerignore
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: todoapp
      POSTGRES_USER: todouser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U todouser"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://todouser:${DB_PASSWORD}@postgres:5432/todoapp
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - backend
    command: npm run dev

volumes:
  postgres_data:
```

**Deployment Results:**
```
🐳 Building images...
  ✅ postgres:15 - ready
  ✅ backend:latest - built successfully
  ✅ frontend:latest - built successfully

🚀 Starting containers...
  ✅ postgres - running (healthy)
  ✅ backend - running (healthy)
  ✅ frontend - running (healthy)

🌐 Service endpoints:
  Frontend: http://localhost:3000
  Backend: http://localhost:8000
  Backend API Docs: http://localhost:8000/docs
  Database: postgresql://localhost:5432/todoapp

✅ Deployment successful!
```

## Final Output Summary

### Generated Artifacts

**Code Files:** ~25 files
- Backend: 15 files (models, routes, services, schemas, config, tests)
- Frontend: 10 files (pages, components, lib, context, config)

**Lines of Code:** ~2,500 lines
- Backend Python: ~1,200 lines
- Frontend TypeScript: ~1,000 lines
- Configuration: ~300 lines

**Dependencies:**
- Backend: FastAPI, SQLAlchemy, psycopg2, python-jose, passlib, pytest
- Frontend: Next.js, React, TypeScript, axios, tailwindcss

### Quality Metrics

**Test Coverage:**
- Backend: 87% (target: >80%) ✅
- Frontend: 74% (target: >70%) ✅

**Code Quality:**
- Pylint score: 8.5/10 ✅
- ESLint: 0 errors ✅
- TypeScript: 0 errors ✅
- Accessibility: 0 violations ✅

**Performance:**
- Build time: ~3-5 minutes
- Container startup: ~20 seconds
- API response time: <100ms

### User Experience

**What the user can do immediately:**
1. Visit http://localhost:3000
2. Register a new account
3. Login with credentials
4. Create todo items
5. Mark todos as complete
6. Edit and delete todos
7. Filter by status
8. Logout

**Visual appearance:**
- Clean, modern interface
- Responsive design (works on mobile)
- Accessible (keyboard navigation, screen reader support)
- Loading states and error messages
- Smooth transitions

## Console Output During Execution

```
==============================================================================
🤖 Supervised Agentic Workflow System
==============================================================================

📝 Requirements: examples/todo-app/requirements.md

🔧 Initializing workflow graph...
✅ Workflow graph created

🆔 Thread ID: abc123-def456-789

🚀 Starting workflow execution...
------------------------------------------------------------------------------

🎯 Planning Agent: Analyzing requirements...
   📄 Reading markdown file: examples/todo-app/requirements.md
   ✅ Requirements loaded (1,523 words)
   🧠 Decomposing into executable tasks...
   ✅ Created execution plan with 8 tasks

👁️  Supervisor: Progress 0% | Next: database_node

🗄️  Database Agent: Initializing databases...
   🐳 Starting PostgreSQL container...
   ✅ Container running: postgres_todoapp
   🔧 Applying schema migrations...
   ✅ Migration successful
   🔌 Validating connection...
   ✅ Database ready

👁️  Supervisor: Progress 12% | Next: backend_node

⚙️  Backend Agent: Generating FastAPI application...
   📝 Generating models and routes...
   ✅ Code generated (1,203 lines)
   🔍 Self-evaluation: Round 1
      ✅ Syntax check: PASSED
      ✅ Type check: PASSED
      ✅ Code quality: 8.5/10 - PASSED
   ✅ Backend code complete

👁️  Supervisor: Progress 37% | Next: frontend_node

🎨 Frontend Agent: Generating Next.js application...
   📝 Generating pages and components...
   ✅ Code generated (998 lines)
   🔍 Self-evaluation: Round 1
      ✅ ESLint: PASSED
      ✅ TypeScript: PASSED
      ✅ Accessibility: PASSED
   ✅ Frontend code complete

👁️  Supervisor: Progress 62% | Next: testing_node

🧪 Testing Agent: Generating and executing tests...
   📝 Generating backend tests...
   ✅ 10 tests generated
   ▶️  Running pytest...
   ✅ 10/10 tests passed | Coverage: 87%
   
   📝 Generating frontend tests...
   ✅ 4 tests generated
   ▶️  Running jest...
   ✅ 4/4 tests passed | Coverage: 74%
   
   ✅ All tests passed

👁️  Supervisor: Progress 87% | Next: deployment_node

🚀 Deployment Agent: Deploying to Docker...
   🏗️  Building images...
   ✅ backend:latest built
   ✅ frontend:latest built
   
   🐳 Starting containers...
   ✅ postgres: running
   ✅ backend: running
   ✅ frontend: running
   
   🏥 Health checks...
   ✅ All services healthy
   
   ✅ Deployment complete!

✅ Workflow completed successfully!

📊 Summary:
   Duration: 3m 47s
   Tasks completed: 8/8
   Tests: 14/14 passed
   Coverage: Backend 87%, Frontend 74%
   
🌐 Your application is ready:
   Frontend: http://localhost:3000
   Backend API: http://localhost:8000
   API Docs: http://localhost:8000/docs

==============================================================================
```

## Verification Steps

To verify the generated application works correctly:

```bash
# 1. Check containers are running
docker ps

# Expected output:
# postgres_todoapp  - Up, healthy
# backend_todoapp   - Up, healthy
# frontend_todoapp  - Up, healthy

# 2. Test backend health
curl http://localhost:8000/health

# Expected: {"status":"healthy"}

# 3. Test user registration
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Expected: {"id":1,"email":"test@example.com","created_at":"..."}

# 4. Visit frontend
open http://localhost:3000

# Expected: Login page loads successfully
```

## Troubleshooting

If any issues occur during generation:

**Database connection fails:**
- Supervisor routes back to Database Agent
- Agent retries with exponential backoff
- After 3 attempts, requests human approval

**Backend tests fail:**
- Supervisor routes back to Backend Agent
- Agent regenerates code with fixes
- Self-evaluation runs again
- Maximum 5 regeneration attempts

**Frontend accessibility violations:**
- Frontend Agent detects violations in self-evaluation
- Agent regenerates components with fixes
- axe-core validation runs again

This demonstrates the self-healing capabilities of the agentic workflow system!
