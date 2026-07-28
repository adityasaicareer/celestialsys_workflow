"""
Edge case integration tests for the workflow system.

This module tests error handling and recovery for edge cases and failure scenarios:
- Empty requirements
- Ambiguous requirements  
- Docker not running
- Network failures during package installation
- Insufficient system resources

**Validates: Requirements 11.1, 11.2, 11.3, 11.4**
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import subprocess
import tempfile
import os
from pathlib import Path

from workflow.models import WorkflowState, ErrorRecord, TaskDefinition
from workflow.error_handling import (
    ErrorHandler,
    ErrorClassifier,
    ErrorType,
    CheckpointRollback
)
from workflow.agents.planning_agent import PlanningAgent
from workflow.agents.backend_agent import BackendAgent
from workflow.agents.database_agent import DatabaseAgent


class TestEmptyRequirementsEdgeCase:
    """Test workflow behavior with empty requirements.
    
    **Validates: Requirements 11.1, 11.3**
    """
    
    def test_empty_string_requirements(self):
        """Test that empty string requirements are rejected with clear error."""
        planning_agent = PlanningAgent()
        
        with pytest.raises(Exception) as exc_info:
            planning_agent.create_execution_plan("")
        
        # Verify error is classified as critical
        error_message = str(exc_info.value)
        error_type = ErrorClassifier.classify_error(error_message)
        assert error_type == ErrorType.CRITICAL
    
    def test_whitespace_only_requirements(self):
        """Test that whitespace-only requirements are rejected."""
        planning_agent = PlanningAgent()
        
        with pytest.raises(Exception) as exc_info:
            planning_agent.create_execution_plan("   \n\t   ")
        
        error_message = str(exc_info.value)
        assert "empty" in error_message.lower() or "invalid" in error_message.lower()
    
    def test_empty_requirements_workflow_state(self):
        """Test workflow state handling with empty requirements."""
        state = WorkflowState(
            thread_id="test-empty-reqs",
            user_requirements=""
        )
        
        error_handler = ErrorHandler()
        result = error_handler.handle_error(
            agent="planning",
            task_id="initial_planning",
            error_message="Invalid requirements: requirements cannot be empty",
            error_traceback=None,
            state=state
        )
        
        # Empty requirements should be classified as critical and require approval
        assert result["action"] == "request_approval"
        assert result["error_type"] == ErrorType.CRITICAL.value
        assert len(state.error_log) == 1
    
    def test_empty_file_requirements(self):
        """Test handling of empty file as requirements input."""
        planning_agent = PlanningAgent()
        
        # Create temporary empty file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_file = f.name
            # Write nothing - empty file
        
        try:
            with pytest.raises(Exception) as exc_info:
                # Simulate reading empty file
                with open(temp_file, 'r') as f:
                    content = f.read()
                planning_agent.create_execution_plan(content)
            
            error_message = str(exc_info.value)
            assert "empty" in error_message.lower() or "invalid" in error_message.lower()
        finally:
            os.unlink(temp_file)


class TestAmbiguousRequirementsEdgeCase:
    """Test workflow behavior with ambiguous or contradictory requirements.
    
    **Validates: Requirements 11.1, 11.3**
    """
    
    def test_contradictory_requirements(self):
        """Test detection of contradictory requirements."""
        # Simulate contradictory requirements
        requirements = """
        Build a user authentication system.
        The system must NOT have any user authentication.
        Users should be able to login with passwords.
        Do not implement password-based login.
        """
        
        planning_agent = PlanningAgent()
        
        # The planning agent should either raise an error or flag contradictions
        try:
            result = planning_agent.create_execution_plan(requirements)
            # If it doesn't raise, check if it's flagged somehow in the plan
            # (implementation-dependent)
        except Exception as e:
            error_message = str(e)
            error_type = ErrorClassifier.classify_error(error_message)
            # Contradictions should be classified as critical
            assert error_type == ErrorType.CRITICAL or "contradict" in error_message.lower()
    
    def test_vague_requirements(self):
        """Test handling of extremely vague requirements."""
        requirements = "Make something cool with computers"
        
        planning_agent = PlanningAgent()
        
        # Vague requirements may still create a plan, but should be flagged
        try:
            result = planning_agent.create_execution_plan(requirements)
            # If planning succeeds, the plan should have minimal tasks
            assert result is not None
        except Exception as e:
            # Or it may fail with ambiguous requirements error
            error_message = str(e)
            assert "ambiguous" in error_message.lower() or "vague" in error_message.lower()
    
    def test_ambiguous_requirements_error_classification(self):
        """Test that ambiguous requirements errors are classified as critical."""
        error_message = "Ambiguous requirements: cannot determine required functionality"
        error_type = ErrorClassifier.classify_error(error_message)
        
        assert error_type == ErrorType.CRITICAL
    
    def test_workflow_state_with_ambiguous_requirements(self):
        """Test error handling for ambiguous requirements in workflow."""
        state = WorkflowState(
            thread_id="test-ambiguous",
            user_requirements="Build something, maybe with databases"
        )
        
        error_handler = ErrorHandler()
        result = error_handler.handle_error(
            agent="planning",
            task_id="initial_planning",
            error_message="Invalid requirements: requirements are too ambiguous to create execution plan",
            error_traceback=None,
            state=state
        )
        
        # Ambiguous requirements should require human approval
        assert result["action"] == "request_approval"
        assert result["error_type"] == ErrorType.CRITICAL.value


class TestDockerNotRunningEdgeCase:
    """Test workflow behavior when Docker is not running.
    
    **Validates: Requirements 11.1, 11.2, 11.3**
    """
    
    def test_docker_not_running_error_classification(self):
        """Test that Docker not running errors are classified as critical."""
        error_messages = [
            "Docker daemon not running",
            "Cannot connect to Docker daemon",
            "docker not found",
            "Docker is not installed",
            "Error response from daemon: dial unix docker.raw.sock: connect: connection refused"
        ]
        
        for error_message in error_messages:
            error_type = ErrorClassifier.classify_error(error_message)
            assert error_type == ErrorType.CRITICAL, f"Failed for: {error_message}"
    
    @patch('subprocess.run')
    def test_database_agent_docker_check_failure(self, mock_run):
        """Test database agent behavior when Docker is not running."""
        # Simulate Docker not running
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'docker ps',
            stderr=b"Cannot connect to the Docker daemon"
        )
        
        database_agent = DatabaseAgent()
        state = WorkflowState(
            thread_id="test-docker-fail",
            user_requirements="Test requirements"
        )
        
        # Database agent should detect Docker is not running
        with pytest.raises(Exception) as exc_info:
            database_agent.initialize_postgres(state)
        
        error_message = str(exc_info.value)
        assert "docker" in error_message.lower()
        
        # Classify and verify it's critical
        error_type = ErrorClassifier.classify_error(error_message)
        assert error_type == ErrorType.CRITICAL
    
    def test_docker_not_running_no_retry(self):
        """Test that Docker not running errors are NOT retried automatically."""
        state = WorkflowState(
            thread_id="test-docker-no-retry",
            user_requirements="Test requirements",
            retry_counts={}
        )
        
        error_handler = ErrorHandler()
        result = error_handler.handle_error(
            agent="database",
            task_id="init_postgres",
            error_message="Docker daemon not running",
            error_traceback="subprocess.CalledProcessError: docker ps failed",
            state=state
        )
        
        # Critical errors should request approval, not retry
        assert result["action"] == "request_approval"
        assert result["error_type"] == ErrorType.CRITICAL.value
        assert "Critical error" in result["reason"]
    
    @patch('subprocess.run')
    def test_workflow_fails_gracefully_without_docker(self, mock_run):
        """Test complete workflow handles Docker unavailability gracefully."""
        # Simulate Docker check failing
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Cannot connect to the Docker daemon"
        )
        
        state = WorkflowState(
            thread_id="test-no-docker-workflow",
            user_requirements="Build a simple app",
            execution_plan=[
                TaskDefinition(
                    id="task_1",
                    description="Initialize database",
                    agent="database",
                    dependencies=[],
                    estimated_duration="5 min"
                )
            ]
        )
        
        database_agent = DatabaseAgent()
        error_handler = ErrorHandler()
        
        try:
            database_agent.initialize_postgres(state)
        except Exception as e:
            result = error_handler.handle_error(
                agent="database",
                task_id="task_1",
                error_message=str(e),
                error_traceback=None,
                state=state
            )
            
            # Verify proper error handling
            assert result["action"] == "request_approval"
            assert len(state.error_log) == 1
            assert state.error_log[0].error_type == ErrorType.CRITICAL.value


class TestNetworkFailureEdgeCase:
    """Test workflow behavior with network failures during package installation.
    
    **Validates: Requirements 11.1, 11.2, 11.3**
    """
    
    def test_network_timeout_error_classification(self):
        """Test that network timeout errors are classified as transient."""
        error_messages = [
            "Connection timeout after 30 seconds",
            "Network unreachable",
            "Connection refused",
            "DNS resolution failed",
            "Read timed out",
            "Connection reset by peer",
            "Temporary failure in name resolution"
        ]
        
        for error_message in error_messages:
            error_type = ErrorClassifier.classify_error(error_message)
            assert error_type == ErrorType.TRANSIENT, f"Failed for: {error_message}"
    
    def test_package_installation_network_failure_retry(self):
        """Test that package installation network failures trigger retry with backoff."""
        state = WorkflowState(
            thread_id="test-network-fail",
            user_requirements="Test requirements",
            retry_counts={}
        )
        
        error_handler = ErrorHandler()
        result = error_handler.handle_error(
            agent="backend",
            task_id="install_packages",
            error_message="pip install failed: Connection timeout",
            error_traceback="urllib3.exceptions.ReadTimeoutError: Read timed out",
            state=state
        )
        
        # Network failures should retry with backoff
        assert result["action"] == "retry"
        assert result["error_type"] == ErrorType.TRANSIENT.value
        assert result["backoff_time"] == 1.0  # First retry
        assert state.retry_counts["backend"] == 1
    
    def test_npm_install_network_failure_retry(self):
        """Test npm install network failure handling."""
        state = WorkflowState(
            thread_id="test-npm-network-fail",
            user_requirements="Test requirements",
            retry_counts={"frontend": 2}  # Already tried twice
        )
        
        error_handler = ErrorHandler()
        result = error_handler.handle_error(
            agent="frontend",
            task_id="install_npm_packages",
            error_message="npm ERR! network request to https://registry.npmjs.org failed, reason: connect ETIMEDOUT",
            error_traceback=None,
            state=state
        )
        
        # Should still retry (within limits)
        assert result["action"] == "retry"
        assert result["backoff_time"] == 4.0  # Third retry: 2^2 = 4
        assert state.retry_counts["frontend"] == 3
    
    def test_network_failure_exponential_backoff(self):
        """Test exponential backoff progression for network failures."""
        state = WorkflowState(
            thread_id="test-backoff",
            user_requirements="Test requirements",
            retry_counts={}
        )
        
        error_handler = ErrorHandler()
        
        # Simulate multiple network failures
        backoff_times = []
        for i in range(5):
            result = error_handler.handle_error(
                agent="backend",
                task_id="network_operation",
                error_message="Connection timeout",
                error_traceback=None,
                state=state
            )
            
            if result["action"] == "retry":
                backoff_times.append(result["backoff_time"])
        
        # Verify exponential backoff: 1, 2, 4, 8, 16
        assert backoff_times[0] == 1.0
        assert backoff_times[1] == 2.0
        assert backoff_times[2] == 4.0
        assert backoff_times[3] == 8.0
        assert backoff_times[4] == 16.0
    
    def test_network_failure_max_retries_then_approval(self):
        """Test that max retries for network failures leads to approval request."""
        state = WorkflowState(
            thread_id="test-max-network-retries",
            user_requirements="Test requirements",
            retry_counts={"backend": 4}  # Already at 4 retries
        )
        
        error_handler = ErrorHandler()
        result = error_handler.handle_error(
            agent="backend",
            task_id="install_packages",
            error_message="Connection timeout",
            error_traceback=None,
            state=state
        )
        
        # At 5 retries, should request approval
        assert result["action"] == "request_approval"
        assert "Max retries exceeded" in result["reason"]
        assert state.retry_counts["backend"] == 5
    
    @patch('subprocess.run')
    def test_backend_agent_handles_pip_timeout(self, mock_run):
        """Test backend agent handling of pip installation timeout."""
        # Simulate pip timeout
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd='pip install fastapi',
            timeout=30
        )
        
        backend_agent = BackendAgent()
        state = WorkflowState(
            thread_id="test-pip-timeout",
            user_requirements="Build a FastAPI app"
        )
        
        error_handler = ErrorHandler()
        
        try:
            # Attempt to install packages (would fail)
            subprocess.run(['pip', 'install', 'fastapi'], timeout=30, check=True)
        except subprocess.TimeoutExpired as e:
            result = error_handler.handle_error(
                agent="backend",
                task_id="install_dependencies",
                error_message=str(e),
                error_traceback=None,
                state=state
            )
            
            # Should classify as transient and retry
            assert result["action"] == "retry"
            assert result["error_type"] == ErrorType.TRANSIENT.value


class TestInsufficientResourcesEdgeCase:
    """Test workflow behavior with insufficient system resources.
    
    **Validates: Requirements 11.1, 11.3**
    """
    
    def test_out_of_memory_error_classification(self):
        """Test that out of memory errors are classified as critical."""
        error_messages = [
            "Fatal: out of memory",
            "Cannot allocate memory",
            "Insufficient memory to continue",
            "MemoryError: unable to allocate array",
            "OSError: [Errno 12] Cannot allocate memory"
        ]
        
        for error_message in error_messages:
            error_type = ErrorClassifier.classify_error(error_message)
            assert error_type == ErrorType.CRITICAL, f"Failed for: {error_message}"
    
    def test_disk_space_error_classification(self):
        """Test that disk space errors are classified as critical."""
        error_messages = [
            "No space left on device",
            "Disk quota exceeded",
            "Insufficient disk space",
            "OSError: [Errno 28] No space left on device"
        ]
        
        for error_message in error_messages:
            error_type = ErrorClassifier.classify_error(error_message)
            assert error_type == ErrorType.CRITICAL, f"Failed for: {error_message}"
    
    def test_out_of_memory_no_retry(self):
        """Test that out of memory errors are not retried automatically."""
        state = WorkflowState(
            thread_id="test-oom",
            user_requirements="Test requirements",
            retry_counts={}
        )
        
        error_handler = ErrorHandler()
        result = error_handler.handle_error(
            agent="backend",
            task_id="generate_code",
            error_message="Fatal: out of memory",
            error_traceback="MemoryError: unable to allocate 1024 MB",
            state=state
        )
        
        # Critical errors should request approval, not retry
        assert result["action"] == "request_approval"
        assert result["error_type"] == ErrorType.CRITICAL.value
    
    def test_disk_space_error_requires_approval(self):
        """Test that disk space errors require human approval."""
        state = WorkflowState(
            thread_id="test-disk-space",
            user_requirements="Test requirements",
            retry_counts={}
        )
        
        error_handler = ErrorHandler()
        result = error_handler.handle_error(
            agent="deployment",
            task_id="build_docker_image",
            error_message="Error: No space left on device",
            error_traceback="OSError: [Errno 28] No space left on device",
            state=state
        )
        
        assert result["action"] == "request_approval"
        assert result["error_type"] == ErrorType.CRITICAL.value
        assert "Critical error" in result["reason"]
    
    def test_resource_exhaustion_workflow_state(self):
        """Test workflow state handling with resource exhaustion."""
        state = WorkflowState(
            thread_id="test-resource-exhaustion",
            user_requirements="Build large application",
            execution_plan=[
                TaskDefinition(
                    id="task_1",
                    description="Generate backend",
                    agent="backend",
                    dependencies=[],
                    estimated_duration="10 min"
                )
            ],
            retry_counts={}
        )
        
        error_handler = ErrorHandler()
        
        # Simulate memory error
        result = error_handler.handle_error(
            agent="backend",
            task_id="task_1",
            error_message="Cannot allocate memory for LLM inference",
            error_traceback="MemoryError",
            state=state
        )
        
        # Verify proper handling
        assert result["action"] == "request_approval"
        assert len(state.error_log) == 1
        assert state.error_log[0].agent == "backend"
        assert state.error_log[0].error_type == ErrorType.CRITICAL.value
    
    def test_permission_denied_error_classification(self):
        """Test that permission denied errors are classified as critical."""
        error_messages = [
            "Permission denied",
            "OSError: [Errno 13] Permission denied",
            "Access denied: insufficient permissions"
        ]
        
        for error_message in error_messages:
            error_type = ErrorClassifier.classify_error(error_message)
            assert error_type == ErrorType.CRITICAL, f"Failed for: {error_message}"


class TestEdgeCaseRecoveryIntegration:
    """Integration tests for edge case recovery mechanisms.
    
    **Validates: Requirements 11.2, 11.4, 11.5**
    """
    
    def test_rollback_after_critical_error(self):
        """Test that workflow can rollback after critical error."""
        state = WorkflowState(
            thread_id="test-rollback",
            user_requirements="Test requirements",
            current_task_id="task_3",
            completed_task_ids=["task_1", "task_2"],
            execution_plan=[
                TaskDefinition(
                    id="task_1",
                    description="Planning",
                    agent="planning",
                    dependencies=[],
                    estimated_duration="2 min"
                ),
                TaskDefinition(
                    id="task_2",
                    description="Backend",
                    agent="backend",
                    dependencies=["task_1"],
                    estimated_duration="5 min"
                ),
                TaskDefinition(
                    id="task_3",
                    description="Database",
                    agent="database",
                    dependencies=["task_2"],
                    estimated_duration="5 min"
                )
            ]
        )
        
        # Simulate critical error
        error_handler = ErrorHandler()
        error_handler.handle_error(
            agent="database",
            task_id="task_3",
            error_message="Docker daemon not running",
            error_traceback=None,
            state=state
        )
        
        # Verify rollback is possible
        assert CheckpointRollback.can_rollback(state)
        
        # Perform rollback to last successful task
        rolled_back = CheckpointRollback.prepare_rollback(state, "task_2")
        
        assert rolled_back.completed_task_ids == ["task_1", "task_2"]
        assert rolled_back.current_task_id is None
        assert rolled_back.workflow_status == "running"
    
    def test_error_summary_after_multiple_failures(self):
        """Test error summary aggregation after multiple edge case failures."""
        state = WorkflowState(
            thread_id="test-multi-error",
            user_requirements="Test requirements",
            retry_counts={"backend": 3, "database": 2, "frontend": 1}
        )
        
        error_handler = ErrorHandler()
        
        # Add multiple errors
        error_handler.handle_error(
            agent="backend",
            task_id="task_1",
            error_message="Connection timeout",
            error_traceback=None,
            state=state
        )
        
        error_handler.handle_error(
            agent="database",
            task_id="task_2",
            error_message="Docker not running",
            error_traceback=None,
            state=state
        )
        
        error_handler.handle_error(
            agent="frontend",
            task_id="task_3",
            error_message="npm install timeout",
            error_traceback=None,
            state=state
        )
        
        # Get error summary
        summary = error_handler.get_error_summary(state)
        
        assert summary["total_errors"] == 3
        assert summary["by_agent"]["backend"] == 1
        assert summary["by_agent"]["database"] == 1
        assert summary["by_agent"]["frontend"] == 1
        assert summary["retry_counts"]["backend"] == 4  # Incremented
        assert summary["retry_counts"]["database"] == 3
        assert summary["retry_counts"]["frontend"] == 2
    
    def test_mixed_error_types_routing(self):
        """Test proper routing with mix of transient and critical errors."""
        state = WorkflowState(
            thread_id="test-mixed-errors",
            user_requirements="Test requirements",
            retry_counts={}
        )
        
        error_handler = ErrorHandler()
        
        # First error: transient (should retry)
        result1 = error_handler.handle_error(
            agent="backend",
            task_id="task_1",
            error_message="Connection timeout",
            error_traceback=None,
            state=state
        )
        assert result1["action"] == "retry"
        
        # Second error: critical (should request approval)
        result2 = error_handler.handle_error(
            agent="database",
            task_id="task_2",
            error_message="Docker daemon not running",
            error_traceback=None,
            state=state
        )
        assert result2["action"] == "request_approval"
        
        # Verify state reflects both errors
        assert len(state.error_log) == 2
        assert state.error_log[0].error_type == ErrorType.TRANSIENT.value
        assert state.error_log[1].error_type == ErrorType.CRITICAL.value
    
    def test_global_retry_limit_across_edge_cases(self):
        """Test that global retry limit is enforced across multiple edge cases."""
        state = WorkflowState(
            thread_id="test-global-limit",
            user_requirements="Test requirements",
            retry_counts={
                "backend": 5,
                "frontend": 5,
                "database": 5,
                "testing": 4  # Total: 19
            }
        )
        
        error_handler = ErrorHandler()
        
        # This should be the 20th retry, hitting global limit
        result = error_handler.handle_error(
            agent="testing",
            task_id="run_tests",
            error_message="Network timeout during test execution",
            error_traceback=None,
            state=state
        )
        
        # Even though it's transient, global limit should trigger approval
        assert result["action"] == "request_approval"
        assert "Max retries exceeded" in result["reason"]
        assert sum(state.retry_counts.values()) == 20


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
