#!/usr/bin/env python3
"""
Comprehensive validation test for all Pydantic models against design requirements.
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

def test_execution_plan_validate_completeness():
    """Test ExecutionPlan.validate_completeness method."""
    task1 = TaskDefinition(
        id="task_1",
        description="Setup database",
        agent="database",
        dependencies=[]
    )
    
    # Test with tasks
    plan = ExecutionPlan(
        tasks=[task1],
        dependency_graph={},
        estimated_total_duration="5 min",
        required_agents=["database"]
    )
    
    result = plan.validate_completeness("Build a database")
    assert result == True, "validate_completeness should return True when tasks exist"
    
    # Test with empty tasks
    empty_plan = ExecutionPlan(
        tasks=[],
        dependency_graph={},
        estimated_total_duration="0 min",
        required_agents=[]
    )
    
    result = empty_plan.validate_completeness("Build something")
    assert result == False, "validate_completeness should return False when no tasks"
    
    print("✅ ExecutionPlan.validate_completeness works correctly")

def test_workflow_state_default_values():
    """Test that WorkflowState has proper default values."""
    state = WorkflowState(
        thread_id="test_thread",
        user_requirements="Test requirements"
    )
    
    # Check defaults
    assert state.messages == [], "messages should default to empty list"
    assert state.requirements_source == "text", "requirements_source should default to 'text'"
    assert state.execution_plan == [], "execution_plan should default to empty list"
    assert state.completed_task_ids == [], "completed_task_ids should default to empty list"
    assert state.error_log == [], "error_log should default to empty list"
    assert state.retry_counts == {}, "retry_counts should default to empty dict"
    assert state.requires_approval == False, "requires_approval should default to False"
    assert state.workflow_status == "running", "workflow_status should default to 'running'"
    assert state.agent_transitions == [], "agent_transitions should default to empty list"
    
    print("✅ WorkflowState default values are correct")

def test_task_definition_status_values():
    """Test TaskDefinition status field accepts expected values."""
    statuses = ["pending", "in_progress", "complete", "failed"]
    
    for status in statuses:
        task = TaskDefinition(
            id=f"task_{status}",
            description="Test task",
            agent="test",
            dependencies=[],
            status=status
        )
        assert task.status == status
    
    print("✅ TaskDefinition status field accepts all expected values")

def test_error_record_types():
    """Test ErrorRecord accepts expected error types."""
    error_types = ["transient", "recoverable", "critical"]
    
    for error_type in error_types:
        error = ErrorRecord(
            agent="test_agent",
            task_id="task_1",
            error_type=error_type,
            message="Test error"
        )
        assert error.error_type == error_type
    
    print("✅ ErrorRecord accepts all expected error types")

def test_agent_message_types():
    """Test AgentMessage accepts expected message types."""
    message_types = ["task_assignment", "result", "error", "approval_request"]
    
    for msg_type in message_types:
        message = AgentMessage(
            from_agent="sender",
            to_agent="receiver",
            message_type=msg_type,
            content={}
        )
        assert message.message_type == msg_type
    
    print("✅ AgentMessage accepts all expected message types")

def test_workflow_state_with_file_requirements():
    """Test WorkflowState with file path as requirements."""
    state = WorkflowState(
        thread_id="test_file",
        user_requirements="path/to/requirements.md",
        requirements_source="file"
    )
    
    assert state.user_requirements == "path/to/requirements.md"
    assert state.requirements_source == "file"
    
    print("✅ WorkflowState supports file path requirements")

def test_deployment_status_optional_fields():
    """Test DeploymentStatus with optional fields as None."""
    status = DeploymentStatus()
    
    assert status.containers_running == [], "containers_running should default to empty list"
    assert status.frontend_url is None, "frontend_url should default to None"
    assert status.backend_url is None, "backend_url should default to None"
    assert status.health_checks_passed == False, "health_checks_passed should default to False"
    assert status.deployment_timestamp is None, "deployment_timestamp should default to None"
    
    print("✅ DeploymentStatus optional fields have correct defaults")

def test_test_results_structure():
    """Test TestResults can hold detailed test information."""
    results = TestResults(
        backend_tests={
            "total": 45,
            "passed": 43,
            "failed": 2,
            "coverage": 87.3,
            "failures": [
                {
                    "test": "test_user_authentication",
                    "error": "AssertionError: Expected 200, got 401"
                }
            ]
        },
        frontend_tests={
            "total": 32,
            "passed": 32,
            "failed": 0,
            "coverage": 92.1,
            "failures": []
        },
        overall_passed=False
    )
    
    assert results.backend_tests["total"] == 45
    assert results.backend_tests["coverage"] == 87.3
    assert len(results.backend_tests["failures"]) == 1
    assert results.frontend_tests["coverage"] == 92.1
    assert results.overall_passed == False
    
    print("✅ TestResults can hold detailed test information")

def test_execution_plan_get_next_task_complex():
    """Test ExecutionPlan.get_next_task with complex dependencies."""
    task1 = TaskDefinition(id="t1", description="Task 1", agent="a1", dependencies=[])
    task2 = TaskDefinition(id="t2", description="Task 2", agent="a2", dependencies=["t1"])
    task3 = TaskDefinition(id="t3", description="Task 3", agent="a3", dependencies=["t1"])
    task4 = TaskDefinition(id="t4", description="Task 4", agent="a4", dependencies=["t2", "t3"])
    
    plan = ExecutionPlan(
        tasks=[task1, task2, task3, task4],
        dependency_graph={
            "t1": [],
            "t2": ["t1"],
            "t3": ["t1"],
            "t4": ["t2", "t3"]
        },
        estimated_total_duration="20 min",
        required_agents=["a1", "a2", "a3", "a4"]
    )
    
    # Initially, only t1 can be executed
    next_task = plan.get_next_task(completed=[])
    assert next_task.id == "t1", "First task should be t1 (no dependencies)"
    
    # After t1, both t2 and t3 can be executed
    next_task = plan.get_next_task(completed=["t1"])
    assert next_task.id in ["t2", "t3"], "Next should be t2 or t3"
    
    # After t1 and t2, t3 can be executed
    next_task = plan.get_next_task(completed=["t1", "t2"])
    assert next_task.id == "t3", "Next should be t3"
    
    # After t1, t2, and t3, t4 can be executed
    next_task = plan.get_next_task(completed=["t1", "t2", "t3"])
    assert next_task.id == "t4", "Next should be t4"
    
    # After all tasks, None should be returned
    next_task = plan.get_next_task(completed=["t1", "t2", "t3", "t4"])
    assert next_task is None, "Should return None when all tasks complete"
    
    print("✅ ExecutionPlan.get_next_task handles complex dependencies correctly")

def main():
    """Run all comprehensive validation tests."""
    print("Running comprehensive Pydantic model validation tests...\n")
    
    try:
        test_execution_plan_validate_completeness()
        test_workflow_state_default_values()
        test_task_definition_status_values()
        test_error_record_types()
        test_agent_message_types()
        test_workflow_state_with_file_requirements()
        test_deployment_status_optional_fields()
        test_test_results_structure()
        test_execution_plan_get_next_task_complex()
        
        print("\n" + "=" * 60)
        print("✅ All validation tests passed!")
        print("✅ Models conform to design document specifications!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
