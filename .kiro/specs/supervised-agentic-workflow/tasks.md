# Implementation Plan: Supervised Agentic Workflow System

## Overview

This implementation plan breaks down the supervised agentic workflow system into executable tasks. The system uses LangGraph to orchestrate seven specialist agents (Planning, Supervisor, Backend, Frontend, Database, Testing, Deployment) that collaborate to build full-stack applications with Next.js frontend, FastAPI backend, and Docker-hosted databases. 

**Implementation Language:** Python (using LangGraph, LangChain, Pydantic, FastAPI)

The implementation follows a bottom-up approach: first building core data models and state management, then implementing individual agents with self-evaluation capabilities, followed by LangGraph state machine integration, checkpointing, error handling, and finally testing infrastructure.

### Current Status

✅ **Completed (Tasks 1-14):**
- Core project structure and dependencies
- Data models and state management (Pydantic models)
- Checkpointing infrastructure (SQLite-based)
- All seven specialist agents implemented:
  - Planning Agent (with file input support)
  - Supervisor Agent (routing and coordination)
  - Backend Agent (FastAPI code generation with self-evaluation)
  - Frontend Agent (Next.js code generation with self-evaluation)
  - Database Agent (Docker-hosted PostgreSQL and MongoDB)
  - Testing Agent (test generation and execution)
  - Deployment Agent (Docker orchestration)
- LangGraph state machine with conditional routing
- Error handling and retry logic with exponential backoff

🚧 **In Progress (Tasks 15-22):**
- Human approval mechanism (partially complete)
- Workflow system orchestration enhancements
- Monitoring and observability
- Configuration management
- Comprehensive integration testing
- Documentation and examples

## Tasks

- [x] 1. Set up project structure and core dependencies
  - Create project directory structure with `backend/`, `frontend/`, `workflow/`, `tests/` folders
  - Create `requirements.txt` with core dependencies: `langgraph`, `langchain`, `langchain-openai`, `pydantic`, `sqlalchemy`, `fastapi`, `pytest`, `docker`
  - Create `.env.example` file for configuration templates
  - Initialize Python virtual environment and install dependencies
  - _Requirements: 1.1, 1.2, 1.5, 13.1, 13.2_

- [x] 2. Implement core data models and state management
  - [x] 2.1 Create Pydantic models for workflow state
    - Implement `TaskDefinition` model with id, description, agent, dependencies, estimated_duration, status fields
    - Implement `ErrorRecord` model with timestamp, agent, task_id, error_type, message, traceback, retry_count fields
    - Implement `TestResults` model with backend_tests, frontend_tests, overall_passed fields
    - Implement `DeploymentStatus` model with containers_running, frontend_url, backend_url, health_checks_passed, deployment_timestamp fields
    - Implement `WorkflowState` model with all fields specified in design document
    - Implement `ExecutionPlan` model with `get_next_task` and `validate_completeness` methods
    - Implement `AgentMessage` model for inter-agent communication
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 10.2_

  - [ ]* 2.2 Write property test for state models
    - **Property 10: Error Logging Completeness**
    - **Validates: Requirements 11.1, 11.4**

  - [ ]* 2.3 Write unit tests for ExecutionPlan methods
    - Test `get_next_task` method with various dependency graphs
    - Test `validate_completeness` method with sample requirements
    - _Requirements: 2.3, 2.4_

- [x] 3. Implement checkpointing infrastructure
  - [x] 3.1 Create checkpointing system using SQLite
    - Implement `CheckpointManager` class with `SqliteSaver` integration from LangGraph
    - Implement checkpoint database initialization and schema setup
    - Implement state serialization and deserialization logic
    - Add thread_id management for workflow isolation with `generate_thread_id` method
    - Add checkpoint listing, cleanup, and statistics methods
    - _Requirements: 1.3, 10.1, 10.2, 10.4_

  - [ ]* 3.2 Write unit tests for checkpointing
    - Test state save and restore operations
    - Test thread_id isolation
    - Test checkpoint cleanup on workflow completion
    - _Requirements: 10.1, 10.2, 10.4, 10.5_

- [x] 4. Implement Planning Agent with file input support
  - [x] 4.1 Create Planning Agent with file path detection and markdown reading
    - Implement `PlanningAgent` class with LangChain OpenAI integration
    - Implement `detect_input_type` to identify text vs file paths (checks for .md extension)
    - Implement `read_markdown_file` with error handling for missing/unreadable files
    - Implement `create_execution_plan` with LLM-based task decomposition
    - Implement `validate_plan` with DAG cycle detection, unique task IDs, and valid agent names
    - Add comprehensive system prompt for task breakdown and agent assignment
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 4.2 Write property test for planning agent
    - **Property 1: Execution Plan Validity**
    - Test that all generated plans have valid agent assignments
    - Test that dependency graphs are acyclic
    - Test that all tasks are reachable
    - **Validates: Requirements 2.3, 2.4, 2.5, 2.6**

  - [ ]* 4.3 Write unit tests for Planning Agent
    - Test with simple text requirements (e.g., "build a todo app")
    - Test with markdown file path input (create temporary markdown file)
    - Test file reading and parsing logic
    - Test error handling for non-existent files
    - Test with complex requirements from file
    - Test DAG validation with cyclic dependencies
    - _Requirements: 2.1, 2.2_

- [ ] 5. Checkpoint - Ensure core models and planning work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Supervisor Agent routing and coordination
  - [x] 6.1 Create Supervisor Agent with comprehensive routing logic
    - Implement `SupervisorAgent` class with routing decision logic
    - Implement `route_next_agent` function with approval checking, retry limit enforcement, error routing, and task dependency handling
    - Implement `calculate_progress` for percentage completion tracking
    - Implement `estimate_remaining_time` based on progress and elapsed time
    - Implement `log_transition` to track agent transitions with timestamps
    - Implement `log_error` to record errors with retry counter increments
    - Implement `should_request_approval` for critical operations
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 15.2, 15.4_

  - [ ]* 6.2 Write property tests for supervisor routing
    - **Property 2: Supervisor Routes on Task Success**
    - **Property 3: Supervisor Routes on Task Failure**
    - **Property 4: Supervisor Routes to Approval on Critical Operations**
    - **Property 5: Supervisor Maintains Execution Log**
    - **Property 6: Test Failure Routes to Code Agent**
    - **Property 12: Agent Transitions Logged with Timestamps**
    - **Property 13: Progress Calculation Accuracy**
    - **Property 14: Estimated Completion Time Calculation**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 7.5, 15.1, 15.2, 15.4**

  - [ ]* 6.3 Write unit tests for supervisor edge cases
    - Test routing when all tasks complete
    - Test routing when max retries exceeded
    - Test routing with empty execution plan
    - Test test failure routing to appropriate agent
    - Test progress calculation edge cases
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 7. Implement LangGraph state machine and workflow graph
  - [x] 7.1 Create LangGraph StateGraph with all nodes and edges
    - Define `StateGraph` with `WorkflowState` as state schema
    - Add all node functions: `planning_node`, `supervisor_node`, `backend_node`, `frontend_node`, `database_node`, `testing_node`, `deployment_node`, `human_approval_node`
    - Implement node execution functions wrapping agent logic with state updates
    - Define conditional edges from supervisor to specialist agents using `route_from_supervisor`
    - Define deterministic edges from specialists back to supervisor
    - Define deployment edge to END
    - Set entry point to `planning_node`
    - Integrate CheckpointManager and compile graph with checkpointing enabled
    - _Requirements: 1.1, 1.2, 3.1_

  - [ ]* 7.2 Write integration tests for state machine
    - Test graph construction
    - Test node execution with mock agents
    - Test conditional edge routing
    - Test interrupt mechanism
    - _Requirements: 1.1, 3.1_

- [x] 8. Implement comprehensive error handling and retry logic
  - [x] 8.1 Create error handling infrastructure module
    - Create `workflow/error_handling.py` module
    - Implement error classification logic (transient, recoverable, critical)
    - Implement exponential backoff calculation function: `min(2^n, 16)` seconds
    - Implement retry decision logic with per-agent (5 max) and global (20 max) limits
    - Create `ErrorHandler` class to centralize error management
    - Add rollback mechanism for checkpoint-based recovery
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ]* 8.2 Write property tests for error handling
    - **Property 8: Max Retries Trigger Approval Request**
    - Test that 5 agent retries triggers approval
    - **Property 9: Exponential Backoff Calculation**
    - Test backoff calculation for n=0 to 10
    - **Validates: Requirements 9.4, 9.5, 11.2, 11.3**

  - [ ]* 8.3 Write unit tests for error classification and retry
    - Test transient error identification (network timeouts, rate limits)
    - Test recoverable error identification (syntax errors, test failures)
    - Test critical error identification (Docker not running, invalid requirements)
    - Test retry decision logic with various error types and retry counts
    - Test exponential backoff calculation edge cases
    - _Requirements: 11.1, 11.2, 11.3_

- [x] 9. Complete Backend Agent with self-evaluation
  - [x] 9.1 Implement Backend Agent code generation with LLM
    - Create `BackendAgent` class with LangChain OpenAI integration
    - Implement FastAPI code generation with proper file structure: main.py, models/, routes/, services/, config.py
    - Add comprehensive error handling and input validation to generated code
    - Ensure Python type hints and docstrings in all generated code
    - Add requirements.txt generation with correct dependencies
    - Implement database integration code (SQLAlchemy models, connection management)
    - _Requirements: 4.1, 4.4, 4.5, 4.6, 12.2, 13.1, 13.3, 14.1_

  - [x] 9.2 Implement Backend Agent self-evaluation loop
    - Implement `evaluate_code` method using pylint (target score > 8.0)
    - Implement type checking with mypy (must pass with no errors)
    - Add syntax validation (compile Python AST)
    - Implement functionality comparison against requirements
    - Add quality gate validation before marking complete
    - Implement regeneration loop with retry counter (max 5 attempts)
    - Add approval request when max retries exceeded
    - _Requirements: 4.2, 4.3, 9.1, 9.3, 9.4, 9.5_

  - [ ]* 9.3 Write unit tests for Backend Agent
    - Test code generation with sample requirements (simple CRUD API)
    - Test self-evaluation with valid, well-typed code
    - Test self-evaluation with syntax errors
    - Test self-evaluation with type errors
    - Test retry loop behavior and counter increment
    - Test max retry approval request
    - _Requirements: 4.1, 4.2, 4.3, 9.1, 9.3_

- [x] 10. Complete Frontend Agent with self-evaluation
  - [x] 10.1 Implement Frontend Agent code generation with LLM
    - Create `FrontendAgent` class with LangChain OpenAI integration
    - Implement Next.js code generation with proper structure: pages/, components/, styles/, lib/, public/
    - Implement responsive design generation (mobile-first, Tailwind CSS or similar)
    - Implement accessibility features (WCAG AA: ARIA labels, semantic HTML)
    - Ensure TypeScript usage with proper types
    - Add comprehensive error boundaries and loading states
    - Generate package.json and next.config.js with proper configuration
    - _Requirements: 5.1, 5.4, 5.5, 5.6, 12.3, 13.1, 13.4, 14.2_

  - [x] 10.2 Implement Frontend Agent self-evaluation loop
    - Implement `evaluate_code` method using eslint (must pass with no errors)
    - Implement code formatting check with prettier
    - Add accessibility validation (integrate axe-core or similar tool)
    - Implement responsive design validation logic
    - Implement functionality comparison against requirements
    - Add quality gate validation (no linting errors, no accessibility violations)
    - Implement regeneration loop with retry counter (max 5 attempts)
    - Add approval request when max retries exceeded
    - _Requirements: 5.2, 5.3, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 10.3 Write unit tests for Frontend Agent
    - Test component generation with sample requirements (simple form, data display)
    - Test self-evaluation with valid, accessible code
    - Test self-evaluation with linting errors
    - Test self-evaluation with accessibility violations
    - Test retry loop behavior and counter increment
    - Test max retry approval request
    - _Requirements: 5.1, 5.2, 5.3, 9.2, 9.3_

- [x] 11. Checkpoint - Ensure agents and error handling work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement Database Agent with Docker integration
  - [x] 12.1 Create Database Agent class with Docker SDK
    - Create `workflow/agents/database_agent.py` module
    - Implement `DatabaseAgent` class with Docker SDK integration (docker-py)
    - Implement PostgreSQL container initialization logic (docker run postgres:15)
    - Implement MongoDB container initialization logic (docker run mongo:7)
    - Implement database schema creation and migration script generation
    - Add strong random password generation using secrets module
    - Add .env file generation for database configuration
    - Ensure proper Docker networking between database and application containers
    - _Requirements: 6.1, 6.2, 6.3, 6.5, 12.4, 14.3_

  - [x] 12.2 Implement database connection validation
    - Implement PostgreSQL connection test using psycopg2 (SELECT 1 query)
    - Implement MongoDB connection test using pymongo (admin ping)
    - Add connection validation loop before reporting completion
    - Add detailed error reporting with diagnostics on connection failure
    - Implement retry logic for transient connection failures
    - _Requirements: 6.4, 6.6_

  - [ ]* 12.3 Write property test for database security
    - **Property 11: No Hardcoded Credentials in Generated Code**
    - Test that no database configuration files contain literal passwords
    - Test that all credentials are stored in .env files
    - **Validates: Requirements 14.5**

  - [ ]* 12.4 Write unit tests for Database Agent
    - Test PostgreSQL container initialization (mock Docker calls)
    - Test MongoDB container initialization (mock Docker calls)
    - Test connection validation logic with mock connections
    - Test credential generation (check randomness and length)
    - Test .env file generation format
    - _Requirements: 6.1, 6.2, 6.4, 6.5_

- [x] 13. Implement Testing Agent with test generation and execution
  - [x] 13.1 Create Testing Agent class with test generation
    - Create `workflow/agents/testing_agent.py` module
    - Implement `TestingAgent` class with test generation capabilities using LLM
    - Implement backend unit test generation using pytest
    - Implement backend integration test generation (API endpoint testing)
    - Implement frontend component test generation using Jest or Vitest
    - Implement frontend integration test generation
    - Generate proper test file structure (tests/ directory, conftest.py)
    - _Requirements: 7.1, 7.2, 12.6, 13.6_

  - [x] 13.2 Implement test execution and result collection
    - Implement pytest execution via subprocess with result parsing
    - Implement Jest/Vitest execution via subprocess with result parsing
    - Implement coverage calculation (pytest-cov for backend, istanbul for frontend)
    - Implement result aggregation into TestResults model
    - Add detailed failure reporting with error messages and tracebacks
    - Parse test output to extract pass/fail counts and coverage percentages
    - _Requirements: 7.3, 7.4, 7.5_

  - [ ]* 13.3 Write property test for test coverage
    - **Property 7: Coverage Below Threshold Blocks Deployment**
    - Test that <80% coverage prevents routing to deployment
    - Test with various coverage percentages (0%, 50%, 79%, 80%, 100%)
    - **Validates: Requirements 7.6**

  - [ ]* 13.4 Write unit tests for Testing Agent
    - Test test generation with sample backend code
    - Test test generation with sample frontend code
    - Test pytest execution and output parsing
    - Test Jest execution and output parsing
    - Test coverage calculation and threshold validation
    - Test failure reporting format
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 14. Implement Deployment Agent with Docker orchestration
  - [x] 14.1 Create Deployment Agent class with Docker SDK
    - Create `workflow/agents/deployment_agent.py` module
    - Implement `DeploymentAgent` class with Docker SDK integration
    - Implement Dockerfile generation for frontend (Node.js 18+ base image)
    - Implement Dockerfile generation for backend (Python 3.11+ base image)
    - Implement Docker Compose configuration generation (version 3.8)
    - Add environment-specific configuration handling (dev, staging, prod)
    - Generate proper networking configuration (Docker networks)
    - _Requirements: 8.1, 8.2, 12.5, 13.5, 14.4_

  - [x] 14.2 Implement container build and deployment
    - Implement Docker image build logic using Docker SDK
    - Implement Docker Compose deployment (docker-compose up -d)
    - Implement service health validation (HTTP health checks for frontend/backend)
    - Implement database connection validation from backend container
    - Add service endpoint output (URLs for frontend and backend)
    - Add detailed error reporting with diagnostics on deployment failure
    - Implement container cleanup on failure
    - _Requirements: 8.3, 8.4, 8.5, 8.6, 8.7_

  - [ ]* 14.3 Write unit tests for Deployment Agent
    - Test Dockerfile generation for frontend
    - Test Dockerfile generation for backend
    - Test Docker Compose generation with all services
    - Test service health validation logic
    - Test endpoint output formatting
    - Test error handling for failed deployments
    - _Requirements: 8.1, 8.2, 8.5, 8.7_

- [x] 15. Implement human approval mechanism
  - [x] 15.1 Create human approval node with user interaction
    - Implement `human_approval_node` function for LangGraph in `workflow/graph.py`
    - Implement workflow pause/interrupt logic using LangGraph interrupts
    - Implement approval request presentation (CLI or UI interface)
    - Implement user response handling (approve, reject, modify requirements)
    - Implement workflow resumption after approval
    - Add timeout handling for approval requests
    - _Requirements: 3.6, 9.5, 11.3_

  - [ ]* 15.2 Write unit tests for approval mechanism
    - Test approval node pauses workflow
    - Test approval response handling
    - Test workflow resumption after approval
    - Test timeout handling
    - _Requirements: 3.6_

- [x] 16. Checkpoint - Ensure all agents are complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Enhance workflow system orchestration and entry point
  - [ ] 17.1 Add Docker validation and directory management to main.py
    - Add Docker daemon validation before workflow execution
    - Implement output directory creation (frontend/, backend/) if they don't exist
    - Add pre-flight checks for required tools (Docker, Node.js, Python packages)
    - Add checkpoint cleanup on successful completion
    - Improve error messages and user feedback
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 10.3, 10.4, 10.5_

  - [ ] 17.2 Implement workflow resumption logic
    - Add command-line option to list incomplete workflows (--list-workflows)
    - Add command-line option to resume existing workflow (--resume THREAD_ID)
    - Implement checkpoint restoration with thread_id
    - Display workflow state information on resume
    - Add user confirmation before resuming
    - _Requirements: 10.3, 10.4_

  - [ ]* 17.3 Write integration tests for workflow system
    - Test Docker validation logic
    - Test workflow execution end-to-end with sample requirements
    - Test workflow resumption after interruption
    - Test checkpoint cleanup after completion
    - _Requirements: 1.1, 1.4, 10.3, 10.4, 10.5_

- [x] 18. Implement monitoring and observability
  - [x] 18.1 Create logging and metrics infrastructure
    - Create `workflow/monitoring.py` module
    - Implement structured logging for all agent transitions using Python logging
    - Implement agent activity logging with timestamps
    - Implement workflow metrics collection (workflow_duration, agent_execution_times, retry_counts, total_tasks, failed_tasks)
    - Implement workflow state visualization (current position in state graph, ASCII diagram or JSON representation)
    - Add progress tracking updates to console during execution
    - Add metrics export functionality (JSON, CSV, or monitoring service integration)
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6_

  - [ ]* 18.2 Write property test for metrics completeness
    - **Property 15: Workflow Metrics Completeness**
    - Test that all required metrics are collected for any workflow execution
    - Test that agent transition logs contain all required fields
    - **Validates: Requirements 15.6**

  - [ ]* 18.3 Write unit tests for monitoring
    - Test agent transition logging
    - Test metrics collection
    - Test state visualization output
    - Test metrics export formats
    - _Requirements: 15.1, 15.3, 15.5, 15.6_

- [x] 19. Implement configuration management and validation
  - [ ] 19.1 Create configuration validation system
    - Update `workflow/config.py` with comprehensive validation logic
    - Implement environment variable validation (required variables present)
    - Implement configuration file templates for different environments (.env.dev, .env.prod)
    - Add secrets validation (ensure no hardcoded credentials in generated code)
    - Implement configuration documentation generation
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ]* 19.2 Write unit tests for configuration
    - Test environment variable loading
    - Test configuration validation with missing variables
    - Test secrets detection in generated code
    - Test configuration template generation
    - _Requirements: 14.5_

- [ ] 20. Write comprehensive integration tests
  - [ ]* 20.1 Write end-to-end workflow integration tests
    - Test full workflow with simple application (todo app with CRUD operations)
    - Test full workflow with complex application (e-commerce app with authentication)
    - Test workflow with test failures and corrections
    - Test workflow with deployment failures and retries
    - Test workflow with max retries and human approval
    - Test workflow interruption and resumption
    - _Requirements: All requirements_

  - [ ]* 20.2 Write edge case integration tests
    - Test with empty requirements
    - Test with ambiguous requirements
    - Test with Docker not running
    - Test with network failures during package installation
    - Test with insufficient system resources
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 21. Create documentation and examples
  - [ ] 21.1 Write user documentation
    - Create comprehensive README.md with system overview and quick start guide
    - Document installation and setup instructions (dependencies, Docker, API keys)
    - Document workflow execution examples with screenshots/output
    - Document configuration options and environment variables
    - Document troubleshooting common issues
    - Create API reference documentation for all public classes and methods
    - _Requirements: All requirements_

  - [ ] 21.2 Create example applications
    - Create example: simple todo app with CRUD operations (requirements.md, expected output)
    - Create example: blog platform with user authentication (requirements.md, expected output)
    - Create example: e-commerce app with payment integration (requirements.md, expected output)
    - Add video walkthrough or animated GIFs demonstrating workflow execution
    - _Requirements: All requirements_

- [ ] 22. Final checkpoint - Ensure all tests pass and system is complete
  - Run complete test suite (unit, integration, property tests)
  - Verify all code passes linting and type checking (pylint, mypy)
  - Test end-to-end workflow with all example applications
  - Verify Docker configurations work correctly
  - Verify checkpointing and resumption work correctly
  - Verify all documentation is complete and accurate
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Implementation follows bottom-up approach: data models → individual agents → orchestration → testing
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- Self-evaluation loops are critical for agent quality - ensure retry logic and approval requests work correctly
- Checkpointing enables workflow resumption - test thoroughly with interruptions
- Docker dependencies require validation before workflow execution begins
- Configuration management must prevent hardcoded credentials in all generated code

## Recommended Next Steps

Based on the current implementation status, here's the recommended order for completing remaining work:

1. **Task 15.1** - Complete human approval mechanism (enables user control over critical operations)
2. **Task 17.1** - Add Docker validation and directory management (essential for production readiness)
3. **Task 17.2** - Implement workflow resumption (enables recovery from interruptions)
4. **Task 18.1** - Create monitoring infrastructure (visibility into workflow execution)
5. **Task 19.1** - Implement configuration validation (prevent security issues)
6. **Tasks 20.1-20.2** - Write integration tests (validate end-to-end behavior)
7. **Tasks 21.1-21.2** - Create documentation and examples (enable user adoption)
8. **Task 22** - Final validation and testing

Optional testing tasks (marked with `*`) can be executed in parallel or skipped for MVP.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.2", "2.3", "3.2", "4.2", "4.3"] },
    { "id": 1, "tasks": ["6.2", "6.3", "7.2", "8.2", "8.3"] },
    { "id": 2, "tasks": ["9.3", "10.3", "12.3", "12.4"] },
    { "id": 3, "tasks": ["13.3", "13.4", "14.3", "15.1"] },
    { "id": 4, "tasks": ["15.2", "17.1"] },
    { "id": 5, "tasks": ["17.2", "18.1", "19.1"] },
    { "id": 6, "tasks": ["17.3", "18.2", "18.3", "19.2"] },
    { "id": 7, "tasks": ["20.1", "20.2", "21.1"] },
    { "id": 8, "tasks": ["21.2"] }
  ]
}
```
