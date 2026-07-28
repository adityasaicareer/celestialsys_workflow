"""
Error handling infrastructure for the workflow system.

This module provides comprehensive error handling including:
- Error classification (transient, recoverable, critical)
- Exponential backoff calculation
- Retry decision logic with per-agent and global limits
- Centralized error management through ErrorHandler class
- Rollback mechanisms for checkpoint-based recovery

**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import time

from .models import ErrorRecord, WorkflowState


class ErrorType(Enum):
    """Error classification types."""
    TRANSIENT = "transient"  # Network timeouts, rate limits, temporary unavailability
    RECOVERABLE = "recoverable"  # Code errors, test failures, validation issues
    CRITICAL = "critical"  # Docker not running, invalid requirements, system errors


class ErrorClassifier:
    """
    Classifies errors into transient, recoverable, or critical categories.
    
    **Validates: Requirement 11.1**
    """
    
    # Keywords that indicate transient errors
    TRANSIENT_KEYWORDS = [
        "timeout", "timed out", "connection refused", "connection reset",
        "network", "rate limit", "too many requests", "503", "502", "504",
        "temporarily unavailable", "connection pool exhausted",
        "connection error", "dns", "unreachable"
    ]
    
    # Keywords that indicate recoverable errors
    RECOVERABLE_KEYWORDS = [
        "syntax error", "type error", "name error", "attribute error",
        "import error", "test failed", "assertion error", "validation error",
        "linting error", "format error", "mypy", "pylint", "eslint",
        "jest", "pytest", "compilation error", "build failed"
    ]
    
    # Keywords that indicate critical errors
    CRITICAL_KEYWORDS = [
        "docker not found", "docker daemon not running", "docker not installed",
        "insufficient memory", "disk space", "permission denied",
        "invalid requirements", "ambiguous requirements", "contradictory",
        "fatal", "system error", "out of memory", "cannot allocate"
    ]
    
    @classmethod
    def classify_error(cls, error_message: str, error_traceback: Optional[str] = None) -> ErrorType:
        """
        Classify an error based on its message and traceback.
        
        Args:
            error_message: Error message text
            error_traceback: Optional error traceback
            
        Returns:
            ErrorType classification (TRANSIENT, RECOVERABLE, or CRITICAL)
        """
        # Combine message and traceback for analysis
        full_text = error_message.lower()
        if error_traceback:
            full_text += " " + error_traceback.lower()
        
        # Check for critical errors first (highest priority)
        if any(keyword in full_text for keyword in cls.CRITICAL_KEYWORDS):
            return ErrorType.CRITICAL
        
        # Check for transient errors
        if any(keyword in full_text for keyword in cls.TRANSIENT_KEYWORDS):
            return ErrorType.TRANSIENT
        
        # Check for recoverable errors
        if any(keyword in full_text for keyword in cls.RECOVERABLE_KEYWORDS):
            return ErrorType.RECOVERABLE
        
        # Default to recoverable for unknown errors
        return ErrorType.RECOVERABLE


def calculate_exponential_backoff(retry_count: int) -> float:
    """
    Calculate exponential backoff wait time with cap at 16 seconds.
    
    Formula: min(2^n, 16) seconds where n is the retry count.
    
    Args:
        retry_count: Number of retries attempted (0-indexed)
        
    Returns:
        Wait time in seconds (capped at 16 seconds)
        
    **Validates: Requirement 11.2**
    
    Examples:
        >>> calculate_exponential_backoff(0)
        1.0
        >>> calculate_exponential_backoff(1)
        2.0
        >>> calculate_exponential_backoff(4)
        16.0
        >>> calculate_exponential_backoff(10)
        16.0
    """
    return min(2 ** retry_count, 16.0)


class RetryDecision:
    """
    Determines whether a retry should be attempted based on error type and retry counts.
    
    **Validates: Requirements 11.2, 11.3**
    """
    
    # Maximum retries per agent
    MAX_AGENT_RETRIES = 5
    
    # Maximum retries across all agents in workflow
    MAX_GLOBAL_RETRIES = 20
    
    @classmethod
    def should_retry(
        cls,
        error: ErrorRecord,
        state: WorkflowState
    ) -> bool:
        """
        Determine if a retry should be attempted for the given error.
        
        Args:
            error: Error record containing error details
            state: Current workflow state with retry counts
            
        Returns:
            True if retry should be attempted, False otherwise
            
        **Validates: Requirements 11.2, 11.3**
        """
        # Check agent-specific retry limit
        agent_retries = state.retry_counts.get(error.agent, 0)
        if agent_retries >= cls.MAX_AGENT_RETRIES:
            return False
        
        # Check global retry limit
        total_retries = sum(state.retry_counts.values())
        if total_retries >= cls.MAX_GLOBAL_RETRIES:
            return False
        
        # Never retry critical errors automatically
        if error.error_type == ErrorType.CRITICAL.value:
            return False
        
        # Retry transient and recoverable errors within limits
        return True
    
    @classmethod
    def get_backoff_time(cls, error: ErrorRecord) -> float:
        """
        Get the backoff time for the given error.
        
        Args:
            error: Error record with retry count
            
        Returns:
            Backoff time in seconds
        """
        return calculate_exponential_backoff(error.retry_count)


class ErrorHandler:
    """
    Centralized error management for the workflow system.
    
    Provides error classification, retry logic, rollback mechanisms,
    and comprehensive error logging.
    
    **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**
    """
    
    def __init__(self):
        """Initialize the error handler."""
        self.classifier = ErrorClassifier()
        self.retry_decision = RetryDecision()
    
    def handle_error(
        self,
        agent: str,
        task_id: str,
        error_message: str,
        error_traceback: Optional[str],
        state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Handle an error by classifying it, logging it, and determining next action.
        
        Args:
            agent: Name of the agent that encountered the error
            task_id: Task ID where error occurred
            error_message: Error message
            error_traceback: Optional error traceback
            state: Current workflow state
            
        Returns:
            Dictionary with handling decision:
            {
                "action": "retry" | "request_approval" | "fail",
                "error_type": "transient" | "recoverable" | "critical",
                "backoff_time": float (seconds to wait before retry),
                "error_record": ErrorRecord
            }
            
        **Validates: Requirements 11.1, 11.2, 11.3, 11.4**
        """
        # Classify the error
        error_type = self.classifier.classify_error(error_message, error_traceback)
        
        # Get current retry count for this agent
        current_retry_count = state.retry_counts.get(agent, 0)
        
        # Create error record
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            agent=agent,
            task_id=task_id,
            error_type=error_type.value,
            message=error_message,
            traceback=error_traceback,
            retry_count=current_retry_count
        )
        
        # Log the error
        state.error_log.append(error_record)
        
        # Increment retry counter
        state.retry_counts[agent] = current_retry_count + 1
        
        # Determine action based on retry decision
        should_retry = self.retry_decision.should_retry(error_record, state)
        
        if error_type == ErrorType.CRITICAL:
            # Critical errors always require approval
            return {
                "action": "request_approval",
                "error_type": error_type.value,
                "backoff_time": 0.0,
                "error_record": error_record,
                "reason": "Critical error requires human intervention"
            }
        
        if not should_retry:
            # Max retries exceeded, request approval
            return {
                "action": "request_approval",
                "error_type": error_type.value,
                "backoff_time": 0.0,
                "error_record": error_record,
                "reason": f"Max retries exceeded (agent: {current_retry_count + 1}/{RetryDecision.MAX_AGENT_RETRIES}, global: {sum(state.retry_counts.values())}/{RetryDecision.MAX_GLOBAL_RETRIES})"
            }
        
        # Calculate backoff time for retry
        backoff_time = self.retry_decision.get_backoff_time(error_record)
        
        return {
            "action": "retry",
            "error_type": error_type.value,
            "backoff_time": backoff_time,
            "error_record": error_record,
            "reason": f"Retrying after {backoff_time}s (attempt {current_retry_count + 1}/{RetryDecision.MAX_AGENT_RETRIES})"
        }
    
    def apply_backoff(self, backoff_time: float) -> None:
        """
        Apply exponential backoff by sleeping for the specified time.
        
        Args:
            backoff_time: Time to wait in seconds
        """
        if backoff_time > 0:
            time.sleep(backoff_time)
    
    def get_error_summary(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Get a summary of all errors in the workflow.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dictionary with error statistics and details
            
        **Validates: Requirement 11.4**
        """
        if not state.error_log:
            return {
                "total_errors": 0,
                "by_type": {},
                "by_agent": {},
                "recent_errors": []
            }
        
        # Count errors by type
        by_type: Dict[str, int] = {}
        for error in state.error_log:
            by_type[error.error_type] = by_type.get(error.error_type, 0) + 1
        
        # Count errors by agent
        by_agent: Dict[str, int] = {}
        for error in state.error_log:
            by_agent[error.agent] = by_agent.get(error.agent, 0) + 1
        
        # Get most recent errors (last 5)
        recent_errors = [
            {
                "timestamp": error.timestamp.isoformat(),
                "agent": error.agent,
                "task_id": error.task_id,
                "type": error.error_type,
                "message": error.message[:200]  # Truncate long messages
            }
            for error in state.error_log[-5:]
        ]
        
        return {
            "total_errors": len(state.error_log),
            "by_type": by_type,
            "by_agent": by_agent,
            "retry_counts": dict(state.retry_counts),
            "recent_errors": recent_errors
        }


class CheckpointRollback:
    """
    Handles rollback to previous checkpoints for recovery.
    
    **Validates: Requirement 11.5**
    """
    
    @staticmethod
    def prepare_rollback(
        state: WorkflowState,
        target_task_id: Optional[str] = None
    ) -> WorkflowState:
        """
        Prepare workflow state for rollback to a previous checkpoint.
        
        This method creates a new state that reverts to a previous point,
        clearing state changes after the rollback point.
        
        Args:
            state: Current workflow state
            target_task_id: Task ID to rollback to (if None, rollback to last completed task)
            
        Returns:
            New WorkflowState rolled back to the target checkpoint
            
        **Validates: Requirement 11.5**
        """
        # If no target specified, rollback to last completed task
        if target_task_id is None:
            if not state.completed_task_ids:
                # No completed tasks, return initial state
                return state
            target_task_id = state.completed_task_ids[-1]
        
        # Find the index of target task in completed list
        try:
            rollback_index = state.completed_task_ids.index(target_task_id)
        except ValueError:
            # Target task not found, return current state
            return state
        
        # Create new state with rolled back data
        rolled_back_state = state.model_copy(deep=True)
        
        # Keep only completed tasks up to rollback point
        rolled_back_state.completed_task_ids = state.completed_task_ids[:rollback_index + 1]
        
        # Reset current task to None (will be determined by supervisor)
        rolled_back_state.current_task_id = None
        
        # Clear retry counts for tasks after rollback point
        # Keep retry counts for tasks before rollback point
        
        # Update workflow status
        rolled_back_state.workflow_status = "running"
        rolled_back_state.requires_approval = False
        rolled_back_state.approval_message = None
        
        # Add rollback transition to agent transitions
        rolled_back_state.agent_transitions.append({
            "from": state.current_task_id or "unknown",
            "to": target_task_id,
            "action": "rollback",
            "timestamp": datetime.now().isoformat(),
            "reason": "Rollback to previous checkpoint"
        })
        
        rolled_back_state.updated_at = datetime.now()
        
        return rolled_back_state
    
    @staticmethod
    def can_rollback(state: WorkflowState) -> bool:
        """
        Check if rollback is possible for the current state.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if rollback is possible, False otherwise
        """
        # Rollback is possible if there are completed tasks
        return len(state.completed_task_ids) > 0
    
    @staticmethod
    def get_rollback_points(state: WorkflowState) -> List[str]:
        """
        Get available rollback points (completed task IDs).
        
        Args:
            state: Current workflow state
            
        Returns:
            List of task IDs that can be rolled back to
        """
        return state.completed_task_ids.copy()


# Convenience function for common error handling pattern
def handle_agent_error(
    error_handler: ErrorHandler,
    agent: str,
    task_id: str,
    exception: Exception,
    state: WorkflowState
) -> Dict[str, Any]:
    """
    Convenience function to handle agent errors with standard pattern.
    
    Args:
        error_handler: ErrorHandler instance
        agent: Agent name
        task_id: Task ID
        exception: Exception that occurred
        state: Workflow state
        
    Returns:
        Error handling decision dictionary
    """
    import traceback
    
    error_message = str(exception)
    error_traceback = traceback.format_exc()
    
    return error_handler.handle_error(
        agent=agent,
        task_id=task_id,
        error_message=error_message,
        error_traceback=error_traceback,
        state=state
    )
