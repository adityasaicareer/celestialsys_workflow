"""
Unit tests for error handling infrastructure.

Tests error classification, exponential backoff, retry logic,
and rollback mechanisms.
"""

import pytest
from datetime import datetime

from workflow.error_handling import (
    ErrorClassifier,
    ErrorType,
    calculate_exponential_backoff,
    RetryDecision,
    ErrorHandler,
    CheckpointRollback,
    handle_agent_error
)
from workflow.models import ErrorRecord, WorkflowState, TaskDefinition


class TestErrorClassifier:
    """Test error classification logic."""
    
    def test_classify_transient_network_timeout(self):
        """Test that network timeouts are classified as transient."""
        message = "Connection timeout after 30 seconds"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.TRANSIENT
    
    def test_classify_transient_rate_limit(self):
        """Test that rate limiting is classified as transient."""
        message = "Rate limit exceeded, too many requests"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.TRANSIENT
    
    def test_classify_transient_connection_refused(self):
        """Test that connection refused is classified as transient."""
        message = "Connection refused by server"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.TRANSIENT
    
    def test_classify_recoverable_syntax_error(self):
        """Test that syntax errors are classified as recoverable."""
        message = "SyntaxError: invalid syntax at line 42"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.RECOVERABLE
    
    def test_classify_recoverable_type_error(self):
        """Test that type errors are classified as recoverable."""
        message = "TypeError: expected str, got int"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.RECOVERABLE
    
    def test_classify_recoverable_test_failure(self):
        """Test that test failures are classified as recoverable."""
        message = "Test failed: assertion error in test_user_login"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.RECOVERABLE
    
    def test_classify_recoverable_linting_error(self):
        """Test that linting errors are classified as recoverable."""
        message = "pylint error: line too long (120 > 100)"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.RECOVERABLE
    
    def test_classify_critical_docker_not_running(self):
        """Test that Docker not running is classified as critical."""
        message = "Docker daemon not running"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.CRITICAL
    
    def test_classify_critical_insufficient_memory(self):
        """Test that memory errors are classified as critical."""
        message = "Fatal: insufficient memory to continue"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.CRITICAL
    
    def test_classify_critical_invalid_requirements(self):
        """Test that invalid requirements are classified as critical."""
        message = "Invalid requirements: contradictory specifications detected"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.CRITICAL
    
    def test_classify_with_traceback(self):
        """Test classification with both message and traceback."""
        message = "Something went wrong"
        traceback = "File 'test.py', line 10\n    SyntaxError: invalid syntax"
        result = ErrorClassifier.classify_error(message, traceback)
        assert result == ErrorType.RECOVERABLE
    
    def test_classify_unknown_defaults_to_recoverable(self):
        """Test that unknown errors default to recoverable."""
        message = "Some unknown error occurred"
        result = ErrorClassifier.classify_error(message)
        assert result == ErrorType.RECOVERABLE


class TestExponentialBackoff:
    """Test exponential backoff calculation."""
    
    def test_backoff_retry_0(self):
        """Test backoff for first retry (2^0 = 1)."""
        result = calculate_exponential_backoff(0)
        assert result == 1.0
    
    def test_backoff_retry_1(self):
        """Test backoff for second retry (2^1 = 2)."""
        result = calculate_exponential_backoff(1)
        assert result == 2.0
    
    def test_backoff_retry_2(self):
        """Test backoff for third retry (2^2 = 4)."""
        result = calculate_exponential_backoff(2)
        assert result == 4.0
    
    def test_backoff_retry_3(self):
        """Test backoff for fourth retry (2^3 = 8)."""
        result = calculate_exponential_backoff(3)
        assert result == 8.0
    
    def test_backoff_retry_4(self):
        """Test backoff for fifth retry (2^4 = 16, at cap)."""
        result = calculate_exponential_backoff(4)
        assert result == 16.0
    
    def test_backoff_capped_at_16(self):
        """Test that backoff is capped at 16 seconds."""
        # Test various high retry counts
        assert calculate_exponential_backoff(5) == 16.0
        assert calculate_exponential_backoff(10) == 16.0
        assert calculate_exponential_backoff(100) == 16.0


class TestRetryDecision:
    """Test retry decision logic."""
    
    def test_should_retry_within_limits(self):
        """Test that retry is allowed within agent and global limits."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={"backend": 2}  # 2 retries, below limit of 5
        )
        error = ErrorRecord(
            timestamp=datetime.now(),
            agent="backend",
            task_id="task_1",
            error_type=ErrorType.RECOVERABLE.value,
            message="Test error",
            retry_count=2
        )
        
        result = RetryDecision.should_retry(error, state)
        assert result is True
    
    def test_should_not_retry_at_agent_limit(self):
        """Test that retry is blocked at agent limit (5 retries)."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={"backend": 5}  # At limit
        )
        error = ErrorRecord(
            timestamp=datetime.now(),
            agent="backend",
            task_id="task_1",
            error_type=ErrorType.RECOVERABLE.value,
            message="Test error",
            retry_count=5
        )
        
        result = RetryDecision.should_retry(error, state)
        assert result is False
    
    def test_should_not_retry_at_global_limit(self):
        """Test that retry is blocked at global limit (20 retries)."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={
                "backend": 5,
                "frontend": 5,
                "database": 5,
                "testing": 5  # Total: 20
            }
        )
        error = ErrorRecord(
            timestamp=datetime.now(),
            agent="deployment",
            task_id="task_1",
            error_type=ErrorType.RECOVERABLE.value,
            message="Test error",
            retry_count=0
        )
        
        result = RetryDecision.should_retry(error, state)
        assert result is False
    
    def test_should_not_retry_critical_errors(self):
        """Test that critical errors are never retried."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={}
        )
        error = ErrorRecord(
            timestamp=datetime.now(),
            agent="backend",
            task_id="task_1",
            error_type=ErrorType.CRITICAL.value,
            message="Docker not running",
            retry_count=0
        )
        
        result = RetryDecision.should_retry(error, state)
        assert result is False
    
    def test_get_backoff_time(self):
        """Test that backoff time is calculated correctly."""
        error = ErrorRecord(
            timestamp=datetime.now(),
            agent="backend",
            task_id="task_1",
            error_type=ErrorType.TRANSIENT.value,
            message="Network timeout",
            retry_count=3
        )
        
        result = RetryDecision.get_backoff_time(error)
        assert result == 8.0  # 2^3 = 8


class TestErrorHandler:
    """Test ErrorHandler class."""
    
    def test_handle_transient_error_with_retry(self):
        """Test handling transient error results in retry."""
        handler = ErrorHandler()
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={}
        )
        
        result = handler.handle_error(
            agent="backend",
            task_id="task_1",
            error_message="Connection timeout",
            error_traceback=None,
            state=state
        )
        
        assert result["action"] == "retry"
        assert result["error_type"] == ErrorType.TRANSIENT.value
        assert result["backoff_time"] == 1.0  # First retry
        assert len(state.error_log) == 1
        assert state.retry_counts["backend"] == 1
    
    def test_handle_recoverable_error_with_retry(self):
        """Test handling recoverable error results in retry."""
        handler = ErrorHandler()
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={"backend": 1}
        )
        
        result = handler.handle_error(
            agent="backend",
            task_id="task_1",
            error_message="SyntaxError: invalid syntax",
            error_traceback="File 'test.py', line 10",
            state=state
        )
        
        assert result["action"] == "retry"
        assert result["error_type"] == ErrorType.RECOVERABLE.value
        assert result["backoff_time"] == 2.0  # Second retry (2^1)
        assert state.retry_counts["backend"] == 2
    
    def test_handle_critical_error_requests_approval(self):
        """Test handling critical error requests approval."""
        handler = ErrorHandler()
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={}
        )
        
        result = handler.handle_error(
            agent="backend",
            task_id="task_1",
            error_message="Docker daemon not running",
            error_traceback=None,
            state=state
        )
        
        assert result["action"] == "request_approval"
        assert result["error_type"] == ErrorType.CRITICAL.value
        assert result["backoff_time"] == 0.0
        assert "Critical error" in result["reason"]
    
    def test_handle_max_agent_retries_requests_approval(self):
        """Test that max agent retries triggers approval request."""
        handler = ErrorHandler()
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={"backend": 4}  # Next retry would be 5th
        )
        
        result = handler.handle_error(
            agent="backend",
            task_id="task_1",
            error_message="Test failed",
            error_traceback=None,
            state=state
        )
        
        assert result["action"] == "request_approval"
        assert "Max retries exceeded" in result["reason"]
        assert state.retry_counts["backend"] == 5
    
    def test_handle_max_global_retries_requests_approval(self):
        """Test that max global retries triggers approval request."""
        handler = ErrorHandler()
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={
                "backend": 5,
                "frontend": 5,
                "database": 5,
                "testing": 4  # Total: 19, next would be 20
            }
        )
        
        result = handler.handle_error(
            agent="testing",
            task_id="task_1",
            error_message="Test failed",
            error_traceback=None,
            state=state
        )
        
        assert result["action"] == "request_approval"
        assert "Max retries exceeded" in result["reason"]
    
    def test_get_error_summary_empty(self):
        """Test error summary with no errors."""
        handler = ErrorHandler()
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            error_log=[]
        )
        
        summary = handler.get_error_summary(state)
        
        assert summary["total_errors"] == 0
        assert summary["by_type"] == {}
        assert summary["by_agent"] == {}
        assert summary["recent_errors"] == []
    
    def test_get_error_summary_with_errors(self):
        """Test error summary with multiple errors."""
        handler = ErrorHandler()
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={"backend": 2, "frontend": 1},
            error_log=[
                ErrorRecord(
                    timestamp=datetime.now(),
                    agent="backend",
                    task_id="task_1",
                    error_type=ErrorType.RECOVERABLE.value,
                    message="Error 1",
                    retry_count=0
                ),
                ErrorRecord(
                    timestamp=datetime.now(),
                    agent="backend",
                    task_id="task_1",
                    error_type=ErrorType.RECOVERABLE.value,
                    message="Error 2",
                    retry_count=1
                ),
                ErrorRecord(
                    timestamp=datetime.now(),
                    agent="frontend",
                    task_id="task_2",
                    error_type=ErrorType.TRANSIENT.value,
                    message="Error 3",
                    retry_count=0
                ),
            ]
        )
        
        summary = handler.get_error_summary(state)
        
        assert summary["total_errors"] == 3
        assert summary["by_type"][ErrorType.RECOVERABLE.value] == 2
        assert summary["by_type"][ErrorType.TRANSIENT.value] == 1
        assert summary["by_agent"]["backend"] == 2
        assert summary["by_agent"]["frontend"] == 1
        assert summary["retry_counts"]["backend"] == 2
        assert summary["retry_counts"]["frontend"] == 1
        assert len(summary["recent_errors"]) == 3


class TestCheckpointRollback:
    """Test checkpoint-based rollback mechanism."""
    
    def test_can_rollback_with_completed_tasks(self):
        """Test that rollback is possible with completed tasks."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            completed_task_ids=["task_1", "task_2"]
        )
        
        result = CheckpointRollback.can_rollback(state)
        assert result is True
    
    def test_cannot_rollback_without_completed_tasks(self):
        """Test that rollback is not possible without completed tasks."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            completed_task_ids=[]
        )
        
        result = CheckpointRollback.can_rollback(state)
        assert result is False
    
    def test_get_rollback_points(self):
        """Test getting available rollback points."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            completed_task_ids=["task_1", "task_2", "task_3"]
        )
        
        result = CheckpointRollback.get_rollback_points(state)
        assert result == ["task_1", "task_2", "task_3"]
    
    def test_prepare_rollback_to_specific_task(self):
        """Test rollback to a specific task."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            current_task_id="task_4",
            completed_task_ids=["task_1", "task_2", "task_3"],
            workflow_status="running"
        )
        
        rolled_back = CheckpointRollback.prepare_rollback(state, "task_2")
        
        assert rolled_back.completed_task_ids == ["task_1", "task_2"]
        assert rolled_back.current_task_id is None
        assert rolled_back.workflow_status == "running"
        assert rolled_back.requires_approval is False
        assert len(rolled_back.agent_transitions) == 1
        assert rolled_back.agent_transitions[0]["action"] == "rollback"
    
    def test_prepare_rollback_to_last_task(self):
        """Test rollback to last completed task (no target specified)."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            current_task_id="task_4",
            completed_task_ids=["task_1", "task_2", "task_3"]
        )
        
        rolled_back = CheckpointRollback.prepare_rollback(state, None)
        
        # Should rollback to task_3 (last completed)
        assert rolled_back.completed_task_ids == ["task_1", "task_2", "task_3"]
    
    def test_prepare_rollback_with_no_completed_tasks(self):
        """Test rollback with no completed tasks returns original state."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            completed_task_ids=[]
        )
        
        rolled_back = CheckpointRollback.prepare_rollback(state, None)
        
        # Should return original state unchanged
        assert rolled_back == state
    
    def test_prepare_rollback_invalid_task(self):
        """Test rollback with invalid task ID returns original state."""
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            completed_task_ids=["task_1", "task_2"]
        )
        
        rolled_back = CheckpointRollback.prepare_rollback(state, "invalid_task")
        
        # Should return original state unchanged
        assert rolled_back == state


class TestHandleAgentError:
    """Test convenience function for agent error handling."""
    
    def test_handle_agent_error_with_exception(self):
        """Test handling agent error with Python exception."""
        handler = ErrorHandler()
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test requirements",
            retry_counts={}
        )
        
        try:
            # Trigger a real exception
            raise ValueError("Invalid value provided")
        except Exception as e:
            result = handle_agent_error(
                error_handler=handler,
                agent="backend",
                task_id="task_1",
                exception=e,
                state=state
            )
        
        assert result["action"] == "retry"
        assert "Invalid value provided" in result["error_record"].message
        assert result["error_record"].traceback is not None
        assert len(state.error_log) == 1
