# Supervised Agentic Workflow System

A LangGraph-based orchestration platform that coordinates specialist agents to build full-stack applications with Next.js frontend, FastAPI backend, and Docker-hosted databases.

## Features

- 🤖 **7 Specialist Agents**: Planning, Supervisor, Backend, Frontend, Database, Testing, Deployment
- 🔄 **Self-Evaluation Loops**: Agents validate their work and iterate until quality gates pass
- 💾 **Checkpointing**: Workflow state persists at each step, enabling resumption after interruptions
- 🔀 **Conditional Routing**: Supervisor routes based on success/failure/approval needs
- 🛡️ **Error Handling**: Exponential backoff, retry limits, human-in-the-loop approval
- 📄 **Markdown File Input**: Accept requirements as text or markdown files

## Architecture

```
User Input (text or .md file)
    ↓
Planning Agent → Execution Plan
    ↓
Supervisor Agent (conditional routing)
    ↓
├─→ Backend Agent (FastAPI code)
├─→ Frontend Agent (Next.js code)
├─→ Database Agent (PostgreSQL/MongoDB)
├─→ Testing Agent (pytest/Jest)
└─→ Deployment Agent (Docker)
    ↓
Complete Application
```

## Installation

### Prerequisites

- Python 3.11+
- Docker Desktop
- OpenAI API key

### Setup

1. **Clone and navigate to the project:**
```bash
cd visitor_workflow
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## Usage

### Basic Usage (Text Requirements)

```bash
python main.py "Build a todo application with user authentication and CRUD operations"
```

### Using Markdown File

```bash
python main.py ./agentic-application-requirements.md
```

### Example Output

```
==============================================================================
🤖 Supervised Agentic Workflow System
==============================================================================

📝 Requirements: Build a todo application with user authentication

🔧 Initializing workflow graph...
✅ Workflow graph created

🆔 Thread ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890

🚀 Starting workflow execution...
------------------------------------------------------------------------------

🎯 Planning Agent: Analyzing requirements...
✅ Created execution plan with 8 tasks
   - task_1: Initialize PostgreSQL database (agent: database)
   - task_2: Generate User model and authentication (agent: backend)
   - task_3: Generate Todo CRUD endpoints (agent: backend)
   ...

👁️  Supervisor: Determining next agent...
   Progress: 0.0%
   Next agent: database_node

🗄️  Database Agent: Initializing databases...

...

✅ Workflow completed successfully!

📊 Workflow Summary:
   Status: complete
   Tasks completed: 8
   Agent transitions: 12

🚀 Deployment Info:
   Frontend: http://localhost:3000
   Backend: http://localhost:8000
   Containers: frontend, backend, postgres, mongo
```

## Project Structure

```
visitor_workflow/
├── workflow/                      # Core workflow system
│   ├── __init__.py
│   ├── config.py                  # Configuration management
│   ├── models.py                  # Pydantic data models
│   ├── graph.py                   # LangGraph state machine
│   └── agents/                    # Specialist agents
│       ├── __init__.py
│       ├── planning_agent.py      # Requirements decomposition
│       ├── supervisor_agent.py    # Orchestration and routing
│       ├── backend_agent.py       # FastAPI code generation
│       ├── frontend_agent.py      # Next.js code generation
│       ├── database_agent.py      # Database initialization
│       ├── testing_agent.py       # Test generation and execution
│       └── deployment_agent.py    # Docker deployment
├── backend/                       # Generated backend code
├── frontend/                      # Generated frontend code
├── tests/                         # Test suite
├── main.py                        # CLI entry point
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment template
└── README.md                      # This file
```

## Configuration

Edit `.env` to configure the workflow:

```bash
# LLM Configuration
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4-turbo-preview
LLM_TEMPERATURE=0.0

# Workflow Configuration
MAX_RETRIES_PER_AGENT=5
MAX_TOTAL_RETRIES=20

# Database Images
POSTGRES_IMAGE=postgres:15
MONGO_IMAGE=mongo:7

# Application Ports
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

## Current Implementation Status

✅ **Completed:**
- Project structure and dependencies
- Core data models (WorkflowState, TaskDefinition, ExecutionPlan, etc.)
- Planning Agent with markdown file support
- Supervisor Agent with routing logic
- LangGraph state machine skeleton
- Checkpointing infrastructure
- CLI interface

🚧 **In Progress:**
- Backend Agent (code generation)
- Frontend Agent (code generation)
- Database Agent (Docker integration)
- Testing Agent (test generation)
- Deployment Agent (Docker Compose)
- Self-evaluation loops
- Error handling and retry logic

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Linting
pylint workflow/

# Type checking
mypy workflow/

# Formatting
black workflow/
```

## Roadmap

1. ✅ Core infrastructure (completed)
2. 🚧 Agent implementations (in progress)
3. ⏳ Self-evaluation loops
4. ⏳ Comprehensive testing
5. ⏳ Documentation and examples
6. ⏳ Web UI for workflow monitoring

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or pull request.
