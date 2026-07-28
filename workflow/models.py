"""
Core data models for the workflow system.

This module defines Pydantic models for workflow state, task definitions,
error records, test results, and deployment status.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TaskDefinition(BaseModel):
    """Individual task in the execution plan."""
    
    id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="Task description")
    agent: str = Field(..., description="Which specialist agent handles this task")
    dependencies: List[str] = Field(default_factory=list, description="Task IDs that must complete first")
    estimated_duration: str = Field(default="Unknown", description="Estimated time to complete")
    status: str = Field(default="pending", description="Task status: pending, in_progress, complete, failed")


class ErrorRecord(BaseModel):
    """Error information for debugging and recovery."""
    
    timestamp: datetime = Field(default_factory=datetime.now, description="When the error occurred")
    agent: str = Field(..., description="Agent that encountered the error")
    task_id: str = Field(..., description="Task ID where error occurred")
    error_type: str = Field(..., description="Error classification: transient, recoverable, critical")
    message: str = Field(..., description="Error message")
    traceback: Optional[str] = Field(None, description="Stack trace for debugging")
    retry_count: int = Field(default=0, description="Number of retries attempted")


class TestResults(BaseModel):
    """Test execution results."""
    
    backend_tests: Dict[str, Any] = Field(default_factory=dict, description="Backend test results")
    frontend_tests: Dict[str, Any] = Field(default_factory=dict, description="Frontend test results")
    overall_passed: bool = Field(default=False, description="Whether all tests passed")


class DeploymentStatus(BaseModel):
    """Deployment state and service information."""
    
    containers_running: List[str] = Field(default_factory=list, description="List of running container names")
    frontend_url: Optional[str] = Field(None, description="Frontend service URL")
    backend_url: Optional[str] = Field(None, description="Backend service URL")
    health_checks_passed: bool = Field(default=False, description="Whether health checks passed")
    deployment_timestamp: Optional[datetime] = Field(None, description="When deployment completed")


class ExecutionPlan(BaseModel):
    """Structured plan from Planning Agent."""
    
    tasks: List[TaskDefinition] = Field(default_factory=list, description="List of tasks to execute")
    dependency_graph: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="task_id -> [dependent_task_ids]"
    )
    estimated_total_duration: str = Field(default="Unknown", description="Estimated total time")
    required_agents: List[str] = Field(default_factory=list, description="Which agents are needed")
    
    def get_next_task(self, completed: List[str]) -> Optional[TaskDefinition]:
        """
        Get next executable task based on dependencies.
        
        Args:
            completed: List of completed task IDs
            
        Returns:
            Next task that can be executed, or None if no tasks available
        """
        for task in self.tasks:
            # Skip if already completed
            if task.id in completed:
                continue
            
            # Check if all dependencies are satisfied
            if all(dep in completed for dep in task.dependencies):
                return task
        
        return None
    
    def validate_completeness(self, requirements: str) -> bool:
        """
        Check that all requirements map to at least one task.
        
        Args:
            requirements: User requirements string
            
        Returns:
            True if requirements are covered, False otherwise
        """
        # Basic validation: ensure we have tasks
        if not self.tasks:
            return False
        
        # More sophisticated validation would involve NLP analysis
        # For now, we ensure basic coverage
        return len(self.tasks) > 0 and all(
            task.agent in self.required_agents for task in self.tasks
        )


class AgentMessage(BaseModel):
    """Inter-agent communication message."""
    
    from_agent: str = Field(..., description="Sending agent")
    to_agent: str = Field(..., description="Receiving agent")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    message_type: str = Field(..., description="Message type: task_assignment, result, error, approval_request")
    content: Dict[str, Any] = Field(default_factory=dict, description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class WorkflowState(BaseModel):
    """Complete state persisted at each checkpoint."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Core workflow data
    thread_id: str = Field(..., description="Unique workflow execution ID")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Agent communication history")
    
    # Planning and execution
    user_requirements: str = Field(..., description="Requirements text or file path")
    requirements_source: str = Field(default="text", description="Source type: 'text' or 'file'")
    context_file_path: Optional[str] = Field(None, description="Original file path if requirements from file")
    execution_plan: List[TaskDefinition] = Field(default_factory=list, description="Task execution plan")
    current_task_id: Optional[str] = Field(None, description="Currently executing task ID")
    completed_task_ids: List[str] = Field(default_factory=list, description="Completed task IDs")
    
    # Agent outputs
    backend_code_path: Optional[str] = Field(None, description="Path to generated backend code")
    frontend_code_path: Optional[str] = Field(None, description="Path to generated frontend code")
    database_config: Optional[Dict[str, Any]] = Field(None, description="Database configuration")
    test_results: Optional[TestResults] = Field(None, description="Test execution results")
    test_failures: Optional[Dict[str, Any]] = Field(None, description="Test failure details for routing decisions")
    deployment_status: Optional[DeploymentStatus] = Field(None, description="Deployment status")
    
    # Error handling and recovery
    error_log: List[ErrorRecord] = Field(default_factory=list, description="Error history")
    retry_counts: Dict[str, int] = Field(default_factory=dict, description="agent -> retry count")
    testing_attempt_count: int = Field(default=0, description="Number of testing iterations attempted")
    
    # Workflow control
    requires_approval: bool = Field(default=False, description="Whether human approval is needed")
    approval_message: Optional[str] = Field(None, description="Approval request message")
    workflow_status: str = Field(default="running", description="Status: running, paused, complete, failed")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Workflow creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    agent_transitions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of agent transitions"
    )
