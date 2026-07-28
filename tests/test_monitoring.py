"""
Unit tests for workflow monitoring and observability infrastructure.

Tests cover:
- Structured logging for agent transitions
- Metrics collection (workflow duration, agent execution times, retry counts)
- Progress tracking and ETA calculation
- Workflow state visualization (ASCII and JSON)
- Metrics export (JSON and CSV)
"""

import json
import csv
import tempfile
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

import pytest

from workflow.monitoring import WorkflowMonitor, StructuredFormatter
from workflow.models import WorkflowState, TaskDefinition, ErrorRecord


@pytest.fixture
def sample_tasks():
    """Create sample task definitions."""
    return [
        TaskDefinition(
            id="task_1",
            description="Initialize database",
            agent="database",
            dependencies=[],
            status="complete"
        ),
        TaskDefinition(
            id="task_2",
            description="Generate backend code",
            agent="backend",
            dependencies=["task_1"],
            status="in_progress"
        ),
        TaskDefinition(
            id="task_3",
            description="Generate frontend code",
            agent="frontend",
            dependencies=["task_1"],
            status="pending"
        ),
    ]


@pytest.fixture
def sample_state(sample_tasks):
    """Create sample workflow state."""
    return WorkflowState(
        thread_id="test-workflow-123",
        user_requirements="Build a todo app",
        requirements_source="text",
        execution_plan=sample_tasks,
        current_task_id="task_2",
        completed_task_ids=["task_1"],
        workflow_status="running",
    )


@pytest.fixture
def monitor():
    """Create monitor with temp log file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_path = Path(f.name)
    
    monitor = WorkflowMonitor(log_file=log_path, enable_console=False)
    yield monitor
    
    # Cleanup
    if log_path.exists():
        log_path.unlink()


class TestStructuredFormatter:
    """Test JSON log formatting."""
    
    def test_formats_basic_log_as_json(self):
        """Verify basic log record is formatted as JSON."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert "timestamp" in data
    
    def test_includes_extra_fields(self):
        """Verify extra fields are included in JSON output."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Agent transition",
            args=(),
            exc_info=None
        )
        record.agent = "backend"
        record.task_id = "task_1"
        record.transition = {"from": "planning", "to": "backend"}
        
        result = formatter.format(record)
        data = json.loads(result)
        
        assert data["agent"] == "backend"
        assert data["task_id"] == "task_1"
        assert data["transition"]["from"] == "planning"


class TestWorkflowMonitor:
    """Test workflow monitoring functionality."""
    
    def test_initializes_with_default_metrics(self, monitor):
        """Verify monitor initializes with empty metrics."""
        assert monitor.metrics["workflow_start_time"] is None
        assert monitor.metrics["workflow_end_time"] is None
        assert monitor.metrics["total_tasks"] == 0
        assert monitor.metrics["completed_tasks"] == 0
        assert monitor.metrics["failed_tasks"] == 0
        assert monitor.metrics["error_count"] == 0
    
    def test_start_workflow_initializes_metrics(self, monitor, sample_state):
        """Verify workflow start initializes metrics correctly."""
        monitor.start_workflow(sample_state)
        
        assert monitor.metrics["workflow_start_time"] is not None
        assert monitor.metrics["total_tasks"] == len(sample_state.execution_plan)
        assert monitor.current_state == sample_state
    
    def test_end_workflow_calculates_duration(self, monitor, sample_state):
        """Verify workflow end calculates duration correctly."""
        # Start workflow
        monitor.start_workflow(sample_state)
        
        # Simulate some work
        import time
        time.sleep(0.1)
        
        # End workflow
        monitor.end_workflow(sample_state)
        
        assert monitor.metrics["workflow_end_time"] is not None
        assert monitor.metrics["workflow_duration"] is not None
        assert monitor.metrics["workflow_duration"] > 0
    
    def test_log_agent_transition_records_transition(self, monitor, sample_state):
        """Verify agent transitions are logged correctly."""
        monitor.start_workflow(sample_state)
        
        monitor.log_agent_transition(
            from_agent="planning",
            to_agent="backend",
            state=sample_state,
            reason="Task ready"
        )
        
        transitions = monitor.metrics["agent_transitions"]
        assert len(transitions) == 1
        assert transitions[0]["from_agent"] == "planning"
        assert transitions[0]["to_agent"] == "backend"
        assert transitions[0]["reason"] == "Task ready"
    
    def test_log_agent_transition_tracks_execution_time(self, monitor, sample_state):
        """Verify agent execution time is tracked."""
        monitor.start_workflow(sample_state)
        
        # Start backend agent
        monitor.log_agent_transition("supervisor", "backend", sample_state)
        
        # Simulate work
        import time
        time.sleep(0.1)
        
        # Transition away from backend
        monitor.log_agent_transition("backend", "supervisor", sample_state)
        
        # Check execution time was recorded
        assert "backend" in monitor.metrics["agent_execution_times"]
        assert len(monitor.metrics["agent_execution_times"]["backend"]) == 1
        assert monitor.metrics["agent_execution_times"]["backend"][0] > 0
    
    def test_log_agent_activity_writes_to_log(self, monitor, sample_state):
        """Verify agent activities are logged."""
        monitor.start_workflow(sample_state)
        
        monitor.log_agent_activity(
            agent="backend",
            activity="Generating API endpoints",
            task_id="task_2",
            details={"endpoint_count": 5}
        )
        
        # Verify log file contains the activity
        with open(monitor.log_file, 'r') as f:
            logs = [json.loads(line) for line in f]
        
        activity_logs = [log for log in logs if "Generating API endpoints" in log["message"]]
        assert len(activity_logs) > 0
        assert activity_logs[0]["agent"] == "backend"
    
    def test_log_error_increments_error_count(self, monitor, sample_state):
        """Verify errors increment error count."""
        monitor.start_workflow(sample_state)
        
        error = ErrorRecord(
            agent="backend",
            task_id="task_2",
            error_type="recoverable",
            message="Type checking failed",
            retry_count=1
        )
        
        monitor.log_error(error)
        
        assert monitor.metrics["error_count"] == 1
        assert monitor.metrics["retry_counts"]["backend"] == 1
    
    def test_log_retry_updates_retry_count(self, monitor, sample_state):
        """Verify retry attempts are tracked."""
        monitor.start_workflow(sample_state)
        
        monitor.log_retry(
            agent="backend",
            task_id="task_2",
            attempt=2,
            reason="Linting failures"
        )
        
        assert monitor.metrics["retry_counts"]["backend"] == 2
    
    def test_log_approval_request_increments_count(self, monitor, sample_state):
        """Verify approval requests are counted."""
        monitor.start_workflow(sample_state)
        
        monitor.log_approval_request(
            agent="deployment",
            message="Deploy to production?"
        )
        
        assert monitor.metrics["approval_count"] == 1
    
    def test_update_progress_tracks_completion(self, monitor, sample_state):
        """Verify progress updates track task completion."""
        monitor.start_workflow(sample_state)
        
        # Complete another task
        sample_state.completed_task_ids.append("task_2")
        sample_state.execution_plan[1].status = "complete"
        
        monitor.update_progress(sample_state)
        
        assert monitor.metrics["completed_tasks"] == 2
    
    def test_calculate_progress_percentage(self, monitor, sample_state):
        """Verify progress percentage calculation."""
        monitor.start_workflow(sample_state)
        monitor.update_progress(sample_state)
        
        progress = monitor.calculate_progress_percentage()
        
        # 1 completed out of 3 total = 33.33%
        assert progress == pytest.approx(33.33, rel=0.1)
    
    def test_calculate_eta_estimates_remaining_time(self, monitor, sample_state):
        """Verify ETA calculation based on progress."""
        monitor.start_workflow(sample_state)
        
        # Simulate some elapsed time
        import time
        time.sleep(0.2)
        
        monitor.update_progress(sample_state)
        
        eta = monitor.calculate_eta()
        
        # With 1/3 complete after 0.2s, ETA should be ~0.4s (2 remaining tasks)
        assert eta is not None
        assert eta > 0
    
    def test_calculate_eta_returns_none_when_no_progress(self, monitor, sample_state):
        """Verify ETA returns None when no tasks completed."""
        sample_state.completed_task_ids = []
        monitor.start_workflow(sample_state)
        
        eta = monitor.calculate_eta()
        
        assert eta is None
    
    def test_visualize_state_ascii_generates_diagram(self, monitor, sample_state):
        """Verify ASCII visualization generates readable diagram."""
        monitor.start_workflow(sample_state)
        
        ascii_diagram = monitor.visualize_state_ascii(sample_state)
        
        assert "WORKFLOW STATE VISUALIZATION" in ascii_diagram
        assert sample_state.thread_id in ascii_diagram
        assert "Initialize database" in ascii_diagram
        assert "✅" in ascii_diagram  # Completed task icon
        assert "🔄" in ascii_diagram  # In-progress task icon
        assert "⏳" in ascii_diagram  # Pending task icon
        assert ">>>" in ascii_diagram  # Current task indicator
    
    def test_visualize_state_ascii_marks_current_task(self, monitor, sample_state):
        """Verify ASCII visualization highlights current task."""
        monitor.start_workflow(sample_state)
        
        ascii_diagram = monitor.visualize_state_ascii(sample_state)
        
        # Current task (task_2) should be marked with >>>
        lines = ascii_diagram.split('\n')
        current_line = [line for line in lines if "Generate backend code" in line][0]
        assert ">>>" in current_line
    
    def test_visualize_state_json_generates_structure(self, monitor, sample_state):
        """Verify JSON visualization generates proper structure."""
        monitor.start_workflow(sample_state)
        
        json_state = monitor.visualize_state_json(sample_state)
        
        assert json_state["thread_id"] == sample_state.thread_id
        assert json_state["workflow_status"] == sample_state.workflow_status
        assert json_state["current_task_id"] == sample_state.current_task_id
        assert json_state["total_tasks"] == 3
        assert json_state["completed_count"] == 1
        assert len(json_state["tasks"]) == 3
    
    def test_visualize_state_json_marks_current_task(self, monitor, sample_state):
        """Verify JSON visualization marks current task."""
        monitor.start_workflow(sample_state)
        
        json_state = monitor.visualize_state_json(sample_state)
        
        current_tasks = [t for t in json_state["tasks"] if t["is_current"]]
        assert len(current_tasks) == 1
        assert current_tasks[0]["id"] == "task_2"
    
    def test_collect_metrics_returns_complete_summary(self, monitor, sample_state):
        """Verify metrics collection includes all data."""
        monitor.start_workflow(sample_state)
        
        # Simulate some activity
        monitor.log_agent_transition("planning", "backend", sample_state)
        import time
        time.sleep(0.1)
        monitor.log_agent_transition("backend", "supervisor", sample_state)
        
        error = ErrorRecord(
            agent="backend",
            task_id="task_2",
            error_type="recoverable",
            message="Test error",
            retry_count=1
        )
        monitor.log_error(error)
        
        monitor.end_workflow(sample_state)
        
        metrics = monitor.collect_metrics()
        
        assert "workflow_duration" in metrics
        assert "agent_avg_execution_times" in metrics
        assert "agent_total_execution_times" in metrics
        assert metrics["error_count"] == 1
        assert "backend" in metrics["agent_avg_execution_times"]
    
    def test_export_metrics_json_creates_file(self, monitor, sample_state):
        """Verify JSON export creates valid file."""
        monitor.start_workflow(sample_state)
        monitor.end_workflow(sample_state)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_path = Path(f.name)
        
        try:
            monitor.export_metrics_json(output_path)
            
            assert output_path.exists()
            
            # Verify JSON is valid
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert "workflow_duration" in data
            assert "total_tasks" in data
        finally:
            if output_path.exists():
                output_path.unlink()
    
    def test_export_metrics_csv_creates_file(self, monitor, sample_state):
        """Verify CSV export creates valid file."""
        monitor.start_workflow(sample_state)
        
        # Add some metrics
        monitor.log_agent_transition("planning", "backend", sample_state)
        import time
        time.sleep(0.05)
        monitor.log_agent_transition("backend", "supervisor", sample_state)
        
        monitor.end_workflow(sample_state)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            output_path = Path(f.name)
        
        try:
            monitor.export_metrics_csv(output_path)
            
            assert output_path.exists()
            
            # Verify CSV is valid
            with open(output_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) > 0
            assert "metric_type" in rows[0]
            assert "metric_name" in rows[0]
            assert "value" in rows[0]
        finally:
            if output_path.exists():
                output_path.unlink()
    
    def test_export_metrics_csv_includes_agent_times(self, monitor, sample_state):
        """Verify CSV export includes agent execution times."""
        monitor.start_workflow(sample_state)
        
        # Simulate backend execution
        monitor.log_agent_transition("supervisor", "backend", sample_state)
        import time
        time.sleep(0.05)
        monitor.log_agent_transition("backend", "supervisor", sample_state)
        
        monitor.end_workflow(sample_state)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            output_path = Path(f.name)
        
        try:
            monitor.export_metrics_csv(output_path)
            
            with open(output_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Check for backend execution time metrics
            agent_metrics = [
                r for r in rows
                if r["metric_type"] == "agent" and "backend" in r["metric_name"]
            ]
            assert len(agent_metrics) > 0
        finally:
            if output_path.exists():
                output_path.unlink()
    
    def test_thread_safety_with_concurrent_logging(self, monitor, sample_state):
        """Verify thread-safe logging operations."""
        import threading
        
        monitor.start_workflow(sample_state)
        
        def log_activity(agent_num):
            for i in range(10):
                monitor.log_agent_activity(
                    agent=f"agent_{agent_num}",
                    activity=f"Activity {i}",
                    task_id="task_1"
                )
        
        # Create multiple threads
        threads = [threading.Thread(target=log_activity, args=(i,)) for i in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify log file has all entries (50 total activities)
        with open(monitor.log_file, 'r') as f:
            logs = [json.loads(line) for line in f]
        
        activity_logs = [log for log in logs if "Activity" in log["message"]]
        assert len(activity_logs) == 50


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_handles_empty_execution_plan(self, monitor):
        """Verify monitor handles state with no tasks."""
        state = WorkflowState(
            thread_id="empty-workflow",
            user_requirements="Test",
            execution_plan=[],
        )
        
        monitor.start_workflow(state)
        
        progress = monitor.calculate_progress_percentage()
        assert progress == 0.0
        
        eta = monitor.calculate_eta()
        assert eta is None
    
    def test_visualize_returns_message_when_no_state(self, monitor):
        """Verify visualization handles missing state."""
        result = monitor.visualize_state_ascii()
        assert "No workflow state available" in result
        
        json_result = monitor.visualize_state_json()
        assert "error" in json_result
    
    def test_handles_multiple_agent_executions(self, monitor, sample_state):
        """Verify tracking of multiple executions of same agent."""
        monitor.start_workflow(sample_state)
        
        # First backend execution
        monitor.log_agent_transition("supervisor", "backend", sample_state)
        import time
        time.sleep(0.05)
        monitor.log_agent_transition("backend", "supervisor", sample_state)
        
        # Second backend execution (retry)
        monitor.log_agent_transition("supervisor", "backend", sample_state)
        time.sleep(0.05)
        monitor.log_agent_transition("backend", "supervisor", sample_state)
        
        # Should have two execution times recorded
        assert len(monitor.metrics["agent_execution_times"]["backend"]) == 2
    
    def test_progress_calculation_handles_all_complete(self, monitor, sample_state):
        """Verify progress shows 100% when all tasks complete."""
        # Mark all tasks complete
        for task in sample_state.execution_plan:
            task.status = "complete"
        sample_state.completed_task_ids = [t.id for t in sample_state.execution_plan]
        
        monitor.start_workflow(sample_state)
        monitor.update_progress(sample_state)
        
        progress = monitor.calculate_progress_percentage()
        assert progress == 100.0
