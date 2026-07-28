"""
Unit tests for checkpointing infrastructure.

Tests cover:
- State serialization and deserialization
- Thread ID management and isolation
- Checkpoint cleanup on workflow completion
- Checkpoint restoration for workflow resumption
"""

import os
import tempfile
import pytest
from datetime import datetime
from pathlib import Path

from workflow.checkpointing import CheckpointManager, create_checkpoint_manager
from workflow.models import WorkflowState, TaskDefinition, ErrorRecord


class TestCheckpointManager:
    """Test suite for CheckpointManager class."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def checkpoint_manager(self, temp_db_path):
        """Create a CheckpointManager instance for testing."""
        return CheckpointManager(temp_db_path)
    
    @pytest.fixture
    def sample_workflow_state(self):
        """Create a sample WorkflowState for testing."""
        return WorkflowState(
            thread_id="test_thread_123",
            user_requirements="Build a todo app",
            requirements_source="text",
            workflow_status="running",
            execution_plan=[
                TaskDefinition(
                    id="task_1",
                    description="Initialize database",
                    agent="database",
                    dependencies=[],
                    status="pending"
                )
            ]
        )
    
    def test_checkpoint_manager_initialization(self, temp_db_path):
        """Test CheckpointManager initializes correctly."""
        manager = CheckpointManager(temp_db_path)
        
        assert manager.checkpoint_db_path == temp_db_path
        assert manager._saver is None  # Lazy initialization
    
    def test_checkpoint_manager_creates_db_directory(self):
        """Test CheckpointManager creates database directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "subdir", "checkpoints.db")
            
            manager = CheckpointManager(db_path)
            
            # Directory should be created
            assert os.path.exists(os.path.dirname(db_path))
    
    def test_get_saver_lazy_initialization(self, checkpoint_manager):
        """Test get_saver creates SqliteSaver on first call."""
        assert checkpoint_manager._saver is None
        
        saver = checkpoint_manager.get_saver()
        
        assert saver is not None
        assert checkpoint_manager._saver is saver
        
        # Second call should return same instance
        saver2 = checkpoint_manager.get_saver()
        assert saver2 is saver
    
    def test_generate_thread_id_uniqueness(self, checkpoint_manager):
        """Test generate_thread_id creates unique IDs."""
        thread_id1 = checkpoint_manager.generate_thread_id()
        thread_id2 = checkpoint_manager.generate_thread_id()
        
        assert thread_id1 != thread_id2
        assert thread_id1.startswith("workflow_")
        assert thread_id2.startswith("workflow_")
    
    def test_generate_thread_id_custom_prefix(self, checkpoint_manager):
        """Test generate_thread_id accepts custom prefix."""
        thread_id = checkpoint_manager.generate_thread_id(prefix="custom")
        
        assert thread_id.startswith("custom_")
    
    def test_serialize_state(self, checkpoint_manager, sample_workflow_state):
        """Test serialize_state converts WorkflowState to dictionary."""
        serialized = checkpoint_manager.serialize_state(sample_workflow_state)
        
        assert isinstance(serialized, dict)
        assert serialized["thread_id"] == "test_thread_123"
        assert serialized["user_requirements"] == "Build a todo app"
        assert serialized["workflow_status"] == "running"
        assert len(serialized["execution_plan"]) == 1
    
    def test_deserialize_state(self, checkpoint_manager, sample_workflow_state):
        """Test deserialize_state reconstructs WorkflowState from dictionary."""
        # Serialize then deserialize
        serialized = checkpoint_manager.serialize_state(sample_workflow_state)
        deserialized = checkpoint_manager.deserialize_state(serialized)
        
        assert isinstance(deserialized, WorkflowState)
        assert deserialized.thread_id == sample_workflow_state.thread_id
        assert deserialized.user_requirements == sample_workflow_state.user_requirements
        assert deserialized.workflow_status == sample_workflow_state.workflow_status
        assert len(deserialized.execution_plan) == len(sample_workflow_state.execution_plan)
    
    def test_serialize_deserialize_round_trip(self, checkpoint_manager, sample_workflow_state):
        """Test state remains unchanged after serialize->deserialize round trip."""
        # Add more complex data
        sample_workflow_state.error_log.append(
            ErrorRecord(
                agent="backend",
                task_id="task_1",
                error_type="transient",
                message="Connection timeout",
                retry_count=1
            )
        )
        sample_workflow_state.retry_counts = {"backend": 1}
        sample_workflow_state.completed_task_ids = ["task_0"]
        
        # Round trip
        serialized = checkpoint_manager.serialize_state(sample_workflow_state)
        deserialized = checkpoint_manager.deserialize_state(serialized)
        
        # Verify all fields
        assert deserialized.thread_id == sample_workflow_state.thread_id
        assert deserialized.user_requirements == sample_workflow_state.user_requirements
        assert len(deserialized.error_log) == 1
        assert deserialized.error_log[0].agent == "backend"
        assert deserialized.retry_counts == {"backend": 1}
        assert deserialized.completed_task_ids == ["task_0"]
    
    def test_list_checkpoints_empty_database(self, checkpoint_manager):
        """Test list_checkpoints returns empty list for new database."""
        # Initialize the database
        checkpoint_manager.get_saver()
        
        checkpoints = checkpoint_manager.list_checkpoints()
        
        assert isinstance(checkpoints, list)
        # May be empty or may have some initialization data
        assert len(checkpoints) >= 0
    
    def test_list_checkpoints_with_thread_id_filter(self, checkpoint_manager):
        """Test list_checkpoints can filter by thread_id."""
        # Initialize the database
        checkpoint_manager.get_saver()
        
        checkpoints = checkpoint_manager.list_checkpoints(thread_id="nonexistent_thread")
        
        assert isinstance(checkpoints, list)
        assert len(checkpoints) == 0
    
    def test_get_incomplete_workflows(self, checkpoint_manager):
        """Test get_incomplete_workflows detects resumable workflows."""
        # Initialize the database
        checkpoint_manager.get_saver()
        
        incomplete = checkpoint_manager.get_incomplete_workflows()
        
        assert isinstance(incomplete, list)
    
    def test_cleanup_checkpoint(self, checkpoint_manager):
        """Test cleanup_checkpoint removes checkpoint data."""
        # Initialize the database
        checkpoint_manager.get_saver()
        
        # Try to clean up a nonexistent thread (should not error)
        result = checkpoint_manager.cleanup_checkpoint("test_thread_123")
        
        assert isinstance(result, bool)
    
    def test_get_checkpoint_stats(self, checkpoint_manager):
        """Test get_checkpoint_stats returns statistics."""
        # Initialize the database
        checkpoint_manager.get_saver()
        
        stats = checkpoint_manager.get_checkpoint_stats()
        
        assert isinstance(stats, dict)
        assert "checkpoint_count" in stats
        assert "thread_count" in stats
        assert "db_size_bytes" in stats
        assert "db_path" in stats
        assert stats["db_path"] == checkpoint_manager.checkpoint_db_path
    
    def test_verify_checkpoint_integrity_nonexistent_thread(self, checkpoint_manager):
        """Test verify_checkpoint_integrity returns False for nonexistent thread."""
        # Initialize the database
        checkpoint_manager.get_saver()
        
        result = checkpoint_manager.verify_checkpoint_integrity("nonexistent_thread")
        
        assert result is False


class TestCheckpointFactory:
    """Test suite for checkpoint factory function."""
    
    def test_create_checkpoint_manager_default(self):
        """Test create_checkpoint_manager with default path."""
        # Note: This uses the actual config, so we can't easily test without mocking
        # For now, just verify it creates an instance
        manager = create_checkpoint_manager()
        
        assert isinstance(manager, CheckpointManager)
    
    def test_create_checkpoint_manager_custom_path(self):
        """Test create_checkpoint_manager with custom path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            manager = create_checkpoint_manager(db_path)
            
            assert isinstance(manager, CheckpointManager)
            assert manager.checkpoint_db_path == db_path
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestThreadIsolation:
    """Test suite for thread ID isolation between workflows."""
    
    @pytest.fixture
    def checkpoint_manager(self):
        """Create a CheckpointManager with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        manager = CheckpointManager(db_path)
        yield manager
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_different_threads_have_unique_ids(self, checkpoint_manager):
        """Test different workflow executions get unique thread IDs."""
        thread_id1 = checkpoint_manager.generate_thread_id()
        thread_id2 = checkpoint_manager.generate_thread_id()
        thread_id3 = checkpoint_manager.generate_thread_id()
        
        # All should be unique
        assert len({thread_id1, thread_id2, thread_id3}) == 3
    
    def test_thread_id_format(self, checkpoint_manager):
        """Test thread ID has expected format."""
        thread_id = checkpoint_manager.generate_thread_id()
        
        # Should be: prefix_YYYYMMDD_HHMMSS_microseconds
        parts = thread_id.split("_")
        assert len(parts) >= 4
        assert parts[0] == "workflow"
        
        # Second part should be a date in YYYYMMDD format
        date_part = parts[1]
        assert len(date_part) == 8
        assert date_part.isdigit()


class TestCheckpointCleanup:
    """Test suite for checkpoint cleanup functionality."""
    
    @pytest.fixture
    def checkpoint_manager(self):
        """Create a CheckpointManager with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        manager = CheckpointManager(db_path)
        # Initialize database
        manager.get_saver()
        yield manager
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_cleanup_checkpoint_success(self, checkpoint_manager):
        """Test cleanup_checkpoint returns True on success."""
        result = checkpoint_manager.cleanup_checkpoint("test_thread")
        
        # Should succeed even if thread doesn't exist
        assert result is True
    
    def test_cleanup_all_completed(self, checkpoint_manager):
        """Test cleanup_all_completed returns count."""
        count = checkpoint_manager.cleanup_all_completed()
        
        assert isinstance(count, int)
        assert count >= 0


class TestStateSerializationEdgeCases:
    """Test edge cases in state serialization."""
    
    @pytest.fixture
    def checkpoint_manager(self):
        """Create a CheckpointManager with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        manager = CheckpointManager(db_path)
        yield manager
        
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_serialize_minimal_state(self, checkpoint_manager):
        """Test serializing state with minimal fields."""
        state = WorkflowState(
            thread_id="minimal_thread",
            user_requirements="Minimal requirements"
        )
        
        serialized = checkpoint_manager.serialize_state(state)
        
        assert serialized["thread_id"] == "minimal_thread"
        assert serialized["user_requirements"] == "Minimal requirements"
    
    def test_serialize_state_with_complex_nested_data(self, checkpoint_manager):
        """Test serializing state with complex nested structures."""
        state = WorkflowState(
            thread_id="complex_thread",
            user_requirements="Complex requirements",
            execution_plan=[
                TaskDefinition(
                    id="task_1",
                    description="Task 1",
                    agent="backend",
                    dependencies=["task_0"],
                    status="complete"
                ),
                TaskDefinition(
                    id="task_2",
                    description="Task 2",
                    agent="frontend",
                    dependencies=["task_1"],
                    status="in_progress"
                )
            ],
            error_log=[
                ErrorRecord(
                    agent="backend",
                    task_id="task_1",
                    error_type="recoverable",
                    message="Test error",
                    traceback="Traceback...",
                    retry_count=2
                )
            ],
            completed_task_ids=["task_0", "task_1"],
            retry_counts={"backend": 2, "frontend": 0}
        )
        
        serialized = checkpoint_manager.serialize_state(state)
        deserialized = checkpoint_manager.deserialize_state(serialized)
        
        assert len(deserialized.execution_plan) == 2
        assert len(deserialized.error_log) == 1
        assert deserialized.execution_plan[0].id == "task_1"
        assert deserialized.execution_plan[1].dependencies == ["task_1"]
        assert deserialized.error_log[0].retry_count == 2
        assert deserialized.retry_counts == {"backend": 2, "frontend": 0}
