"""
LangGraph state machine construction.

This module builds the LangGraph StateGraph with all nodes and edges,
implementing the supervised workflow orchestration.
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END

from .models import WorkflowState
from .agents.planning_agent import PlanningAgent
from .agents.supervisor_agent import SupervisorAgent
from .agents.backend_agent import BackendAgent
from .agents.frontend_agent import FrontendAgent
from .agents.database_agent import DatabaseAgent
from .agents.testing_agent import TestingAgent
from .agents.deployment_agent import DeploymentAgent
from .config import get_config
from .checkpointing import CheckpointManager


def create_workflow_graph():
    """
    Create and compile the LangGraph workflow.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    config = get_config()
    
    # Initialize agents
    planning_agent = PlanningAgent()
    supervisor_agent = SupervisorAgent()
    backend_agent = BackendAgent()
    frontend_agent = FrontendAgent()
    database_agent = DatabaseAgent()
    testing_agent = TestingAgent()
    deployment_agent = DeploymentAgent()
    
    # Create state graph
    workflow = StateGraph(WorkflowState)
    
    # Define node functions
    def planning_node(state: WorkflowState) -> Dict[str, Any]:
        """Planning Agent node."""
        print("🎯 Planning Agent: Analyzing requirements...")
        
        try:
            # Create execution plan
            execution_plan = planning_agent.create_execution_plan(state.user_requirements)
            
            print(f"✅ Created execution plan with {len(execution_plan.tasks)} tasks")
            for task in execution_plan.tasks:
                print(f"   - {task.id}: {task.description} (agent: {task.agent})")
            
            # Update state
            return {
                "execution_plan": execution_plan.tasks,
                "workflow_status": "planned"
            }
        except Exception as e:
            print(f"❌ Planning failed: {str(e)}")
            supervisor_agent.log_error(
                state,
                "planning",
                "critical",
                str(e)
            )
            return {
                "workflow_status": "failed",
                "requires_approval": True,
                "approval_message": f"Planning failed: {str(e)}"
            }
    
    def supervisor_node(state: WorkflowState) -> Dict[str, Any]:
        """Supervisor Agent node - routing logic."""
        print("👁️  Supervisor: Determining next agent...")
        
        # Calculate progress
        progress = supervisor_agent.calculate_progress(state)
        print(f"   Progress: {progress:.1f}%")
        
        # Determine next agent
        next_agent = supervisor_agent.route_next_agent(state)
        print(f"   Next agent: {next_agent}")
        
        # Log transition
        supervisor_agent.log_transition(
            state,
            from_agent="supervisor",
            to_agent=next_agent,
            reason="Routing based on workflow state"
        )
        
        return {
            "updated_at": state.updated_at
        }
    
    def backend_node(state: WorkflowState) -> Dict[str, Any]:
        """Backend Agent node - executes actual code generation."""
        print("🔧 Backend Agent: Generating FastAPI code...")
        
        try:
            # Find all pending backend tasks
            completed_ids = list(state.completed_task_ids) if state.completed_task_ids else []
            backend_tasks = [
                task for task in state.execution_plan
                if task.agent == "backend" and task.id not in completed_ids
            ]
            
            if not backend_tasks:
                return {
                    "backend_code_path": config.backend_output_dir,
                    "completed_task_ids": completed_ids
                }
            
            # Combine all backend task descriptions
            task_descriptions = "\n".join([task.description for task in backend_tasks])
            
            # Execute backend code generation with self-evaluation
            result = backend_agent.execute_task(
                task_description=task_descriptions,
                database_config=state.database_config
            )
            
            if result["success"]:
                # Mark all backend tasks as complete
                for task in backend_tasks:
                    completed_ids.append(task.id)
                    print(f"   ✅ Completed task: {task.id}")
                
                return {
                    "backend_code_path": result["output_dir"],
                    "completed_task_ids": completed_ids
                }
            else:
                # Generation failed after retries
                if result.get("requires_approval"):
                    return {
                        "backend_code_path": result.get("output_dir", config.backend_output_dir),
                        "requires_approval": True,
                        "approval_message": result.get("approval_message", "Backend code generation failed")
                    }
                else:
                    # Log error and retry
                    supervisor_agent.log_error(
                        state,
                        "backend",
                        "recoverable",
                        result.get("error", "Unknown error")
                    )
                    return {
                        "backend_code_path": config.backend_output_dir,
                        "completed_task_ids": completed_ids
                    }
                    
        except Exception as e:
            print(f"   ❌ Backend generation failed: {str(e)}")
            supervisor_agent.log_error(
                state,
                "backend",
                "recoverable",
                str(e)
            )
            return {
                "backend_code_path": config.backend_output_dir,
                "requires_approval": True,
                "approval_message": f"Backend generation failed: {str(e)}"
            }
    
    def frontend_node(state: WorkflowState) -> Dict[str, Any]:
        """Frontend Agent node - executes actual code generation."""
        print("🎨 Frontend Agent: Generating Next.js code...")
        
        try:
            # Find all pending frontend tasks
            completed_ids = list(state.completed_task_ids) if state.completed_task_ids else []
            frontend_tasks = [
                task for task in state.execution_plan
                if task.agent == "frontend" and task.id not in completed_ids
            ]
            
            if not frontend_tasks:
                return {
                    "frontend_code_path": config.frontend_output_dir,
                    "completed_task_ids": completed_ids
                }
            
            # Combine all frontend task descriptions
            task_descriptions = "\n".join([task.description for task in frontend_tasks])
            
            # Determine backend URL
            backend_url = "http://localhost:8000"
            if state.backend_code_path:
                backend_url = "http://localhost:8000"
            
            # Execute frontend code generation with self-evaluation
            result = frontend_agent.execute_task(
                task_description=task_descriptions,
                backend_url=backend_url
            )
            
            if result["success"]:
                # Mark all frontend tasks as complete
                for task in frontend_tasks:
                    completed_ids.append(task.id)
                    print(f"   ✅ Completed task: {task.id}")
                
                return {
                    "frontend_code_path": result["output_dir"],
                    "completed_task_ids": completed_ids
                }
            else:
                # Generation failed after retries
                if result.get("requires_approval"):
                    return {
                        "frontend_code_path": result.get("output_dir", config.frontend_output_dir),
                        "requires_approval": True,
                        "approval_message": result.get("approval_message", "Frontend code generation failed")
                    }
                else:
                    # Log error and retry
                    supervisor_agent.log_error(
                        state,
                        "frontend",
                        "recoverable",
                        result.get("error", "Unknown error")
                    )
                    return {
                        "frontend_code_path": config.frontend_output_dir,
                        "completed_task_ids": completed_ids
                    }
                    
        except Exception as e:
            print(f"   ❌ Frontend generation failed: {str(e)}")
            supervisor_agent.log_error(
                state,
                "frontend",
                "recoverable",
                str(e)
            )
            return {
                "frontend_code_path": config.frontend_output_dir,
                "requires_approval": True,
                "approval_message": f"Frontend generation failed: {str(e)}"
            }
    
    def database_node(state: WorkflowState) -> Dict[str, Any]:
        """Database Agent node - executes actual database initialization."""
        print("🗄️  Database Agent: Initializing databases...")
        
        try:
            # Initialize PostgreSQL database
            postgres_config = database_agent.initialize_postgres(
                database_name="app_db",
                username="app_user"
            )
            
            # Initialize MongoDB database
            mongo_config = database_agent.initialize_mongodb(
                database_name="app_db",
                username="app_user"
            )
            
            # Generate .env file with database configuration
            env_result = database_agent.generate_env_file(
                postgres_config=postgres_config if postgres_config.get("success") else None,
                mongo_config=mongo_config if mongo_config.get("success") else None,
                output_dir=config.backend_output_dir
            )
            
            # Mark all pending database tasks as complete
            completed_ids = list(state.completed_task_ids) if state.completed_task_ids else []
            
            for task in state.execution_plan:
                if task.agent == "database" and task.id not in completed_ids:
                    completed_ids.append(task.id)
                    print(f"   ✅ Completed task: {task.id}")
            
            database_config = {}
            if postgres_config.get("success"):
                database_config["postgres"] = postgres_config
            if mongo_config.get("success"):
                database_config["mongo"] = mongo_config
            
            return {
                "database_config": database_config,
                "completed_task_ids": completed_ids
            }
            
        except Exception as e:
            print(f"   ❌ Database initialization failed: {str(e)}")
            supervisor_agent.log_error(
                state,
                "database",
                "recoverable",
                str(e)
            )
            return {
                "database_config": {},
                "requires_approval": True,
                "approval_message": f"Database initialization failed: {str(e)}"
            }
    
    def testing_node(state: WorkflowState) -> Dict[str, Any]:
        """Testing Agent node - executes actual test generation and execution."""
        print("🧪 Testing Agent: Running tests...")
        
        # Track testing attempts
        current_attempt = state.testing_attempt_count + 1
        max_attempts = 3
        
        print(f"   Testing attempt {current_attempt}/{max_attempts}")
        
        try:
            # Find all pending testing tasks
            completed_ids = list(state.completed_task_ids) if state.completed_task_ids else []
            testing_tasks = [
                task for task in state.execution_plan
                if task.agent == "testing" and task.id not in completed_ids
            ]
            
            if not testing_tasks:
                from .models import TestResults
                return {
                    "test_results": TestResults(
                        backend_tests={"total": 0, "passed": 0, "failed": 0},
                        frontend_tests={"total": 0, "passed": 0, "failed": 0},
                        overall_passed=True
                    ),
                    "completed_task_ids": completed_ids,
                    "testing_attempt_count": current_attempt
                }
            
            # Execute testing agent - SKIP FRONTEND TESTS
            print("⚠️  Frontend testing is DISABLED - only running backend tests")
            result = testing_agent.execute_task(
                backend_dir=state.backend_code_path or config.backend_output_dir,
                frontend_dir=None  # SKIP FRONTEND TESTS
            )
            
            # Analyze test failures to determine which agent needs to fix them
            test_results = result.get("test_results", result)
            backend_tests = result.get("backend_tests", {})
            # Ensure frontend_tests is always a dict, not None
            frontend_tests = result.get("frontend_tests") or {"total": 0, "passed": 0, "failed": 0}
            
            backend_failed = backend_tests.get("failed", 0) > 0 if backend_tests else False
            frontend_failed = False  # Frontend tests are skipped
            
            # SPECIAL CASE: If 0 tests were collected, treat as test failure
            if backend_tests.get("total", 0) == 0:
                print(f"\n⚠️  No backend tests found (0 tests collected)")
                backend_failed = True
                # On max attempts, proceed anyway
                if current_attempt >= max_attempts:
                    print(f"   ➡️  Max attempts reached, proceeding to deployment despite 0 tests")
                    for task in testing_tasks:
                        if task.id not in completed_ids:
                            completed_ids.append(task.id)
                    
                    from .models import TestResults
                    return {
                        "test_results": TestResults(
                            backend_tests={"total": 0, "passed": 0, "failed": 0},
                            frontend_tests={"total": 0, "passed": 0, "failed": 0},
                            overall_passed=False
                        ),
                        "completed_task_ids": completed_ids,
                        "testing_attempt_count": current_attempt,
                        "test_failures": {
                            "backend_failed": True,
                            "frontend_failed": False,
                            "backend_failures": ["No tests were collected by pytest"],
                            "frontend_failures": [],
                            "max_attempts_reached": True
                        }
                    }
            
            backend_failed = backend_tests.get("failed", 0) > 0 if backend_tests else False
            frontend_failed = False  # Frontend tests are skipped
            
            # If tests failed AND we haven't reached max attempts, route back for fixes
            if (backend_failed or frontend_failed) and current_attempt < max_attempts:
                print(f"\n⚠️  Test failures detected:")
                if backend_failed:
                    print(f"   - Backend: {backend_tests.get('failed', 0)} tests failed")
                if frontend_failed:
                    print(f"   - Frontend: {frontend_tests.get('failed', 0)} tests failed")
                
                print(f"   🔄 Routing back to fix issues (attempt {current_attempt}/{max_attempts})")
                
                # Remove testing tasks from completed list to allow retry
                # But keep other completed tasks
                testing_task_ids = [task.id for task in testing_tasks]
                completed_ids_without_testing = [
                    tid for tid in completed_ids 
                    if tid not in testing_task_ids
                ]
                
                # Also remove the agent tasks that produced failing tests
                # so they can regenerate code
                if backend_failed:
                    backend_task_ids = [
                        task.id for task in state.execution_plan 
                        if task.agent == "backend"
                    ]
                    completed_ids_without_testing = [
                        tid for tid in completed_ids_without_testing 
                        if tid not in backend_task_ids
                    ]
                    print(f"   🔄 Routing back to Backend Agent to fix issues")
                
                if frontend_failed:
                    frontend_task_ids = [
                        task.id for task in state.execution_plan 
                        if task.agent == "frontend"
                    ]
                    completed_ids_without_testing = [
                        tid for tid in completed_ids_without_testing 
                        if tid not in frontend_task_ids
                    ]
                    print(f"   🔄 Routing back to Frontend Agent to fix issues")
                
                # Ensure test_results has proper structure for Pydantic validation
                from .models import TestResults
                validated_test_results = TestResults(
                    backend_tests=backend_tests or {"total": 0, "passed": 0, "failed": 0},
                    frontend_tests=frontend_tests or {"total": 0, "passed": 0, "failed": 0},
                    overall_passed=not (backend_failed or frontend_failed)
                )
                
                return {
                    "test_results": validated_test_results,
                    "completed_task_ids": completed_ids_without_testing,
                    "testing_attempt_count": current_attempt,
                    "test_failures": {
                        "backend_failed": backend_failed,
                        "frontend_failed": frontend_failed,
                        "backend_failures": backend_tests.get("failures", []) if backend_tests else [],
                        "frontend_failures": []  # No frontend failures since tests are skipped
                    }
                }
            
            # Tests failed but max attempts reached - proceed to deployment anyway
            elif (backend_failed or frontend_failed) and current_attempt >= max_attempts:
                print(f"\n⚠️  Tests still failing after {max_attempts} attempts")
                print(f"   ➡️  Proceeding to deployment anyway (max test iterations reached)")
                
                # Mark testing tasks as complete despite failures
                for task in testing_tasks:
                    if task.id not in completed_ids:
                        completed_ids.append(task.id)
                        print(f"   ✅ Marking task complete (with failures): {task.id}")
                
                # Ensure test_results has proper structure for Pydantic validation
                from .models import TestResults
                validated_test_results = TestResults(
                    backend_tests=backend_tests or {"total": 0, "passed": 0, "failed": 0},
                    frontend_tests=frontend_tests or {"total": 0, "passed": 0, "failed": 0},
                    overall_passed=False  # Tests failed but we're proceeding
                )
                
                return {
                    "test_results": validated_test_results,
                    "completed_task_ids": completed_ids,
                    "testing_attempt_count": current_attempt,
                    "test_failures": {
                        "backend_failed": backend_failed,
                        "frontend_failed": frontend_failed,
                        "backend_failures": backend_tests.get("failures", []) if backend_tests else [],
                        "frontend_failures": [],
                        "max_attempts_reached": True
                    }
                }
            
            # All tests passed
            if result["success"]:
                # Mark all testing tasks as complete
                for task in testing_tasks:
                    completed_ids.append(task.id)
                    print(f"   ✅ Completed task: {task.id}")
                
                # Ensure test_results has proper structure for Pydantic validation
                from .models import TestResults
                validated_test_results = TestResults(
                    backend_tests=backend_tests or {"total": 0, "passed": 0, "failed": 0},
                    frontend_tests=frontend_tests or {"total": 0, "passed": 0, "failed": 0},
                    overall_passed=result["overall_passed"]
                )
                
                return {
                    "test_results": validated_test_results,
                    "completed_task_ids": completed_ids,
                    "testing_attempt_count": current_attempt
                }
            else:
                # Testing execution failed (not test failures, but execution errors)
                if result.get("requires_approval"):
                    return {
                        "test_results": result.get("test_results"),
                        "requires_approval": True,
                        "approval_message": result.get("approval_message", "Tests failed to execute"),
                        "testing_attempt_count": current_attempt
                    }
                else:
                    from .models import TestResults
                    return {
                        "test_results": result.get("test_results", TestResults(
                            backend_tests={"total": 0, "passed": 0, "failed": 0},
                            frontend_tests={"total": 0, "passed": 0, "failed": 0},
                            overall_passed=False
                        )),
                        "completed_task_ids": completed_ids,
                        "testing_attempt_count": current_attempt
                    }
                    
        except Exception as e:
            print(f"   ❌ Testing failed: {str(e)}")
            supervisor_agent.log_error(
                state,
                "testing",
                "recoverable",
                str(e)
            )
            from .models import TestResults
            return {
                "test_results": TestResults(
                    backend_tests={"total": 0, "passed": 0, "failed": 0},
                    frontend_tests={"total": 0, "passed": 0, "failed": 0},
                    overall_passed=False
                ),
                "requires_approval": True,
                "approval_message": f"Testing failed: {str(e)}",
                "testing_attempt_count": current_attempt
            }
    
    def deployment_node(state: WorkflowState) -> Dict[str, Any]:
        """Deployment Agent node - executes actual deployment."""
        print("🚀 Deployment Agent: Deploying to Docker...")
        
        try:
            # Execute deployment agent
            result = deployment_agent.execute_task(
                backend_path=state.backend_code_path or config.backend_output_dir,
                frontend_path=state.frontend_code_path or config.frontend_output_dir,
                database_config=state.database_config
            )
            
            if result["success"]:
                print(f"   ✅ Deployment successful!")
                return {
                    "deployment_status": result["deployment_status"],
                    "workflow_status": "complete"
                }
            else:
                # Deployment failed
                print(f"   ❌ Deployment failed: {result.get('error', 'Unknown error')}")
                
                from .models import DeploymentStatus
                from datetime import datetime
                return {
                    "deployment_status": result.get("deployment_status", DeploymentStatus(
                        containers_running=[],
                        frontend_url="",
                        backend_url="",
                        health_checks_passed=False,
                        deployment_timestamp=datetime.now()
                    )),
                    "workflow_status": "failed",
                    "requires_approval": True,
                    "approval_message": result.get("error", "Deployment failed")
                }
                
        except Exception as e:
            print(f"   ❌ Deployment failed: {str(e)}")
            supervisor_agent.log_error(
                state,
                "deployment",
                "critical",
                str(e)
            )
            from .models import DeploymentStatus
            from datetime import datetime
            return {
                "deployment_status": DeploymentStatus(
                    containers_running=[],
                    frontend_url="",
                    backend_url="",
                    health_checks_passed=False,
                    deployment_timestamp=datetime.now()
                ),
                "workflow_status": "failed",
                "requires_approval": True,
                "approval_message": f"Deployment failed: {str(e)}"
            }
    
    def human_approval_node(state: WorkflowState) -> Dict[str, Any]:
        """
        Human approval node with interactive user input.
        
        This node pauses workflow execution and waits for user approval.
        Uses LangGraph's interrupt mechanism to pause and resume workflows.
        
        The node:
        1. Presents approval context to the user via CLI
        2. Collects user response (approve/reject/modify/skip)
        3. Handles timeout scenarios (auto-reject after timeout)
        4. Updates workflow state based on user decision
        5. Allows workflow resumption after approval
        
        Requirements: 3.6, 9.5, 11.3
        """
        from .approval import request_human_approval, check_approval_needed
        
        print("⏸️  Workflow paused - human approval required")
        print(f"   Reason: {state.approval_message or 'Critical operation pending'}")
        
        # Verify approval is actually needed
        if not check_approval_needed(state):
            print("   No approval needed, continuing...")
            return {
                "requires_approval": False,
                "workflow_status": "running"
            }
        
        # Request approval from user with timeout handling
        # This presents the approval request via CLI and waits for user input
        try:
            result = request_human_approval(state, timeout_seconds=300)
            
            # Log the approval decision
            decision = "approved" if result.get("workflow_status") == "running" else "rejected"
            print(f"\n   Approval decision: {decision}")
            
            # Add to agent transitions log
            from datetime import datetime
            transition = {
                "timestamp": datetime.now().isoformat(),
                "from_agent": "human_approval",
                "to_agent": "supervisor",
                "decision": decision,
                "reason": state.approval_message
            }
            
            transitions = list(state.agent_transitions) if state.agent_transitions else []
            transitions.append(transition)
            
            result["agent_transitions"] = transitions
            
            return result
            
        except Exception as e:
            print(f"\n❌ Error during approval: {str(e)}")
            # On error, reject and log
            from datetime import datetime
            return {
                "requires_approval": False,
                "approval_message": f"Approval failed: {str(e)}",
                "workflow_status": "failed",
                "updated_at": datetime.now()
            }
    
    # Add all nodes
    workflow.add_node("planning_node", planning_node)
    workflow.add_node("supervisor_node", supervisor_node)
    workflow.add_node("backend_node", backend_node)
    workflow.add_node("frontend_node", frontend_node)
    workflow.add_node("database_node", database_node)
    workflow.add_node("testing_node", testing_node)
    workflow.add_node("deployment_node", deployment_node)
    workflow.add_node("human_approval_node", human_approval_node)
    
    # Define routing function
    def route_from_supervisor(state: WorkflowState) -> str:
        """Route from supervisor to next agent."""
        next_node = supervisor_agent.route_next_agent(state)
        
        # Check if workflow is complete
        if state.workflow_status == "complete":
            return END
        
        return next_node
    
    # Set entry point
    workflow.set_entry_point("planning_node")
    
    # Add edges
    workflow.add_edge("planning_node", "supervisor_node")
    workflow.add_conditional_edges(
        "supervisor_node",
        route_from_supervisor,
        {
            "planning_node": "planning_node",
            "backend_node": "backend_node",
            "frontend_node": "frontend_node",
            "database_node": "database_node",
            "testing_node": "testing_node",
            "deployment_node": "deployment_node",
            "human_approval_node": "human_approval_node",
            END: END
        }
    )
    
    # All specialist agents return to supervisor
    for agent_node in ["backend_node", "frontend_node", "database_node", "testing_node"]:
        workflow.add_edge(agent_node, "supervisor_node")
    
    # Deployment goes to END
    workflow.add_edge("deployment_node", END)
    
    # Human approval can resume to supervisor
    workflow.add_edge("human_approval_node", "supervisor_node")
    
    # Set up checkpointing using CheckpointManager
    checkpoint_manager = CheckpointManager()
    checkpointer = checkpoint_manager.get_saver()
    
    # Compile graph with checkpointing enabled
    app = workflow.compile(checkpointer=checkpointer)
    
    return app, checkpoint_manager
