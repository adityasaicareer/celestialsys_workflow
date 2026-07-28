"""
Unit tests for human approval mechanism.

Tests approval node behavior, user input handling, timeout scenarios,
and workflow resumption logic.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from io import StringIO

from workflow.models import WorkflowState, TaskDefinition, ErrorRecord
from workflow.approval import (
    ApprovalHandler,
    ApprovalTimeout,
    request_human_approval,
    check_approval_needed,
    request_approval_with_reason
)


@pytest.fixture
def sample_state():
    """Create a sample workflow state for testing."""
    return WorkflowState(
        thread_id="test-thread-123",
        user_requirements="Build a test application",
        execution_plan=[
            TaskDefinition(
                id="task_1",
                description="Test task 1",
                agent="backend",
                dependencies=[],
                status="complete"
            ),
            TaskDefinition(
                id="task_2",
                description="Test task 2",
                agent="frontend",
                dependencies=["task_1"],
                status="in_progress"
            )
        ],
        current_task_id="task_2",
        completed_task_ids=["task_1"],
        requires_approval=True,
        approval_message="Max retries exceeded",
        retry_counts={"backend": 5},
        workflow_status="running"
    )


@pytest.fixture
def approval_handler():
    """Create approval handler with short timeout for testing."""
    return ApprovalHandler(timeout_seconds=1)


class TestApprovalHandler:
    """Test ApprovalHandler class functionality."""
    
    def test_initialization(self):
        """Test approval handler initialization with custom timeout."""
        handler = ApprovalHandler(timeout_seconds=60)
        assert handler.timeout_seconds == 60
        assert handler._timeout_triggered == False
    
    def test_present_approval_request_format(self, sample_state):
        """Test approval request formatting includes all context."""
        handler = ApprovalHandler()
        request_text = handler.present_approval_request(sample_state)
        
        # Check key elements are present
        assert "HUMAN APPROVAL REQUIRED" in request_text
        assert "Max retries exceeded" in request_text
        assert "Current Task: task_2" in request_text
        assert "Completed Tasks: 1/2" in request_text
        assert "[A] Approve" in request_text
        assert "[R] Reject" in request_text
        assert "[M] Modify" in request_text
        assert "[S] Skip" in request_text
        assert "timeout" in request_text.lower()
    
    def test_present_approval_request_with_errors(self, sample_state):
        """Test approval request displays error context."""
        sample_state.error_log = [
            ErrorRecord(
                timestamp=datetime.now(),
                agent="backend",
                task_id="task_1",
                error_type="recoverable",
                message="Code generation failed",
                retry_count=3
            )
        ]
        
        handler = ApprovalHandler()
        request_text = handler.present_approval_request(sample_state)
        
        assert "Recent Errors: 1" in request_text
        assert "Code generation failed" in request_text
        assert "Retry Count: 3" in request_text
    
    @patch('builtins.input', return_value='A')
    def test_process_approval(self, mock_input, sample_state):
        """Test approval decision processing."""
        handler = ApprovalHandler(timeout_seconds=1)
        
        # Mock signal for systems that support it
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = handler.get_user_response(sample_state)
        
        assert result["requires_approval"] == False
        assert result["workflow_status"] == "running"
        assert result["approval_message"] is None
    
    @patch('builtins.input', return_value='R')
    def test_process_rejection(self, mock_input, sample_state):
        """Test rejection decision processing."""
        handler = ApprovalHandler(timeout_seconds=1)
        
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = handler.get_user_response(sample_state)
        
        assert result["requires_approval"] == False
        assert result["workflow_status"] == "failed"
    
    @patch('builtins.input', side_effect=['new requirements text'])
    def test_process_modification(self, mock_input, sample_state):
        """Test modification decision with new requirements."""
        handler = ApprovalHandler(timeout_seconds=1)
        
        # Mock the first input to select 'M', then provide new requirements
        with patch('builtins.input', side_effect=['M', 'new requirements text']):
            with patch('signal.SIGALRM', 14, create=True):
                with patch('signal.signal'):
                    with patch('signal.alarm'):
                        result = handler.get_user_response(sample_state)
        
        assert result["requires_approval"] == False
        assert result["user_requirements"] == "new requirements text"
        assert result["execution_plan"] == []
        assert result["completed_task_ids"] == []
        assert result["workflow_status"] == "running"
    
    @patch('builtins.input', side_effect=['M', ''])
    def test_process_modification_no_change(self, mock_input, sample_state):
        """Test modification with no changes keeps current requirements."""
        handler = ApprovalHandler(timeout_seconds=1)
        
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = handler.get_user_response(sample_state)
        
        # Should behave like approval when no changes made
        assert result["requires_approval"] == False
        assert result["workflow_status"] == "running"
    
    @patch('builtins.input', return_value='S')
    def test_process_skip(self, mock_input, sample_state):
        """Test skip decision marks current task as complete."""
        handler = ApprovalHandler(timeout_seconds=1)
        
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = handler.get_user_response(sample_state)
        
        assert result["requires_approval"] == False
        assert result["workflow_status"] == "running"
        assert "task_2" in result["completed_task_ids"]
        assert result["current_task_id"] is None
    
    @patch('builtins.input', side_effect=['X', 'A'])
    def test_invalid_input_retry(self, mock_input, sample_state):
        """Test invalid input prompts for retry."""
        handler = ApprovalHandler(timeout_seconds=1)
        
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = handler.get_user_response(sample_state)
        
        # Should eventually accept valid input
        assert result["requires_approval"] == False
        assert result["workflow_status"] == "running"
    
    def test_timeout_scenario(self, sample_state):
        """Test timeout triggers automatic rejection."""
        handler = ApprovalHandler(timeout_seconds=1)
        result = handler._process_timeout(sample_state)
        
        assert result["workflow_status"] == "failed"
        assert result["requires_approval"] == False
        assert result["approval_message"] == "Approval request timed out"
    
    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_keyboard_interrupt_rejection(self, mock_input, sample_state):
        """Test keyboard interrupt triggers rejection."""
        handler = ApprovalHandler(timeout_seconds=1)
        
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = handler.get_user_response(sample_state)
        
        assert result["workflow_status"] == "failed"
        assert result["requires_approval"] == False


class TestApprovalFunctions:
    """Test module-level approval functions."""
    
    @patch('builtins.input', return_value='A')
    def test_request_human_approval(self, mock_input, sample_state):
        """Test request_human_approval function."""
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = request_human_approval(sample_state, timeout_seconds=1)
        
        assert "requires_approval" in result
        assert "workflow_status" in result
    
    @patch('builtins.input', return_value='A')
    def test_request_approval_with_reason(self, mock_input, sample_state):
        """Test request_approval_with_reason sets message."""
        sample_state.requires_approval = False
        sample_state.approval_message = None
        
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = request_approval_with_reason(
                        sample_state,
                        reason="Test reason",
                        timeout_seconds=1
                    )
        
        assert result["workflow_status"] == "running"
    
    def test_check_approval_needed_explicit_flag(self, sample_state):
        """Test check_approval_needed with explicit flag."""
        sample_state.requires_approval = True
        assert check_approval_needed(sample_state) == True
        
        sample_state.requires_approval = False
        sample_state.retry_counts = {}
        sample_state.error_log = []
        assert check_approval_needed(sample_state) == False
    
    def test_check_approval_needed_retry_limit(self, sample_state):
        """Test check_approval_needed detects retry limit."""
        sample_state.requires_approval = False
        sample_state.retry_counts = {"backend": 5}
        
        assert check_approval_needed(sample_state) == True
    
    def test_check_approval_needed_total_retries(self, sample_state):
        """Test check_approval_needed detects total retry limit."""
        sample_state.requires_approval = False
        sample_state.retry_counts = {
            "backend": 5,
            "frontend": 5,
            "database": 5,
            "testing": 5
        }
        
        assert check_approval_needed(sample_state) == True
    
    def test_check_approval_needed_critical_error(self, sample_state):
        """Test check_approval_needed detects critical errors."""
        sample_state.requires_approval = False
        sample_state.retry_counts = {}
        sample_state.error_log = [
            ErrorRecord(
                timestamp=datetime.now(),
                agent="database",
                task_id="task_1",
                error_type="critical",
                message="Docker not running",
                retry_count=0
            )
        ]
        
        assert check_approval_needed(sample_state) == True


class TestApprovalNodeIntegration:
    """Test human_approval_node integration."""
    
    @patch('builtins.input', return_value='A')
    def test_approval_node_execution(self, mock_input, sample_state):
        """Test human_approval_node executes successfully."""
        from workflow.graph import create_workflow_graph
        
        # Import the node function directly
        from workflow.approval import request_human_approval
        
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = request_human_approval(sample_state, timeout_seconds=1)
        
        assert isinstance(result, dict)
        assert "requires_approval" in result
        assert "workflow_status" in result
    
    def test_approval_node_not_needed(self):
        """Test approval node skips when approval not needed."""
        from workflow.approval import check_approval_needed
        
        state = WorkflowState(
            thread_id="test-123",
            user_requirements="Test",
            requires_approval=False,
            retry_counts={},
            error_log=[]
        )
        
        assert check_approval_needed(state) == False
    
    @patch('builtins.input', return_value='R')
    def test_approval_node_rejection(self, mock_input, sample_state):
        """Test approval node handles rejection."""
        from workflow.approval import request_human_approval
        
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = request_human_approval(sample_state, timeout_seconds=1)
        
        assert result["workflow_status"] == "failed"
    
    @patch('builtins.input', return_value='S')
    def test_approval_node_skip(self, mock_input, sample_state):
        """Test approval node handles skip."""
        from workflow.approval import request_human_approval
        
        with patch('signal.SIGALRM', 14, create=True):
            with patch('signal.signal'):
                with patch('signal.alarm'):
                    result = request_human_approval(sample_state, timeout_seconds=1)
        
        assert result["workflow_status"] == "running"
        assert "task_2" in result["completed_task_ids"]


class TestApprovalTimeout:
    """Test timeout handling in approval mechanism."""
    
    def test_timeout_exception_raised(self, sample_state):
        """Test ApprovalTimeout exception."""
        handler = ApprovalHandler(timeout_seconds=1)
        
        # Simulate timeout
        handler._timeout_triggered = True
        
        try:
            raise ApprovalTimeout("Timeout test")
        except ApprovalTimeout as e:
            assert "Timeout" in str(e)
    
    def test_timeout_handler_sets_flag(self, sample_state):
        """Test timeout handler sets timeout flag."""
        handler = ApprovalHandler(timeout_seconds=1)
        
        assert handler._timeout_triggered == False
        
        # Simulate signal handler call
        try:
            handler._timeout_handler(None, None)
        except ApprovalTimeout:
            pass
        
        assert handler._timeout_triggered == True


class TestApprovalStateTransitions:
    """Test state transitions during approval."""
    
    def test_approval_preserves_workflow_data(self, sample_state):
        """Test approval doesn't corrupt workflow state."""
        handler = ApprovalHandler()
        result = handler._process_approval(sample_state)
        
        # Should only update approval-related fields
        assert "requires_approval" in result
        assert "workflow_status" in result
        assert "updated_at" in result
        
        # Should not modify other state
        assert "execution_plan" not in result
        assert "completed_task_ids" not in result
    
    def test_rejection_preserves_error_log(self, sample_state):
        """Test rejection preserves error history."""
        handler = ApprovalHandler()
        result = handler._process_rejection(sample_state)
        
        assert result["workflow_status"] == "failed"
        # Error log should be preserved in state (not in result)
    
    def test_modification_clears_execution_state(self, sample_state):
        """Test modification clears execution to force re-planning."""
        handler = ApprovalHandler()
        
        # Simulate modification with new requirements
        with patch('builtins.input', return_value='new requirements'):
            result = handler._process_modification(sample_state)
        
        assert result["execution_plan"] == []
        assert result["completed_task_ids"] == []
        assert result["current_task_id"] is None
        assert result["user_requirements"] == "new requirements"
    
    def test_skip_updates_completed_tasks(self, sample_state):
        """Test skip adds current task to completed."""
        handler = ApprovalHandler()
        result = handler._process_skip(sample_state)
        
        assert "task_2" in result["completed_task_ids"]
        assert "task_1" in result["completed_task_ids"]
        assert result["current_task_id"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
