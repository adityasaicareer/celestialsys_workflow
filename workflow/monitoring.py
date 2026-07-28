"""
Monitoring and observability infrastructure for the workflow system.

This module provides structured logging, metrics collection, progress tracking,
and workflow state visualization for debugging and performance analysis.
"""

import json
import logging
import csv
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from workflow.models import WorkflowState, ErrorRecord, TaskDefinition


# Configure structured logging
class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "agent"):
            log_data["agent"] = record.agent
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "transition"):
            log_data["transition"] = record.transition
        if hasattr(record, "state_info"):
            log_data["state_info"] = record.state_info
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


class WorkflowMonitor:
    """
    Comprehensive monitoring and observability for workflow execution.
    
    Provides:
    - Structured logging for agent transitions and activities
    - Metrics collection (durations, retry counts, task counts)
    - Progress tracking and ETA calculation
    - Workflow state visualization (ASCII and JSON)
    - Metrics export (JSON, CSV)
    """
    
    def __init__(
        self,
        log_file: Optional[Path] = None,
        log_level: int = logging.INFO,
        enable_console: bool = True
    ):
        """
        Initialize workflow monitor.
        
        Args:
            log_file: Path to log file (optional)
            log_level: Logging level
            enable_console: Whether to log to console
        """
        self.log_file = log_file or Path("workflow_execution.log")
        self.log_level = log_level
        self.enable_console = enable_console
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Metrics storage
        self.metrics: Dict[str, Any] = {
            "workflow_start_time": None,
            "workflow_end_time": None,
            "workflow_duration": None,
            "agent_execution_times": defaultdict(list),  # agent -> [durations]
            "agent_start_times": {},  # agent -> start_time
            "retry_counts": defaultdict(int),  # agent -> count
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "agent_transitions": [],  # List of transition records
            "error_count": 0,
            "approval_count": 0,
        }
        
        # Progress tracking
        self.current_state: Optional[WorkflowState] = None
        self.task_history: List[Tuple[str, datetime, str]] = []  # (task_id, time, status)
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure logging handlers and formatters."""
        # Create logger
        self.logger = logging.getLogger("workflow_monitor")
        self.logger.setLevel(self.log_level)
        self.logger.handlers.clear()  # Remove any existing handlers
        
        # File handler with JSON formatting
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file, mode='a')
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)
        
        # Console handler with readable formatting
        if self.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            console_format = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
    
    def start_workflow(self, state: WorkflowState) -> None:
        """
        Log workflow start and initialize metrics.
        
        Args:
            state: Initial workflow state
        """
        with self._lock:
            self.metrics["workflow_start_time"] = datetime.now()
            self.current_state = state
            self.metrics["total_tasks"] = len(state.execution_plan)
            
        self.logger.info(
            f"Workflow started: {state.thread_id}",
            extra={
                "agent": "workflow_system",
                "state_info": {
                    "thread_id": state.thread_id,
                    "total_tasks": len(state.execution_plan),
                    "requirements_source": state.requirements_source,
                }
            }
        )
        
        # Console progress update
        if self.enable_console:
            print("\n" + "="*60)
            print(f"🚀 WORKFLOW STARTED: {state.thread_id}")
            print(f"📋 Total Tasks: {len(state.execution_plan)}")
            print("="*60 + "\n")
    
    def end_workflow(self, state: WorkflowState) -> None:
        """
        Log workflow completion and finalize metrics.
        
        Args:
            state: Final workflow state
        """
        with self._lock:
            self.metrics["workflow_end_time"] = datetime.now()
            start_time = self.metrics["workflow_start_time"]
            if start_time:
                duration = self.metrics["workflow_end_time"] - start_time
                self.metrics["workflow_duration"] = duration.total_seconds()
            
            self.current_state = state
            self.metrics["completed_tasks"] = len(state.completed_task_ids)
            self.metrics["failed_tasks"] = sum(
                1 for task in state.execution_plan if task.status == "failed"
            )
        
        self.logger.info(
            f"Workflow completed: {state.thread_id}",
            extra={
                "agent": "workflow_system",
                "state_info": {
                    "thread_id": state.thread_id,
                    "status": state.workflow_status,
                    "completed_tasks": len(state.completed_task_ids),
                    "duration": self.metrics["workflow_duration"],
                }
            }
        )
        
        # Console progress update
        if self.enable_console:
            print("\n" + "="*60)
            print(f"✅ WORKFLOW COMPLETED: {state.thread_id}")
            print(f"📊 Status: {state.workflow_status}")
            print(f"⏱️  Duration: {self._format_duration(self.metrics['workflow_duration'])}")
            print(f"✔️  Completed: {len(state.completed_task_ids)}/{len(state.execution_plan)}")
            print("="*60 + "\n")
    
    def log_agent_transition(
        self,
        from_agent: str,
        to_agent: str,
        state: WorkflowState,
        reason: Optional[str] = None
    ) -> None:
        """
        Log agent-to-agent transition with timestamps and state info.
        
        Args:
            from_agent: Source agent name
            to_agent: Destination agent name
            state: Current workflow state
            reason: Optional reason for transition
        """
        transition_time = datetime.now()
        
        with self._lock:
            # Record transition
            transition_record = {
                "timestamp": transition_time.isoformat(),
                "from_agent": from_agent,
                "to_agent": to_agent,
                "task_id": state.current_task_id,
                "reason": reason,
                "workflow_status": state.workflow_status,
            }
            self.metrics["agent_transitions"].append(transition_record)
            
            # Track agent execution time for completed agent
            if from_agent in self.metrics["agent_start_times"]:
                start_time = self.metrics["agent_start_times"][from_agent]
                duration = (transition_time - start_time).total_seconds()
                self.metrics["agent_execution_times"][from_agent].append(duration)
                del self.metrics["agent_start_times"][from_agent]
            
            # Start timing for new agent
            if to_agent != "complete":
                self.metrics["agent_start_times"][to_agent] = transition_time
            
            self.current_state = state
        
        self.logger.info(
            f"Agent transition: {from_agent} -> {to_agent}",
            extra={
                "agent": from_agent,
                "transition": {
                    "from": from_agent,
                    "to": to_agent,
                    "reason": reason,
                },
                "state_info": {
                    "current_task": state.current_task_id,
                    "completed_tasks": len(state.completed_task_ids),
                    "workflow_status": state.workflow_status,
                }
            }
        )
        
        # Console progress update
        if self.enable_console:
            print(f"🔄 {from_agent} → {to_agent}" + (f" ({reason})" if reason else ""))
    
    def log_agent_activity(
        self,
        agent: str,
        activity: str,
        task_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log agent activity and intermediate results.
        
        Args:
            agent: Agent name
            activity: Activity description
            task_id: Task ID (optional)
            details: Additional activity details (optional)
        """
        self.logger.info(
            f"Agent activity: {agent} - {activity}",
            extra={
                "agent": agent,
                "task_id": task_id,
                "state_info": details or {}
            }
        )
        
        # Console update for important activities
        if self.enable_console and any(
            keyword in activity.lower()
            for keyword in ["started", "completed", "failed", "generating", "testing"]
        ):
            print(f"  ⚙️  {agent}: {activity}")
    
    def log_error(self, error: ErrorRecord) -> None:
        """
        Log error with detailed information.
        
        Args:
            error: Error record to log
        """
        with self._lock:
            self.metrics["error_count"] += 1
            self.metrics["retry_counts"][error.agent] = error.retry_count
        
        self.logger.error(
            f"Error in {error.agent}: {error.message}",
            extra={
                "agent": error.agent,
                "task_id": error.task_id,
                "error_type": error.error_type,
                "state_info": {
                    "retry_count": error.retry_count,
                    "traceback": error.traceback,
                }
            }
        )
        
        # Console error notification
        if self.enable_console:
            print(f"  ❌ ERROR in {error.agent}: {error.message}")
    
    def log_retry(self, agent: str, task_id: str, attempt: int, reason: str) -> None:
        """
        Log retry attempt.
        
        Args:
            agent: Agent name
            task_id: Task ID
            attempt: Retry attempt number
            reason: Reason for retry
        """
        with self._lock:
            self.metrics["retry_counts"][agent] = attempt
        
        self.logger.warning(
            f"Retry attempt {attempt} for {agent}",
            extra={
                "agent": agent,
                "task_id": task_id,
                "state_info": {
                    "attempt": attempt,
                    "reason": reason,
                }
            }
        )
        
        if self.enable_console:
            print(f"  🔄 Retry #{attempt} - {agent}: {reason}")
    
    def log_approval_request(self, agent: str, message: str) -> None:
        """
        Log human approval request.
        
        Args:
            agent: Agent requesting approval
            message: Approval message
        """
        with self._lock:
            self.metrics["approval_count"] += 1
        
        self.logger.warning(
            f"Human approval required: {agent}",
            extra={
                "agent": agent,
                "state_info": {"message": message}
            }
        )
        
        if self.enable_console:
            print(f"\n⏸️  HUMAN APPROVAL REQUIRED - {agent}")
            print(f"   Message: {message}\n")
    
    def update_progress(self, state: WorkflowState) -> None:
        """
        Update progress tracking and display console update.
        
        Args:
            state: Current workflow state
        """
        with self._lock:
            self.current_state = state
            self.metrics["completed_tasks"] = len(state.completed_task_ids)
            
            # Track task completion
            if state.current_task_id:
                current_task = next(
                    (t for t in state.execution_plan if t.id == state.current_task_id),
                    None
                )
                if current_task:
                    self.task_history.append(
                        (state.current_task_id, datetime.now(), current_task.status)
                    )
        
        # Calculate progress percentage
        progress_pct = self.calculate_progress_percentage()
        eta = self.calculate_eta()
        
        # Console progress bar
        if self.enable_console:
            completed = len(state.completed_task_ids)
            total = len(state.execution_plan)
            bar_length = 40
            filled = int(bar_length * progress_pct / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            print(f"\n📊 Progress: [{bar}] {progress_pct:.1f}% ({completed}/{total} tasks)")
            if eta:
                print(f"⏱️  ETA: {self._format_duration(eta)}")
            print()
    
    def calculate_progress_percentage(self) -> float:
        """
        Calculate workflow completion percentage.
        
        Returns:
            Progress percentage (0-100)
        """
        with self._lock:
            if not self.current_state or not self.current_state.execution_plan:
                return 0.0
            
            completed = len(self.current_state.completed_task_ids)
            total = len(self.current_state.execution_plan)
            
            if total == 0:
                return 0.0
            
            return (completed / total) * 100
    
    def calculate_eta(self) -> Optional[float]:
        """
        Calculate estimated time to completion based on current progress.
        
        Returns:
            Estimated seconds remaining, or None if cannot estimate
        """
        with self._lock:
            if not self.current_state or not self.metrics["workflow_start_time"]:
                return None
            
            completed = len(self.current_state.completed_task_ids)
            total = len(self.current_state.execution_plan)
            
            if completed == 0 or total == 0:
                return None
            
            elapsed = (datetime.now() - self.metrics["workflow_start_time"]).total_seconds()
            avg_time_per_task = elapsed / completed
            remaining_tasks = total - completed
            
            return avg_time_per_task * remaining_tasks
    
    def visualize_state_ascii(self, state: Optional[WorkflowState] = None) -> str:
        """
        Generate ASCII diagram of workflow state graph.
        
        Args:
            state: Workflow state (uses current if not provided)
            
        Returns:
            ASCII diagram showing current position in workflow
        """
        state = state or self.current_state
        if not state:
            return "No workflow state available"
        
        lines = []
        lines.append("\n" + "="*70)
        lines.append("WORKFLOW STATE VISUALIZATION")
        lines.append("="*70)
        lines.append(f"Thread ID: {state.thread_id}")
        lines.append(f"Status: {state.workflow_status}")
        lines.append(f"Current Task: {state.current_task_id or 'None'}")
        lines.append("")
        lines.append("Task Execution Flow:")
        lines.append("-" * 70)
        
        # Show task progression
        for i, task in enumerate(state.execution_plan, 1):
            status_icon = self._get_status_icon(task.status)
            is_current = task.id == state.current_task_id
            
            # Format line
            prefix = ">>> " if is_current else "    "
            line = f"{prefix}{i}. {status_icon} [{task.agent}] {task.description}"
            
            if task.dependencies:
                line += f" (deps: {', '.join(task.dependencies)})"
            
            lines.append(line)
        
        lines.append("-" * 70)
        lines.append(f"Completed: {len(state.completed_task_ids)}/{len(state.execution_plan)}")
        lines.append(f"Errors: {len(state.error_log)}")
        lines.append(f"Retries: {sum(state.retry_counts.values())}")
        lines.append("="*70 + "\n")
        
        return "\n".join(lines)
    
    def visualize_state_json(self, state: Optional[WorkflowState] = None) -> Dict[str, Any]:
        """
        Generate JSON representation of workflow state graph.
        
        Args:
            state: Workflow state (uses current if not provided)
            
        Returns:
            JSON-serializable dict with workflow state
        """
        state = state or self.current_state
        if not state:
            return {"error": "No workflow state available"}
        
        return {
            "thread_id": state.thread_id,
            "workflow_status": state.workflow_status,
            "current_task_id": state.current_task_id,
            "completed_task_ids": state.completed_task_ids,
            "total_tasks": len(state.execution_plan),
            "completed_count": len(state.completed_task_ids),
            "tasks": [
                {
                    "id": task.id,
                    "description": task.description,
                    "agent": task.agent,
                    "status": task.status,
                    "dependencies": task.dependencies,
                    "is_current": task.id == state.current_task_id,
                }
                for task in state.execution_plan
            ],
            "error_count": len(state.error_log),
            "retry_counts": dict(state.retry_counts),
            "requires_approval": state.requires_approval,
            "approval_message": state.approval_message,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        }
    
    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect all workflow metrics.
        
        Returns:
            Dict containing all collected metrics
        """
        with self._lock:
            # Calculate aggregate statistics
            metrics_summary = dict(self.metrics)
            
            # Calculate average execution times per agent
            metrics_summary["agent_avg_execution_times"] = {
                agent: sum(times) / len(times) if times else 0
                for agent, times in self.metrics["agent_execution_times"].items()
            }
            
            # Calculate total execution time per agent
            metrics_summary["agent_total_execution_times"] = {
                agent: sum(times)
                for agent, times in self.metrics["agent_execution_times"].items()
            }
            
            # Format timestamps
            if metrics_summary["workflow_start_time"]:
                metrics_summary["workflow_start_time"] = (
                    metrics_summary["workflow_start_time"].isoformat()
                )
            if metrics_summary["workflow_end_time"]:
                metrics_summary["workflow_end_time"] = (
                    metrics_summary["workflow_end_time"].isoformat()
                )
            
            # Clean up defaultdicts for JSON serialization
            metrics_summary["agent_execution_times"] = dict(
                metrics_summary["agent_execution_times"]
            )
            metrics_summary["retry_counts"] = dict(metrics_summary["retry_counts"])
            
            # Convert agent_start_times datetime objects to ISO format
            metrics_summary["agent_start_times"] = {
                agent: start_time.isoformat()
                for agent, start_time in metrics_summary["agent_start_times"].items()
            }
            
            return metrics_summary
    
    def export_metrics_json(self, output_path: Path) -> None:
        """
        Export metrics to JSON file.
        
        Args:
            output_path: Path to output JSON file
        """
        metrics = self.collect_metrics()
        
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        self.logger.info(f"Metrics exported to JSON: {output_path}")
        
        if self.enable_console:
            print(f"📊 Metrics exported to: {output_path}")
    
    def export_metrics_csv(self, output_path: Path) -> None:
        """
        Export metrics to CSV file.
        
        Args:
            output_path: Path to output CSV file
        """
        metrics = self.collect_metrics()
        
        # Flatten metrics for CSV format
        rows = []
        
        # Overall metrics
        rows.append({
            "metric_type": "workflow",
            "metric_name": "duration",
            "value": metrics.get("workflow_duration", 0),
            "unit": "seconds"
        })
        rows.append({
            "metric_type": "workflow",
            "metric_name": "total_tasks",
            "value": metrics.get("total_tasks", 0),
            "unit": "count"
        })
        rows.append({
            "metric_type": "workflow",
            "metric_name": "completed_tasks",
            "value": metrics.get("completed_tasks", 0),
            "unit": "count"
        })
        rows.append({
            "metric_type": "workflow",
            "metric_name": "failed_tasks",
            "value": metrics.get("failed_tasks", 0),
            "unit": "count"
        })
        rows.append({
            "metric_type": "workflow",
            "metric_name": "error_count",
            "value": metrics.get("error_count", 0),
            "unit": "count"
        })
        
        # Agent execution times
        for agent, avg_time in metrics.get("agent_avg_execution_times", {}).items():
            rows.append({
                "metric_type": "agent",
                "metric_name": f"{agent}_avg_execution_time",
                "value": avg_time,
                "unit": "seconds"
            })
        
        for agent, total_time in metrics.get("agent_total_execution_times", {}).items():
            rows.append({
                "metric_type": "agent",
                "metric_name": f"{agent}_total_execution_time",
                "value": total_time,
                "unit": "seconds"
            })
        
        # Retry counts
        for agent, count in metrics.get("retry_counts", {}).items():
            rows.append({
                "metric_type": "retry",
                "metric_name": f"{agent}_retry_count",
                "value": count,
                "unit": "count"
            })
        
        # Write CSV
        with open(output_path, 'w', newline='') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        self.logger.info(f"Metrics exported to CSV: {output_path}")
        
        if self.enable_console:
            print(f"📊 Metrics exported to: {output_path}")
    
    def _get_status_icon(self, status: str) -> str:
        """Get icon for task status."""
        icons = {
            "pending": "⏳",
            "in_progress": "🔄",
            "complete": "✅",
            "failed": "❌",
        }
        return icons.get(status, "❓")
    
    def _format_duration(self, seconds: Optional[float]) -> str:
        """Format duration in human-readable format."""
        if seconds is None:
            return "Unknown"
        
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}min"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def print_summary(self) -> None:
        """Print comprehensive workflow execution summary."""
        if not self.enable_console:
            return
        
        metrics = self.collect_metrics()
        
        print("\n" + "="*70)
        print("WORKFLOW EXECUTION SUMMARY")
        print("="*70)
        
        # Overall metrics
        print("\n📊 Overall Metrics:")
        print(f"  Duration: {self._format_duration(metrics.get('workflow_duration'))}")
        print(f"  Tasks: {metrics.get('completed_tasks')}/{metrics.get('total_tasks')}")
        print(f"  Failed: {metrics.get('failed_tasks')}")
        print(f"  Errors: {metrics.get('error_count')}")
        print(f"  Approvals: {metrics.get('approval_count')}")
        
        # Agent performance
        if metrics.get("agent_avg_execution_times"):
            print("\n⚙️  Agent Performance:")
            for agent, avg_time in sorted(
                metrics["agent_avg_execution_times"].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                total_time = metrics["agent_total_execution_times"].get(agent, 0)
                print(f"  {agent}:")
                print(f"    - Avg: {self._format_duration(avg_time)}")
                print(f"    - Total: {self._format_duration(total_time)}")
        
        # Retry statistics
        if metrics.get("retry_counts"):
            print("\n🔄 Retry Statistics:")
            for agent, count in sorted(
                metrics["retry_counts"].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                print(f"  {agent}: {count} retries")
        
        # Transition count
        print(f"\n🔄 Agent Transitions: {len(metrics.get('agent_transitions', []))}")
        
        print("="*70 + "\n")
