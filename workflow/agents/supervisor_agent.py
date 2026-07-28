"""
Supervisor Agent: Orchestrates workflow execution and routing.

The Supervisor Agent is the central coordinator that:
- Determines which specialist agent executes next
- Routes tasks based on success/failure/approval needs
- Maintains execution logs and progress tracking
- Implements retry logic with exponential backoff
- Triggers human approval when needed
"""

from typing import Optional
from datetime import datetime

from ..models import WorkflowState, ErrorRecord
from ..config import get_config


class SupervisorAgent:
    """
    Supervisor Agent that orchestrates workflow execution.
    
    The supervisor implements conditional routing logic to determine
    which agent should execute next based on the current workflow state.
    """
    
    def __init__(self):
        """Initialize the Supervisor Agent."""
        self.config = get_config()
    
    def route_next_agent(self, state: WorkflowState) -> str:
        """
        Determine which agent should execute next.
        
        This is the core routing logic that:
        1. Checks if human approval is needed
        2. Checks if retry limits are exceeded
        3. Checks for errors that need fixing
        4. Routes to next task based on dependencies
        5. Routes to deployment when all tasks complete
        
        Args:
            state: Current workflow state
            
        Returns:
            Name of next agent node to execute
        """
        # Check if human approval is required
        if state.requires_approval:
            return "human_approval_node"
        
        # Check if current task has exceeded retry limit
        if state.current_task_id:
            retry_count = state.retry_counts.get(state.current_task_id, 0)
            if retry_count >= self.config.max_retries_per_agent:
                return "human_approval_node"
        
        # Check total retry count
        total_retries = sum(state.retry_counts.values())
        if total_retries >= self.config.max_total_retries:
            return "human_approval_node"
        
        # Check for errors that need fixing
        if self._has_recent_errors(state):
            # Route back to the agent that had errors for a retry
            last_error = state.error_log[-1]
            return self._agent_to_node(last_error.agent)
        
        # Get next task from execution plan
        from ..models import ExecutionPlan
        
        if not state.execution_plan:
            # No plan yet, need planning
            return "planning_node"
        
        # Convert list of TaskDefinition to ExecutionPlan for get_next_task method
        plan = ExecutionPlan(
            tasks=state.execution_plan,
            dependency_graph={},  # Will be built if needed
            estimated_total_duration="",
            required_agents=[]
        )
        
        next_task = plan.get_next_task(state.completed_task_ids)
        
        if next_task is None:
            # All tasks complete, check if we need testing
            if not state.test_results:
                return "testing_node"
            
            # Tests done, check if tests passed
            if state.test_results and state.test_results.overall_passed:
                # All tests passed, proceed to deployment
                return "deployment_node"
            else:
                # Tests failed, need to fix code
                # Route back to appropriate agent based on test failures
                if state.test_results.backend_tests.get("failed", 0) > 0:
                    return "backend_node"
                if state.test_results.frontend_tests.get("failed", 0) > 0:
                    return "frontend_node"
                return "testing_node"
        
        # Route to agent for next task
        return self._agent_to_node(next_task.agent)
    
    def _has_recent_errors(self, state: WorkflowState) -> bool:
        """
        Check if there are recent errors for current task.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if recent errors exist, False otherwise
        """
        if not state.error_log or not state.current_task_id:
            return False
        
        # Check last error matches current task
        last_error = state.error_log[-1]
        return last_error.task_id == state.current_task_id
    
    def _agent_to_node(self, agent_name: str) -> str:
        """
        Convert agent name to node name.
        
        Args:
            agent_name: Name of agent (e.g., 'backend')
            
        Returns:
            Node name (e.g., 'backend_node')
        """
        return f"{agent_name}_node"
    
    def log_transition(
        self,
        state: WorkflowState,
        from_agent: str,
        to_agent: str,
        reason: str = ""
    ) -> WorkflowState:
        """
        Log agent transition in workflow state.
        
        Args:
            state: Current workflow state
            from_agent: Agent transitioning from
            to_agent: Agent transitioning to
            reason: Reason for transition
            
        Returns:
            Updated workflow state
        """
        transition = {
            "timestamp": datetime.now().isoformat(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason,
            "task_id": state.current_task_id
        }
        
        state.agent_transitions.append(transition)
        state.updated_at = datetime.now()
        
        return state
    
    def calculate_progress(self, state: WorkflowState) -> float:
        """
        Calculate workflow progress percentage.
        
        Args:
            state: Current workflow state
            
        Returns:
            Progress percentage (0.0 to 100.0)
        """
        if not state.execution_plan:
            return 0.0
        
        total_tasks = len(state.execution_plan)
        completed_tasks = len(state.completed_task_ids)
        
        if total_tasks == 0:
            return 0.0
        
        return (completed_tasks / total_tasks) * 100.0
    
    def estimate_remaining_time(
        self,
        state: WorkflowState,
        elapsed_seconds: float
    ) -> Optional[float]:
        """
        Estimate remaining time based on current progress.
        
        Args:
            state: Current workflow state
            elapsed_seconds: Time elapsed since workflow start
            
        Returns:
            Estimated remaining seconds, or None if cannot estimate
        """
        progress = self.calculate_progress(state)
        
        if progress <= 0 or progress >= 100:
            return None
        
        # Estimate based on linear extrapolation
        estimated_total = elapsed_seconds / (progress / 100.0)
        remaining = estimated_total - elapsed_seconds
        
        return max(0.0, remaining)
    
    def should_request_approval(
        self,
        state: WorkflowState,
        operation: str
    ) -> bool:
        """
        Determine if operation requires human approval.
        
        Args:
            state: Current workflow state
            operation: Operation being performed
            
        Returns:
            True if approval needed, False otherwise
        """
        critical_operations = [
            "deployment",
            "schema_migration",
            "data_deletion",
            "production_change"
        ]
        
        # Check if operation is critical
        if operation in critical_operations:
            return True
        
        # Check retry limits
        if state.current_task_id:
            retry_count = state.retry_counts.get(state.current_task_id, 0)
            if retry_count >= self.config.max_retries_per_agent:
                return True
        
        return False
    
    def log_error(
        self,
        state: WorkflowState,
        agent: str,
        error_type: str,
        message: str,
        traceback: Optional[str] = None
    ) -> WorkflowState:
        """
        Log error to workflow state.
        
        Args:
            state: Current workflow state
            agent: Agent where error occurred
            error_type: Type of error (transient, recoverable, critical)
            message: Error message
            traceback: Optional stack trace
            
        Returns:
            Updated workflow state
        """
        error = ErrorRecord(
            timestamp=datetime.now(),
            agent=agent,
            task_id=state.current_task_id or "unknown",
            error_type=error_type,
            message=message,
            traceback=traceback,
            retry_count=state.retry_counts.get(agent, 0)
        )
        
        state.error_log.append(error)
        
        # Increment retry count
        if agent not in state.retry_counts:
            state.retry_counts[agent] = 0
        state.retry_counts[agent] += 1
        
        return state
