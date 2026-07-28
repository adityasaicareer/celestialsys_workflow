#!/usr/bin/env python3
"""
Validation script to verify all required Pydantic models and fields are implemented.
"""

from workflow.models import (
    TaskDefinition, 
    ErrorRecord, 
    TestResults, 
    DeploymentStatus, 
    WorkflowState, 
    ExecutionPlan, 
    AgentMessage
)

def validate_model_fields(model_class, expected_fields):
    """Validate that a model has all expected fields."""
    model_fields = set(model_class.model_fields.keys())
    expected = set(expected_fields)
    
    missing = expected - model_fields
    extra = model_fields - expected
    
    if missing:
        print(f"❌ {model_class.__name__} missing fields: {missing}")
        return False
    
    print(f"✅ {model_class.__name__} has all required fields")
    if extra:
        print(f"   ℹ️  Additional fields: {extra}")
    return True

def main():
    print("Validating Pydantic models for Task 2.1...\n")
    
    all_valid = True
    
    # Validate TaskDefinition
    all_valid &= validate_model_fields(TaskDefinition, [
        'id', 'description', 'agent', 'dependencies', 'estimated_duration', 'status'
    ])
    
    # Validate ErrorRecord
    all_valid &= validate_model_fields(ErrorRecord, [
        'timestamp', 'agent', 'task_id', 'error_type', 'message', 'traceback', 'retry_count'
    ])
    
    # Validate TestResults
    all_valid &= validate_model_fields(TestResults, [
        'backend_tests', 'frontend_tests', 'overall_passed'
    ])
    
    # Validate DeploymentStatus
    all_valid &= validate_model_fields(DeploymentStatus, [
        'containers_running', 'frontend_url', 'backend_url', 'health_checks_passed', 'deployment_timestamp'
    ])
    
    # Validate WorkflowState (checking key required fields)
    all_valid &= validate_model_fields(WorkflowState, [
        'thread_id', 'messages', 'user_requirements', 'requirements_source', 
        'execution_plan', 'current_task_id', 'completed_task_ids',
        'backend_code_path', 'frontend_code_path', 'database_config',
        'test_results', 'deployment_status', 'error_log', 'retry_counts',
        'requires_approval', 'approval_message', 'workflow_status',
        'created_at', 'updated_at', 'agent_transitions'
    ])
    
    # Validate ExecutionPlan
    all_valid &= validate_model_fields(ExecutionPlan, [
        'tasks', 'dependency_graph', 'estimated_total_duration', 'required_agents'
    ])
    
    # Validate AgentMessage
    all_valid &= validate_model_fields(AgentMessage, [
        'from_agent', 'to_agent', 'timestamp', 'message_type', 'content', 'metadata'
    ])
    
    print("\n" + "=" * 60)
    if all_valid:
        print("✅ All models are correctly implemented!")
        print("Task 2.1 is COMPLETE")
    else:
        print("❌ Some models are missing required fields")
        print("Task 2.1 needs fixes")
    print("=" * 60)
    
    return 0 if all_valid else 1

if __name__ == "__main__":
    exit(main())
