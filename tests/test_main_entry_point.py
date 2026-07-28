"""
Unit tests for main.py entry point functionality.

Tests cover:
- Docker validation
- Node.js validation
- Python package validation
- Pre-flight checks
- Directory creation
- Command-line argument parsing
- Workflow listing
- Workflow resumption
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import main
from workflow.checkpointing import CheckpointManager


class TestDockerValidation:
    """Tests for Docker daemon validation."""
    
    def test_validate_docker_success(self):
        """Test Docker validation when daemon is running."""
        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_client.ping.return_value = True
            mock_docker.return_value = mock_client
            
            assert main.validate_docker() is True
    
    def test_validate_docker_daemon_not_running(self):
        """Test Docker validation when daemon is not running."""
        with patch('docker.from_env') as mock_docker:
            from docker.errors import DockerException
            mock_docker.side_effect = DockerException("Daemon not running")
            
            assert main.validate_docker() is False
    
    def test_validate_docker_general_error(self):
        """Test Docker validation with general error."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.side_effect = Exception("Unknown error")
            
            assert main.validate_docker() is False


class TestNodeValidation:
    """Tests for Node.js validation."""
    
    def test_validate_nodejs_installed(self):
        """Test Node.js validation when installed."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = "/usr/local/bin/node"
            
            assert main.validate_nodejs() is True
    
    def test_validate_nodejs_not_installed(self):
        """Test Node.js validation when not installed."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = None
            
            assert main.validate_nodejs() is False


class TestPythonPackageValidation:
    """Tests for Python package validation."""
    
    def test_validate_python_packages_all_installed(self):
        """Test package validation when all packages are installed."""
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = Mock()
            
            all_installed, missing = main.validate_python_packages()
            
            assert all_installed is True
            assert missing == []
    
    def test_validate_python_packages_some_missing(self):
        """Test package validation when some packages are missing."""
        def import_side_effect(name):
            if name in ["langchain", "docker"]:
                raise ImportError(f"No module named '{name}'")
            return Mock()
        
        with patch('builtins.__import__') as mock_import:
            mock_import.side_effect = import_side_effect
            
            all_installed, missing = main.validate_python_packages()
            
            assert all_installed is False
            assert "langchain" in missing
            assert "docker" in missing


class TestPreflightChecks:
    """Tests for pre-flight checks."""
    
    def test_preflight_checks_all_pass(self, capsys):
        """Test pre-flight checks when all checks pass."""
        with patch('main.validate_docker', return_value=True), \
             patch('main.validate_nodejs', return_value=True), \
             patch('main.validate_python_packages', return_value=(True, [])):
            
            result = main.run_preflight_checks()
            
            assert result is True
            captured = capsys.readouterr()
            assert "All pre-flight checks passed" in captured.out
    
    def test_preflight_checks_docker_fails(self, capsys):
        """Test pre-flight checks when Docker validation fails."""
        with patch('main.validate_docker', return_value=False), \
             patch('main.validate_nodejs', return_value=True), \
             patch('main.validate_python_packages', return_value=(True, [])):
            
            result = main.run_preflight_checks()
            
            assert result is False
            captured = capsys.readouterr()
            assert "Pre-flight checks failed" in captured.out
            assert "Docker daemon is not running" in captured.out
    
    def test_preflight_checks_nodejs_fails(self, capsys):
        """Test pre-flight checks when Node.js validation fails."""
        with patch('main.validate_docker', return_value=True), \
             patch('main.validate_nodejs', return_value=False), \
             patch('main.validate_python_packages', return_value=(True, [])):
            
            result = main.run_preflight_checks()
            
            assert result is False
            captured = capsys.readouterr()
            assert "Pre-flight checks failed" in captured.out
            assert "Node.js is not installed" in captured.out
    
    def test_preflight_checks_packages_fail(self, capsys):
        """Test pre-flight checks when package validation fails."""
        with patch('main.validate_docker', return_value=True), \
             patch('main.validate_nodejs', return_value=True), \
             patch('main.validate_python_packages', return_value=(False, ["langchain", "docker"])):
            
            result = main.run_preflight_checks()
            
            assert result is False
            captured = capsys.readouterr()
            assert "Pre-flight checks failed" in captured.out
            assert "Missing required packages" in captured.out


class TestDirectoryCreation:
    """Tests for output directory creation."""
    
    def test_create_output_directories_new(self, tmp_path, capsys):
        """Test creating new output directories."""
        frontend_dir = tmp_path / "frontend"
        backend_dir = tmp_path / "backend"
        
        with patch('main.get_config') as mock_config:
            config = Mock()
            config.frontend_output_dir = str(frontend_dir)
            config.backend_output_dir = str(backend_dir)
            mock_config.return_value = config
            
            main.create_output_directories()
            
            assert frontend_dir.exists()
            assert backend_dir.exists()
            
            captured = capsys.readouterr()
            assert "Created:" in captured.out
    
    def test_create_output_directories_existing(self, tmp_path, capsys):
        """Test creating directories that already exist."""
        frontend_dir = tmp_path / "frontend"
        backend_dir = tmp_path / "backend"
        frontend_dir.mkdir()
        backend_dir.mkdir()
        
        with patch('main.get_config') as mock_config:
            config = Mock()
            config.frontend_output_dir = str(frontend_dir)
            config.backend_output_dir = str(backend_dir)
            mock_config.return_value = config
            
            main.create_output_directories()
            
            assert frontend_dir.exists()
            assert backend_dir.exists()
            
            captured = capsys.readouterr()
            assert "Already exists:" in captured.out


class TestListWorkflows:
    """Tests for workflow listing functionality."""
    
    def test_list_workflows_none_found(self, capsys):
        """Test listing workflows when none exist."""
        with patch('main.CheckpointManager') as mock_manager:
            manager_instance = Mock()
            manager_instance.get_incomplete_workflows.return_value = []
            mock_manager.return_value = manager_instance
            
            main.list_workflows()
            
            captured = capsys.readouterr()
            assert "No incomplete workflows found" in captured.out
    
    def test_list_workflows_found(self, capsys):
        """Test listing workflows when some exist."""
        from workflow.checkpointing import CheckpointMetadata
        from datetime import datetime
        
        with patch('main.CheckpointManager') as mock_manager:
            manager_instance = Mock()
            manager_instance.get_incomplete_workflows.return_value = ["thread-1", "thread-2"]
            
            checkpoint = CheckpointMetadata(
                thread_id="thread-1",
                checkpoint_id="checkpoint-1",
                created_at=datetime.now(),
                node_name="planning",
                workflow_status="in_progress"
            )
            manager_instance.list_checkpoints.return_value = [checkpoint]
            mock_manager.return_value = manager_instance
            
            main.list_workflows()
            
            captured = capsys.readouterr()
            assert "Found 2 incomplete workflow(s)" in captured.out
            assert "thread-1" in captured.out
            assert "To resume a workflow" in captured.out


class TestArgumentParsing:
    """Tests for command-line argument parsing."""
    
    def test_main_with_requirements_text(self):
        """Test main with text requirements."""
        test_args = ["main.py", "Build a todo app"]
        
        with patch('sys.argv', test_args), \
             patch('main.start_new_workflow') as mock_start:
            
            main.main()
            
            mock_start.assert_called_once_with("Build a todo app")
    
    def test_main_with_list_workflows(self):
        """Test main with --list-workflows flag."""
        test_args = ["main.py", "--list-workflows"]
        
        with patch('sys.argv', test_args), \
             patch('main.list_workflows') as mock_list:
            
            main.main()
            
            mock_list.assert_called_once()
    
    def test_main_with_resume(self):
        """Test main with --resume flag."""
        test_args = ["main.py", "--resume", "thread-123"]
        
        with patch('sys.argv', test_args), \
             patch('main.resume_workflow') as mock_resume:
            
            main.main()
            
            mock_resume.assert_called_once_with("thread-123")
    
    def test_main_no_arguments(self):
        """Test main with no arguments."""
        test_args = ["main.py"]
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            
            assert exc_info.value.code == 1


class TestResumeWorkflow:
    """Tests for workflow resumption."""
    
    def test_resume_workflow_invalid_thread(self, capsys):
        """Test resuming workflow with invalid thread ID."""
        with patch('main.CheckpointManager') as mock_manager:
            manager_instance = Mock()
            manager_instance.verify_checkpoint_integrity.return_value = False
            mock_manager.return_value = manager_instance
            
            with pytest.raises(SystemExit) as exc_info:
                main.resume_workflow("invalid-thread")
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "No valid checkpoint found" in captured.out
    
    def test_resume_workflow_user_cancels(self, capsys):
        """Test resuming workflow when user cancels."""
        from workflow.checkpointing import CheckpointMetadata
        from datetime import datetime
        
        with patch('main.CheckpointManager') as mock_manager, \
             patch('builtins.input', return_value="no"):
            
            manager_instance = Mock()
            manager_instance.verify_checkpoint_integrity.return_value = True
            
            checkpoint = CheckpointMetadata(
                thread_id="thread-1",
                checkpoint_id="checkpoint-1",
                created_at=datetime.now(),
                node_name="planning",
                workflow_status="in_progress"
            )
            manager_instance.list_checkpoints.return_value = [checkpoint]
            mock_manager.return_value = manager_instance
            
            with pytest.raises(SystemExit) as exc_info:
                main.resume_workflow("thread-1")
            
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "Resume cancelled by user" in captured.out


class TestStartNewWorkflow:
    """Tests for starting new workflow."""
    
    def test_start_new_workflow_preflight_fails(self, capsys):
        """Test starting new workflow when pre-flight checks fail."""
        with patch('main.run_preflight_checks', return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                main.start_new_workflow("Build a todo app")
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Pre-flight checks failed" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
