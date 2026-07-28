#!/usr/bin/env python3
"""
Test script to validate that all Pydantic models can be instantiated correctly.
"""

from datetime import datetime
from workflow.models import (
    TaskDefinition, 
    ErrorRecord, 
    TestResults, 
    DeploymentStatus, 
    WorkflowState, 
    ExecutionPlan, 
    AgentMessage
)

def test_task_definition():
    """Test TaskDefinition model instantiation."""
    task = TaskDefinition(
        id="task_1",
        description="Initialize PostgreSQL database",
        agent="database",
        dependencies=["task_0"],
        estimated_duration="2 minutes",
        status="pending"
    )
    assert task.id == "task_1"
    assert task.agent == "database"
    assert len(task.dependencies) == 1
    print("✅ TaskDefinition instantiation successful")

def test_error_record():
    """Test ErrorRecord model instantiation."""
    error = ErrorRecord(
        timestamp=datetime.now(),
        agent="backend",
        task_id="task_2",
        error_type="recoverable",
        message="Syntax error in generated code",
        traceback="Traceback...",
        retry_count=1
    )
    assert error.agent == "backend"
    assert error.error_type == "recoverable"
    assert error.retry_count == 1
    print("✅ ErrorRecord instantiation successful")

def test_test_results():
    """Test TestResults model instantiation."""
    results = TestResults(
        backend_tests={"total": 10, "passed": 8, "failed": 2},
        frontend_tests={"total": 15, "passed": 15, "failed": 0},
        overall_passed=False
    )
    assert results.backend_tests["total"] == 10
    assert results.frontend_tests["passed"] == 15
    assert results.overall_passed == False
    print("✅ TestResults instantiation successful")

def test_deployment_status():
    """Test DeploymentStatus model instantiation."""
    status = DeploymentStatus(
        containers_running=["frontend", "backend", "postgres"],
        frontend_url="http://localhost:3000",
        backend_url="http://localhost:8000",
        health_checks_passed=True,
        deployment_timestamp=datetime.now()
    )
    assert len(status.containers_running) == 3
    assert status.health_checks_passed == True
    assert status.frontend_url == "http://localhost:3000"
    print("✅ DeploymentStatus instantiation successful")

def test_execution_plan():
    """Test ExecutionPlan model instantiation."""
    task1 = TaskDefinition(
        id="task_1",
        description="Setup database",
        agent="database",
        dependencies=[],
        estimated_duration="2 min"
    )
    task2 = TaskDefinition(
        id="task_2",
        description="Generate backend",
        agent="backend",
        dependencies=["task_1"],
        estimated_duration="5 min"
    )
    
    plan = ExecutionPlan(
        tasks=[task1, task2],
        dependency_graph={"task_1": [], "task_2": ["task_1"]},
        estimated_total_duration="7 minutes",
        required_agents=["database", "backend"]
    )
    
    assert len(plan.tasks) == 2
    assert len(plan.required_agents) == 2
    
    # Test get_next_task method
    next_task = plan.get_next_task(completed=[])
    assert next_task.id == "task_1"  # Task with no dependencies
    
    next_task = plan.get_next_task(completed=["task_1"])
    assert next_task.id == "task_2"  # Task with satisfied dependencies
    
    next_task = plan.get_next_task(completed=["task_1", "task_2"])
    assert next_task is None  # No more tasks
    
    print("✅ ExecutionPlan instantiation and methods successful")

def test_agent_message():
    """Test AgentMessage model instantiation."""
    message = AgentMessage(
        from_agent="supervisor",
        to_agent="backend",
        timestamp=datetime.now(),
        message_type="task_assignment",
        content={"task_id": "task_2", "description": "Generate API endpoints"},
        metadata={"priority": "high"}
    )
    assert message.from_agent == "supervisor"
    assert message.to_agent == "backend"
    assert message.message_type == "task_assignment"
    print("✅ AgentMessage instantiation successful")

def test_workflow_state():
    """Test WorkflowState model instantiation."""
    state = WorkflowState(
        thread_id="thread_12345",
        messages=[{"role": "user", "content": "Build a todo app"}],
        user_requirements="Build a todo application with CRUD operations",
        requirements_source="text",
        execution_plan=[],
        current_task_id="task_1",
        completed_task_ids=[],
        backend_code_path=None,
        frontend_code_path=None,
        database_config=None,
        test_results=None,
        deployment_status=None,
        error_log=[],
        retry_counts={},
        requires_approval=False,
        approval_message=None,
        workflow_status="running",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        agent_transitions=[]
    )
    
    assert state.thread_id == "thread_12345"
    assert state.requirements_source == "text"
    assert state.workflow_status == "running"
    assert state.requires_approval == False
    print("✅ WorkflowState instantiation successful")

def main():
    """Run all model instantiation tests."""
    print("Testing Pydantic model instantiation...\n")
    
    try:
        test_task_definition()
        test_error_record()
        test_test_results()
        test_deployment_status()
        test_execution_plan()
        test_agent_message()
        test_workflow_state()
        
        print("\n" + "=" * 60)
        print("✅ All models can be instantiated correctly!")
        print("✅ All model methods work as expected!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
