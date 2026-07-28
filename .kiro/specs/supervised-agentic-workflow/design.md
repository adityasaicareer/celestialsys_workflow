# Design Document: Supervised Agentic Workflow System

## Overview

The Supervised Agentic Workflow System is a LangGraph-based orchestration platform that coordinates seven specialist agents to build complete full-stack applications. The system uses a state machine architecture where a supervisor agent routes execution between planning, backend development, frontend development, database management, testing, and deployment agents. Each specialist agent operates with self-evaluation capabilities, iteratively refining outputs until quality gates are met.

The architecture implements the **supervisor pattern**, a multi-agent coordination approach where a central orchestrator decomposes high-level tasks, routes sub-tasks to specialist agents by capability, and synthesizes results ([source](https://8080ai.hashnode.dev/supervisor-agent-architecture-multi-agent-ai-performance)). This pattern is well-suited for complex workflows with dependencies, as it centralizes coordination rather than relying on peer-to-peer negotiation ([source](https://www.augmentcode.com/guides/swarm-vs-supervisor)).

Key capabilities include:
- **State persistence and recovery** through LangGraph checkpointing
- **Self-evaluation loops** where agents validate their own outputs against requirements
- **Human-in-the-loop approval** for critical operations
- **Conditional routing** based on agent success or failure
- **Tool access** enabling agents to execute shell commands, manage packages, and interact with Docker

The system generates Next.js frontend applications, FastAPI backend services, and Docker-hosted databases (PostgreSQL and MongoDB), organizing code in proper directory structures with environment-specific configuration.

### Key Research Findings

**LangGraph State Machine**: LangGraph models workflows as directed graphs where nodes represent agents or tools and edges define conditional control flow ([source](https://www.madebyagents.com/frameworks/langgraph)). The state machine provides durable execution and streaming capabilities essential for agent orchestration ([source](https://docs.langchain.com/oss/python/langgraph/overview)).

**Checkpointing and Persistence**: LangGraph's checkpointing system saves snapshots of graph state at every node transition, tied to a thread_id for resumption ([source](https://markaicode.com/langgraph-persistence-checkpointing-workflows/)). For production deployments, SQLite checkpointing suffices for single-node setups, while PostgreSQL is recommended for distributed systems ([source](https://markaicode.com/best/best-langgraph-configuration-production-guide/)).

**Self-Evaluation Pattern**: The reflection pattern, identified by Andrew Ng as a core agentic design pattern, implements a closed feedback loop where agents evaluate outputs against quality criteria and revise until passing or reaching iteration limits ([source](https://www.taskade.com/blog/self-improving-ai-agents-reflection)). This prevents the natural failure mode of fabricated confirmations without actual validation ([source](https://github.com/AnastasiyaW/mclaude/blob/main/docs/code-review-agents.md)).

## Architecture

### System Components

```mermaid
graph TB
    User[User Input] --> Planning[Planning Agent]
    Planning --> Supervisor[Supervisor Agent]
    
    Supervisor --> Backend[Backend Agent]
    Supervisor --> Frontend[Frontend Agent]
    Supervisor --> Database[Database Agent]
    Supervisor --> Testing[Testing Agent]
    Supervisor --> Deployment[Deployment Agent]
    
    Backend --> BackendEval{Self-Evaluation}
    BackendEval -->|Pass| Supervisor
    BackendEval -->|Fail| Backend
    
    Frontend --> FrontendEval{Self-Evaluation}
    FrontendEval -->|Pass| Supervisor
    FrontendEval -->|Fail| Frontend
    
    Database --> DatabaseVal{Connection Test}
    DatabaseVal -->|Pass| Supervisor
    DatabaseVal -->|Fail| Database
    
    Testing --> TestResults{Tests Pass?}
    TestResults -->|All Pass| Supervisor
    TestResults -->|Failures| Supervisor
    
    Deployment --> DeploymentCheck{Services Running?}
    DeploymentCheck -->|Yes| Complete[Workflow Complete]
    DeploymentCheck -->|No| Deployment
    
    Supervisor --> HumanApproval{Needs Approval?}
    HumanApproval -->|Yes| WaitUser[Wait for User]
    WaitUser --> Supervisor
    
    Supervisor --> Checkpoint[(Checkpoint Storage)]
    Checkpoint --> Supervisor
```

### Implemented Bug Fixes

The system has been enhanced with four critical bug fixes that improve reliability and error recovery:

**Bug Fix 1: Testing Agent Import Mismatch**
- **Problem**: Testing Agent generated tests with incorrect import paths (e.g., `import todo` instead of `from models.todo import Todo`), causing pytest failures even when backend code was correct
- **Root Cause**: Backend Agent generates varying code structures (flat vs nested directories), but Testing Agent assumed hardcoded import patterns
- **Solution**: Added dynamic backend structure scanning via `_scan_backend_structure()` method that inspects actual file organization before test generation
- **Impact**: Tests now use correct imports matching the actual backend code structure, eliminating false test failures
- **Files Modified**: `workflow/agents/testing_agent.py` (added import context to system prompts)

**Bug Fix 2: Test Failure Routing**
- **Problem**: When tests failed, Testing Agent marked itself complete and workflow moved forward instead of routing back to Backend/Frontend Agent for fixes
- **Root Cause**: Testing node did not communicate test failure state to Supervisor's routing logic
- **Solution**: Modified `testing_node()` in `workflow/graph.py` to detect test failures and remove failed agent task IDs from `completed_task_ids` list, forcing Supervisor to re-route to the failing agent
- **Impact**: Failed tests now trigger automatic code regeneration by the responsible agent, enabling iterative fixes until tests pass
- **Files Modified**: `workflow/graph.py`, `workflow/models.py` (added `test_failures` field to WorkflowState)

**Bug Fix 3: Backend Agent Nested Folder Issue**
- **Problem**: Backend Agent created nested `backend/backend/` structure on retry, then evaluated old `backend/main.py` instead of new `backend/backend/main.py`, causing same errors to repeat across retries
- **Root Cause**: `write_code()` method never cleared old Python files before writing new ones, allowing stale files to persist
- **Solution**: Added cleanup logic to `write_code()` that deletes all `*.py` files before writing new ones (preserves `.env` for database configuration)
- **Impact**: Eliminates nested folder problems, ensures evaluation targets the correct code, enables progressive error fixing across retries
- **Files Modified**: `workflow/agents/backend_agent.py` (`write_code()` method)

**Bug Fix 4: Backend Agent Regeneration Prompt Enhancement**
- **Problem**: Same errors repeating across retries: "Pylint score 7.73 below threshold 8.0", "No overload variant of sessionmaker", "CRUD operations incomplete"
- **Root Cause**: Generic regeneration prompt lacked specific guidance for common failure patterns
- **Solution**: Enhanced `_get_regeneration_system_prompt()` with detailed fix instructions including:
  - SQLAlchemy 2.0 async patterns (`async_sessionmaker` instead of `sessionmaker(class_=AsyncSession)`)
  - Complete CRUD operation requirements (POST, GET, PUT, DELETE with examples)
  - Pylint score improvement techniques (docstrings, type hints, import cleanup)
  - Import/attribute error debugging (check actual definitions before importing)
  - FastAPI dependency injection patterns (use `Depends()` not `= None`)
  - Pydantic model conversion (return ORM models, let FastAPI convert)
- **Impact**: Agents self-correct common errors faster, reducing retry cycles and improving success rate
- **Files Modified**: `workflow/agents/backend_agent.py` (`_get_regeneration_system_prompt()` method)

These fixes collectively improve the system's ability to recover from errors, reduce infinite retry loops, and increase the success rate of code generation workflows.

### LangGraph State Machine Design

The system implements a **StateGraph** with the following structure:

**State Schema** (Pydantic model for validation):
```python
class WorkflowState(BaseModel):
    """Graph state persisted at each checkpoint."""
    messages: List[dict]  # Agent communication history
    current_task: str
    user_requirements: str  # Text or file path
    requirements_source: str  # "text" or "file"
    execution_plan: List[dict]  # Task dependency graph from Planning Agent
    completed_tasks: List[str]
    backend_code: Optional[str]
    frontend_code: Optional[str]
    database_config: Optional[dict]
    test_results: Optional[dict]
    deployment_status: Optional[dict]
    error_log: List[dict]
    retry_counts: dict  # Per-agent retry tracking
    requires_approval: bool
    workflow_metadata: dict  # Timestamps, agent transitions
```

**Node Definitions**:
- `planning_node`: Planning Agent execution
- `supervisor_node`: Routing logic and orchestration
- `backend_node`: Backend Agent with self-evaluation loop
- `frontend_node`: Frontend Agent with self-evaluation loop
- `database_node`: Database Agent with connection validation
- `testing_node`: Testing Agent with test execution
- `deployment_node`: Deployment Agent with service validation
- `human_approval_node`: Interrupt point for user confirmation

**Edge Types**:
- **Conditional edges** from supervisor to specialist agents (routing logic)
- **Deterministic edges** from specialists back to supervisor
- **Self-loop edges** for agents in evaluation/retry cycles
- **Interrupt edge** to human approval node when `requires_approval == True`

### Checkpointing Strategy

**Persistence Backend**: SQLite for single-process deployments (using `SqliteSaver`), with PostgreSQL option for distributed systems.

**Checkpoint Frequency**: State saved after every node transition, enabling crash recovery from the last successful step.

**Thread Management**: Each workflow execution uses a unique `thread_id` to isolate state. Resumption requires passing the same `thread_id` to the graph invocation.

**Cleanup Policy**: Checkpoint data deleted on successful workflow completion to prevent unbounded storage growth.

### Supervisor Routing Logic

The Supervisor Agent implements conditional routing based on:

1. **Task dependencies**: Routes to the next agent in the execution plan if previous task succeeded
2. **Error conditions**: Routes back to the failing agent (or related agent) with error context
3. **Quality gates**: Only routes forward when self-evaluation passes
4. **Retry limits**: Routes to human approval node when max retries exceeded (5 attempts)
5. **Approval requirements**: Routes to human approval node for critical operations (deployment, schema changes)

**Routing Decision Function**:
```python
def route_next_agent(state: WorkflowState) -> str:
    """Determine next node based on current state."""
    if state.requires_approval:
        return "human_approval_node"
    
    if state.retry_counts.get(state.current_task, 0) >= 5:
        return "human_approval_node"
    
    current_agent = get_current_agent(state.current_task)
    
    if has_errors(state.error_log, current_agent):
        return f"{current_agent}_node"  # Retry same agent
    
    next_task = get_next_task(state.execution_plan, state.completed_tasks)
    
    if next_task is None:
        return "deployment_node"  # All tasks complete
    
    return f"{next_task.agent}_node"
```

## Components and Interfaces

### Planning Agent

**Responsibilities**:
- Accept user requirements as natural language text or markdown file paths
- Read and parse markdown files when file paths are provided
- Decompose user requirements into executable tasks
- Create task dependency graph
- Identify required specialist agents for each task
- Validate requirement-to-task mapping completeness

**Input**: 
- User requirements (natural language string), OR
- Markdown file path (string ending in `.md`)

When a file path is provided, the agent reads the file content and uses it as the requirements context.

**Output**: Execution plan with structured tasks:
```python
{
    "tasks": [
        {
            "id": "task_1",
            "description": "Initialize PostgreSQL database",
            "agent": "database",
            "dependencies": [],
            "estimated_duration": "2 minutes"
        },
        {
            "id": "task_2",
            "description": "Generate User model and authentication endpoints",
            "agent": "backend",
            "dependencies": ["task_1"],
            "estimated_duration": "5 minutes"
        },
        # ... more tasks
    ],
    "dependency_graph": {...}
}
```

**Tools**: 
- File system access (read markdown files)
- None for planning logic (planning is LLM reasoning only)

### Supervisor Agent

**Responsibilities**:
- Execute routing logic for conditional edges
- Maintain workflow execution log
- Implement retry logic with exponential backoff
- Handle error aggregation and reporting
- Trigger human approval when needed
- Calculate progress and estimated completion time
- Route back to agents when tests fail for their code

**Input**: Current `WorkflowState`

**Output**: Next agent to execute (returned as string node name)

**Tools**:
- State inspection utilities
- Logging framework
- Time estimation functions

**Test Failure Routing** (Bug Fix 2 Integration):
- Supervisor analyzes `test_failures` field in WorkflowState
- If `test_failures.backend_failed == True`: Routes to backend_node
- If `test_failures.frontend_failed == True`: Routes to frontend_node  
- Agents receive test failure details and regenerate code to fix issues
- Testing node is re-executed after regeneration
- Process repeats until all tests pass or max retries exceeded

**Retry Logic**:
- Transient errors: Exponential backoff (1s, 2s, 4s, 8s, 16s)
- Max retries per agent: 5 attempts
- On max retries: Route to human approval

### Backend Agent

**Responsibilities**:
- Generate FastAPI Python code for API endpoints
- Implement database models and ORM integration
- Add error handling and input validation
- Apply type hints and docstrings
- Self-evaluate generated code against requirements
- Debug and regenerate on evaluation failure

**Input**: Backend task description from execution plan

**Output**: Python code files saved to `backend/` directory:
```
backend/
├── main.py              # FastAPI application entry point
├── models/              # SQLAlchemy or Pydantic models
├── routes/              # API endpoint handlers
├── services/            # Business logic
├── config.py            # Configuration management
└── requirements.txt     # Dependencies
```

**Tools**:
- Python interpreter (code execution)
- `pip` (package management)
- `pylint`, `mypy` (code analysis)
- File system access (write code files)
- Terminal access (run code)

**Self-Evaluation Loop**:
1. Generate code based on task requirements
2. Run static analysis (linting, type checking)
3. Execute code to check for runtime errors
4. Compare functionality against requirements
5. If issues found:
   - Log specific problems
   - Increment retry counter
   - Regenerate with corrections using enhanced regeneration prompt
6. If max retries exceeded: request human approval
7. If evaluation passes: save code and mark task complete

**Enhanced Regeneration Prompt** (Bug Fix 4):
- Problem: Same errors repeating across retries: "Pylint score below 8.0", "No overload variant of sessionmaker", "CRUD operations incomplete"
- Root Cause: Regeneration prompt lacked specific guidance for common failure patterns
- Solution: Enhanced `_get_regeneration_system_prompt()` with detailed fix instructions for recurring issues
- Added sections for:
  1. **SQLAlchemy 2.0 sessionmaker fix**: Use `async_sessionmaker` instead of `sessionmaker(class_=AsyncSession)`
  2. **Complete CRUD operations**: Explicitly requires POST, GET, PUT, DELETE endpoints with examples
  3. **Pylint score improvements**: Add docstrings, remove unused imports, add type hints
  4. **Import/Attribute errors**: Check actual schema definitions before importing
  5. **FastAPI dependency injection**: Use `Depends()` not `= None` for database sessions
  6. **Pydantic model conversion**: Return ORM models directly, let FastAPI convert with response_model
- Each section includes ❌ WRONG and ✅ CORRECT code examples for clarity

**Code File Cleanup** (Bug Fix 3):
- Problem: Backend agent created nested `backend/backend/` structure on retry, then evaluated old `backend/main.py` instead of new `backend/backend/main.py`, causing same errors to repeat
- Root Cause: `write_code()` never cleared old files before writing new ones
- Solution: Added cleanup logic to `write_code()` - deletes all `*.py` files before writing new ones (preserves `.env` for database config)
- Implementation:
  ```python
  # Clear old Python files to prevent nested folder issues
  for old_file in output_path.rglob("*.py"):
      try:
          old_file.unlink()
      except Exception:
          pass
  ```
- Result: No more nested folders, evaluation of correct code, progressive error fixing across retries
- Files preserved: `.env` (database configuration), other non-Python files

**Quality Gates**:
- No linting errors (pylint score > 8.0)
- No type checking errors (mypy passes)
- Code executes without exceptions
- All required functionality implemented
- Error handling present for external calls

### Frontend Agent

**Responsibilities**:
- Generate Next.js code using React and TypeScript/JavaScript
- Create responsive UI components
- Implement accessibility standards (WCAG AA)
- Apply aesthetic design principles
- Self-evaluate code for functionality and design
- Debug and regenerate on evaluation failure

**Input**: Frontend task description from execution plan

**Output**: Next.js code files saved to `frontend/` directory:
```
frontend/
├── pages/               # Next.js page routes
├── components/          # Reusable React components
├── styles/              # CSS/SCSS stylesheets
├── utils/               # Helper functions
├── public/              # Static assets
├── package.json         # Node dependencies
└── next.config.js       # Next.js configuration
```

**Tools**:
- Node.js runtime
- `npm` or `yarn` (package management)
- `eslint`, `prettier` (code formatting)
- File system access
- Terminal access

**Self-Evaluation Loop**:
1. Generate React components and pages
2. Run linting and formatting checks
3. Check for accessibility violations (axe-core or similar)
4. Validate responsive design (viewport testing)
5. Compare against design requirements
6. If issues found: regenerate with corrections
7. If max retries exceeded: request human approval
8. If evaluation passes: save code and mark complete

**Quality Gates**:
- No linting errors (eslint passes)
- Code formatted correctly (prettier)
- No accessibility violations (WCAG AA)
- Responsive design works on mobile/tablet/desktop
- All required UI elements implemented

### Database Agent

**Responsibilities**:
- Initialize PostgreSQL in Docker container
- Initialize MongoDB in Docker container
- Create database schemas and migrations
- Validate database connections
- Configure security settings and credentials

**Input**: Database requirements from execution plan

**Output**: 
- Running Docker containers for PostgreSQL and MongoDB
- Database initialization scripts
- Configuration files with connection strings

**Tools**:
- Docker CLI (container management)
- `psql` (PostgreSQL client)
- `mongosh` (MongoDB client)
- File system access
- Terminal access

**Connection Validation**:
```python
def validate_database_connection(db_type: str, config: dict) -> bool:
    """Test database connectivity before reporting completion."""
    if db_type == "postgresql":
        # Attempt connection with psycopg2
        # Run simple query: SELECT 1
    elif db_type == "mongodb":
        # Attempt connection with pymongo
        # Run simple query: db.admin.command('ping')
    return connection_successful
```

**Security Configuration**:
- Generate strong random passwords
- Store credentials in `.env` files (never hardcoded)
- Configure network isolation (Docker networks)
- Set appropriate user permissions

### Testing Agent

**Responsibilities**:
- Generate unit tests for backend (pytest)
- Generate integration tests for backend
- Generate component tests for frontend (Jest/Vitest)
- Generate integration tests for frontend
- Execute all tests and collect results
- Validate test coverage thresholds
- Dynamically scan backend structure to determine correct import paths

**Input**: Backend and frontend code from `WorkflowState`

**Output**: Test results with pass/fail status:
```python
{
    "backend_tests": {
        "total": 45,
        "passed": 43,
        "failed": 2,
        "coverage": 87.3,
        "failures": [
            {
                "test": "test_user_authentication",
                "error": "AssertionError: Expected 200, got 401",
                "traceback": "..."
            }
        ]
    },
    "frontend_tests": {
        "total": 32,
        "passed": 32,
        "failed": 0,
        "coverage": 92.1,
        "failures": []
    }
}
```

**Tools**:
- `pytest` (backend testing)
- `jest` or `vitest` (frontend testing)
- Coverage tools (`pytest-cov`, `istanbul`)
- Terminal access

**Test Generation Strategy**:
- **Unit tests**: Test individual functions and methods in isolation
- **Integration tests**: Test API endpoints end-to-end, component interactions
- **Edge cases**: Empty inputs, boundary values, error conditions
- **Coverage targets**: Minimum 80% line coverage for backend and frontend

**Dynamic Import Scanning** (Bug Fix 1):
- Before generating tests, Testing Agent scans backend directory structure
- `_scan_backend_structure()` method discovers:
  - File organization (flat vs nested directories)
  - Model locations (e.g., `models/todo.py` vs `todo.py`)
  - Module names and import paths
  - Database function locations (e.g., `database.py` vs `db/session.py`)
- Scan results included in "Import Context" section of LLM prompt
- Example scan output:
  ```
  # Import Context:
  from models.todo import Todo
  from models.user import User
  from database import get_db
  from main import app
  ```
- LLM instructed via **CRITICAL IMPORT REQUIREMENTS** to use exact paths from scan
- Tests generated with correct imports matching actual backend structure
- Eliminates import errors like `ModuleNotFoundError: No module named 'todo'`

**Import Path Resolution** (Bug Fix 1):
- Problem: Testing Agent generated tests with incorrect imports (e.g., `import todo` instead of `from models.todo import Todo`), causing pytest failures
- Root Cause: Backend Agent generates varying code structures (flat vs nested), but Testing Agent used hardcoded import assumptions
- Solution: Added `_scan_backend_structure()` method to dynamically scan backend directory structure
- Implementation: Before generating tests, Testing Agent scans backend directory to discover actual file structure and import paths
- System prompts enhanced with **CRITICAL IMPORT REQUIREMENTS** section instructing LLM to use exact import paths from scan results
- Example scan output: "from models.todo import Todo", "from database import get_db", "from main import app"
- Tests now use correct imports matching the actual backend code structure

**Test Failure Routing** (Bug Fix 2):
- Problem: When tests fail, Testing Agent completes and workflow moves forward instead of routing back to Backend/Frontend Agent
- Root Cause: Testing node did not communicate test failures to Supervisor's routing logic
- Solution: Modified `testing_node()` in `workflow/graph.py` to detect test failures and remove failed agent task IDs from completed list
- Implementation:
  - Testing node analyzes `backend_tests` and `frontend_tests` results
  - If backend tests fail: Removes backend task IDs from `completed_task_ids`
  - If frontend tests fail: Removes frontend task IDs from `completed_task_ids`
  - Sets `test_failures` in state with detailed failure information
  - Supervisor detects incomplete tasks and routes back to appropriate agent
- Flow After Fix: Tests fail → Testing node detects → Removes backend/frontend task IDs → Supervisor routes back to failing agent → Agent regenerates code → Tests run again

**Failure Handling**:
- Report failures to Supervisor with detailed error messages
- Supervisor routes back to Backend/Frontend agents for fixes based on test_failures field
- Remove failed agent task IDs from completed list to trigger regeneration
- Re-run tests after fixes until all pass

### Deployment Agent

**Responsibilities**:
- Create Docker configurations (Dockerfiles)
- Generate Docker Compose configuration
- Build Docker images for frontend and backend
- Deploy containers
- Validate service health and accessibility
- Output service endpoints

**Input**: Validated code and database configuration from `WorkflowState`

**Output**:
- Docker Compose file in project root
- Running containers for frontend, backend, and databases
- Service endpoint information

**Docker Compose Structure**:
```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend
  
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
      - MONGO_URL=mongodb://mongo:27017/db
    depends_on:
      - postgres
      - mongo
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=...
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db

volumes:
  postgres_data:
  mongo_data:
```

**Tools**:
- Docker CLI
- Docker Compose
- File system access
- Terminal access

**Service Validation**:
- Check container health status
- Verify frontend responds to HTTP requests (GET http://localhost:3000)
- Verify backend responds to health check endpoint (GET http://localhost:8000/health)
- Validate database connections from backend

**Failure Handling**:
- If build fails: report error to Supervisor
- If containers don't start: retry with increased timeouts
- If health checks fail: restart containers and retry
- If max retries exceeded: request human approval

## Data Models

### WorkflowState

```python
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TaskDefinition(BaseModel):
    """Individual task in the execution plan."""
    id: str
    description: str
    agent: str  # Which specialist agent handles this
    dependencies: List[str]  # Task IDs that must complete first
    estimated_duration: str
    status: str = "pending"  # pending, in_progress, complete, failed

class ErrorRecord(BaseModel):
    """Error information for debugging and recovery."""
    timestamp: datetime
    agent: str
    task_id: str
    error_type: str
    message: str
    traceback: Optional[str]
    retry_count: int

class TestResults(BaseModel):
    """Test execution results."""
    backend_tests: Dict[str, Any]
    frontend_tests: Dict[str, Any]
    overall_passed: bool

class DeploymentStatus(BaseModel):
    """Deployment state and service information."""
    containers_running: List[str]
    frontend_url: Optional[str]
    backend_url: Optional[str]
    health_checks_passed: bool
    deployment_timestamp: Optional[datetime]

class WorkflowState(BaseModel):
    """Complete state persisted at each checkpoint."""
    # Core workflow data
    thread_id: str = Field(..., description="Unique workflow execution ID")
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Planning and execution
    user_requirements: str  # Requirements text or file path
    requirements_source: str = "text"  # "text" or "file"
    execution_plan: List[TaskDefinition] = Field(default_factory=list)
    current_task_id: Optional[str] = None
    completed_task_ids: List[str] = Field(default_factory=list)
    
    # Agent outputs
    backend_code_path: Optional[str] = None
    frontend_code_path: Optional[str] = None
    database_config: Optional[Dict[str, Any]] = None
    test_results: Optional[TestResults] = None
    test_failures: Optional[Dict[str, Any]] = None  # Added for test failure routing (Bug Fix 2)
    deployment_status: Optional[DeploymentStatus] = None
    
    # Error handling and recovery
    error_log: List[ErrorRecord] = Field(default_factory=list)
    retry_counts: Dict[str, int] = Field(default_factory=dict)  # agent -> count
    
    # Workflow control
    requires_approval: bool = False
    approval_message: Optional[str] = None
    workflow_status: str = "running"  # running, paused, complete, failed
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    agent_transitions: List[Dict[str, Any]] = Field(default_factory=list)
```

### ExecutionPlan

```python
class ExecutionPlan(BaseModel):
    """Structured plan from Planning Agent."""
    tasks: List[TaskDefinition]
    dependency_graph: Dict[str, List[str]]  # task_id -> [dependent_task_ids]
    estimated_total_duration: str
    required_agents: List[str]
    
    def get_next_task(self, completed: List[str]) -> Optional[TaskDefinition]:
        """Get next executable task based on dependencies."""
        for task in self.tasks:
            if task.id in completed:
                continue
            if all(dep in completed for dep in task.dependencies):
                return task
        return None
    
    def validate_completeness(self, requirements: str) -> bool:
        """Check that all requirements map to at least one task."""
        # Implementation would analyze requirements coverage
        pass
```

### AgentMessage

```python
class AgentMessage(BaseModel):
    """Inter-agent communication message."""
    from_agent: str
    to_agent: str
    timestamp: datetime
    message_type: str  # task_assignment, result, error, approval_request
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
```

## Error Handling

### Error Classification

**Transient Errors** (retry with backoff):
- Network timeouts
- Docker daemon temporarily unavailable
- Database connection pool exhausted
- Rate limiting from external APIs

**Recoverable Errors** (route back to agent for fixes):
- Code generation errors (syntax errors, type errors)
- Test failures (Bug Fix 2: Testing node removes failed agent task IDs, Supervisor routes back)
- Linting violations (Bug Fix 4: Enhanced regeneration prompts guide fixes)
- Failed self-evaluation (Bug Fix 3: File cleanup prevents nested folder issues)
- Import mismatches (Bug Fix 1: Dynamic import scanning ensures correct paths)

**Critical Errors** (require human intervention):
- Docker not installed or not running
- Insufficient system resources (disk, memory)
- Invalid user requirements (ambiguous or contradictory)
- Max retry limit exceeded

### Retry Strategy

**Exponential Backoff**:
```python
def calculate_backoff(retry_count: int) -> float:
    """Calculate wait time before retry."""
    return min(2 ** retry_count, 16)  # Cap at 16 seconds
```

**Retry Limits**:
- Per-agent task limit: 5 attempts
- Per-workflow global limit: 20 total retries across all agents

**Retry Decision Logic**:
```python
def should_retry(error: ErrorRecord, state: WorkflowState) -> bool:
    """Determine if retry is appropriate."""
    agent_retries = state.retry_counts.get(error.agent, 0)
    total_retries = sum(state.retry_counts.values())
    
    if agent_retries >= 5:
        return False
    if total_retries >= 20:
        return False
    if error.error_type in ["CriticalError", "InvalidRequirements"]:
        return False
    
    return True
```

### Error Logging

All errors logged to `error_log` with:
- Timestamp
- Agent name
- Task ID
- Error type and message
- Full traceback (for debugging)
- Retry count at time of error

**Persistent Error Log**: Errors persisted in checkpoint state, available for post-mortem analysis.

### Rollback Mechanism

**Checkpoint-Based Rollback**:
- Supervisor can restore workflow to any previous checkpoint
- Rollback clears state changes after the rollback point
- Use case: When an agent corrupts state or produces invalid output

**File System Rollback**:
- Generated code saved with version suffixes (e.g., `main.py.v1`, `main.py.v2`)
- On rollback, restore previous version
- Use case: When code generation introduces breaking changes

### Human Intervention Protocol

**Approval Request**:
1. Set `state.requires_approval = True`
2. Set `state.approval_message` with context
3. Route to `human_approval_node`
4. Pause workflow execution
5. Present approval request to user via UI/CLI
6. Wait for user response (approve, reject, modify requirements)
7. Resume from next checkpoint based on user decision

**Intervention Triggers**:
- Max retry limit exceeded
- Critical operation (production deployment, schema migration)
- Ambiguous requirements detected
- Security-sensitive configuration changes

## Testing Strategy

The testing strategy employs a **dual approach** combining unit tests for specific scenarios and integration tests for end-to-end validation.

### Unit Testing

**Scope**: Test individual components in isolation

**Backend Unit Tests**:
- Test each API endpoint handler function
- Test database model validation logic
- Test service layer business logic
- Test error handling for invalid inputs
- Mock external dependencies (database, external APIs)

**Frontend Unit Tests**:
- Test React component rendering
- Test component state management
- Test event handlers (button clicks, form submissions)
- Test utility functions
- Mock API calls

**Supervisor Unit Tests**:
- Test routing logic with various state configurations
- Test retry decision logic
- Test error classification
- Test progress calculation

**Planning Agent Unit Tests**:
- Test task decomposition with sample requirements
- Test dependency graph construction
- Test validation of requirement completeness

**Testing Agent Unit Tests**:
- Test test generation logic
- Test coverage calculation
- Test result aggregation

**Test Framework**: `pytest` for backend (Python), `jest` or `vitest` for frontend (JavaScript/TypeScript)

**Example Unit Test**:
```python
def test_backend_agent_self_evaluation_passes_on_valid_code():
    """Verify Backend Agent evaluation accepts valid code."""
    agent = BackendAgent()
    valid_code = """
def get_user(user_id: int) -> User:
    '''Fetch user by ID.'''
    return db.query(User).filter(User.id == user_id).first()
"""
    result = agent.evaluate_code(valid_code, requirements="Fetch user by ID")
    assert result.passed == True
    assert result.issues == []

def test_supervisor_routes_to_human_approval_after_max_retries():
    """Verify Supervisor requests approval after retry limit."""
    state = WorkflowState(
        retry_counts={"backend": 5},
        current_task_id="task_1"
    )
    supervisor = SupervisorAgent()
    next_node = supervisor.route_next_agent(state)
    assert next_node == "human_approval_node"
```

### Integration Testing

**Scope**: Test complete workflows end-to-end

**Workflow Integration Tests**:
- Test full workflow from requirements to deployment
- Use sample applications (e.g., "build a todo app")
- Verify all agents execute in correct order
- Verify checkpoint persistence and recovery
- Verify deployment produces running services

**Agent Integration Tests**:
- Test Backend Agent with real code generation and execution
- Test Frontend Agent with real component generation
- Test Database Agent with actual Docker container creation
- Test Testing Agent with real test execution
- Test Deployment Agent with actual Docker deployment

**Test Environment**: Use Docker containers for isolated testing

**Example Integration Test**:
```python
def test_full_workflow_todo_app():
    """Integration test: Complete workflow for todo application."""
    requirements = """
    Build a todo application with:
    - User authentication
    - CRUD operations for todos
    - PostgreSQL database
    - Next.js frontend with React
    - FastAPI backend
    """
    
    workflow = WorkflowSystem()
    result = workflow.execute(requirements)
    
    # Verify execution completed
    assert result.status == "complete"
    assert len(result.error_log) == 0
    
    # Verify code generated
    assert os.path.exists("backend/main.py")
    assert os.path.exists("frontend/pages/index.js")
    
    # Verify tests passed
    assert result.test_results.overall_passed == True
    
    # Verify deployment successful
    assert result.deployment_status.health_checks_passed == True
    
    # Test deployed services
    frontend_response = requests.get("http://localhost:3000")
    assert frontend_response.status_code == 200
    
    backend_response = requests.get("http://localhost:8000/health")
    assert backend_response.status_code == 200
```

### Edge Case Testing

**Edge Cases to Cover**:
- Empty or minimal requirements
- Very complex requirements (large applications)
- Ambiguous requirements
- Contradictory requirements
- Docker not running
- Insufficient system resources
- Network failures during package installation
- Database initialization failures
- Code generation producing invalid syntax
- Tests that never pass (infinite loop prevention)

### Test Coverage Requirements

- **Minimum Line Coverage**: 80% for both backend and frontend
- **Agent Coverage**: 90% for all specialist agents
- **Critical Path Coverage**: 100% for supervisor routing logic and error handling

### Continuous Testing

**Test Execution**:
- Run unit tests on every code change
- Run integration tests before deployment
- Run edge case tests in CI/CD pipeline

**Test Maintenance**:
- Update tests when agent behavior changes
- Add tests for newly discovered edge cases
- Remove obsolete tests

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

This system is suitable for property-based testing because it implements deterministic logic for planning, routing, error handling, and validation. While the code generation agents themselves use LLMs (non-deterministic), the orchestration layer, validation logic, and state management exhibit universal properties that should hold across all valid inputs.

### Property 1: Execution Plan Validity

*For any* valid user requirements string, the Planning Agent SHALL produce an execution plan where:
- All tasks have valid agent assignments (one of the seven specialists)
- The dependency graph is a directed acyclic graph (no cycles)
- Every task is reachable from the start
- All identified requirements capabilities map to at least one task

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 2: Supervisor Routes on Task Success

*For any* WorkflowState with a completed task and no errors, the Supervisor SHALL route to the next agent according to the execution plan's dependency order, or to deployment_node if all tasks are complete.

**Validates: Requirements 3.2, 3.4**

### Property 3: Supervisor Routes on Task Failure

*For any* WorkflowState containing error records for an agent, the Supervisor SHALL route execution back to that agent (or a related agent) for fixes, unless max retries are exceeded.

**Validates: Requirements 3.3**

### Property 4: Supervisor Routes to Approval on Critical Operations

*For any* WorkflowState where `requires_approval` is `True`, the Supervisor SHALL route to `human_approval_node` regardless of task completion status.

**Validates: Requirements 3.6**

### Property 5: Supervisor Maintains Execution Log

*For any* sequence of agent transitions in the workflow, the `agent_transitions` list SHALL contain entries for each transition with timestamps and agent names in chronological order.

**Validates: Requirements 3.5**

### Property 6: Test Failure Routes to Code Agent

*For any* WorkflowState with test failures in `test_results`, the Supervisor SHALL route back to the Backend_Agent or Frontend_Agent depending on which codebase had failing tests.

**Validates: Requirements 7.5**

### Property 7: Coverage Below Threshold Blocks Deployment

*For any* TestResults where either `backend_tests.coverage` or `frontend_tests.coverage` is below 80%, the workflow SHALL NOT route to the Deployment_Agent until coverage is improved.

**Validates: Requirements 7.6**

### Property 8: Max Retries Trigger Approval Request

*For any* agent and task, when the retry counter for that agent reaches 5 attempts without passing the quality gate, the state SHALL set `requires_approval` to `True` and route to the human approval node.

**Validates: Requirements 9.4, 9.5, 11.3**

### Property 9: Exponential Backoff Calculation

*For any* retry count `n` in the range [0, 10], the backoff duration SHALL equal `min(2^n, 16)` seconds, implementing exponential backoff with a 16-second cap.

**Validates: Requirements 11.2**

### Property 10: Error Logging Completeness

*For any* error encountered by any agent, an ErrorRecord SHALL be added to `state.error_log` containing:
- `timestamp` (datetime)
- `agent` (agent name string)
- `task_id` (current task identifier)
- `error_type` (error classification)
- `message` (error description)
- `traceback` (optional stack trace)
- `retry_count` (attempts so far)

**Validates: Requirements 11.1, 11.4**

### Property 11: No Hardcoded Credentials in Generated Code

*For any* generated code file (backend or frontend), the file contents SHALL NOT contain hardcoded credential patterns matching:
- `password=<literal>`
- `api_key=<literal>`
- `secret=<literal>`
- `token=<literal>`

where `<literal>` is a non-variable string value.

**Validates: Requirements 14.5**

### Property 12: Agent Transitions Logged with Timestamps

*For any* agent execution in the workflow, the `agent_transitions` list SHALL contain a record with:
- `agent_name` (which agent executed)
- `timestamp` (when execution started)
- `task_id` (which task was executed)

ensuring all transitions are logged in chronological order.

**Validates: Requirements 15.1**

### Property 13: Progress Calculation Accuracy

*For any* WorkflowState, the progress percentage SHALL equal `(len(completed_task_ids) / len(execution_plan.tasks)) * 100`, accurately reflecting the proportion of completed tasks.

**Validates: Requirements 15.2**

### Property 14: Estimated Completion Time Calculation

*For any* workflow with progress percentage `p` (0 < p < 100) and elapsed time `t`, the estimated remaining time SHALL equal `(t / p) * (100 - p)`, extrapolating completion based on current pace.

**Validates: Requirements 15.4**

### Property 15: Workflow Metrics Completeness

*For any* completed workflow, the metrics dictionary SHALL contain:
- `workflow_duration` (total execution time)
- `agent_execution_times` (dict mapping agent names to execution durations)
- `retry_counts` (dict mapping agents to retry counts)
- `total_tasks` (number of tasks in execution plan)
- `failed_tasks` (number of tasks that failed)

**Validates: Requirements 15.6**
