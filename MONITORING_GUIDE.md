# Workflow Monitoring and Observability Guide

## Overview

The `workflow/monitoring.py` module provides comprehensive monitoring and observability infrastructure for the supervised agentic workflow system. It implements all requirements from **Requirement 15: Monitoring and Observability**.

## Features

### 1. Structured Logging
- **JSON-formatted logs** for machine parsing
- **Agent transition tracking** with timestamps
- **Agent activity logging** with intermediate results
- **Error logging** with full tracebacks
- **Thread-safe** logging for concurrent operations

### 2. Metrics Collection
- **Workflow duration** tracking
- **Agent execution times** (average and total per agent)
- **Retry counts** per agent
- **Task completion tracking** (total, completed, failed)
- **Error and approval counts**
- **Agent transition history**

### 3. Progress Tracking
- **Real-time progress updates** to console
- **Progress percentage calculation**
- **ETA estimation** based on current progress
- **Visual progress bars** in console output

### 4. State Visualization
- **ASCII diagram** showing workflow state graph
- **JSON representation** for programmatic access
- **Current task highlighting**
- **Task status indicators** (pending, in-progress, complete, failed)

### 5. Metrics Export
- **JSON export** for structured data analysis
- **CSV export** for spreadsheet compatibility
- **Customizable output paths**

## Usage

### Basic Setup

```python
from pathlib import Path
from workflow.monitoring import WorkflowMonitor
from workflow.models import WorkflowState

# Create monitor
monitor = WorkflowMonitor(
    log_file=Path("workflow_execution.log"),
    log_level=logging.INFO,
    enable_console=True
)

# Start monitoring workflow
monitor.start_workflow(state)
```

### Logging Agent Transitions

```python
# Log transition from one agent to another
monitor.log_agent_transition(
    from_agent="planning",
    to_agent="backend",
    state=current_state,
    reason="Task ready for execution"
)
```

### Logging Agent Activities

```python
# Log agent activity
monitor.log_agent_activity(
    agent="backend",
    activity="Generating API endpoints",
    task_id="task_2",
    details={"endpoint_count": 5}
)
```

### Logging Errors and Retries

```python
from workflow.models import ErrorRecord

# Log error
error = ErrorRecord(
    agent="backend",
    task_id="task_2",
    error_type="recoverable",
    message="Type checking failed",
    retry_count=1
)
monitor.log_error(error)

# Log retry attempt
monitor.log_retry(
    agent="backend",
    task_id="task_2",
    attempt=2,
    reason="Fix type errors"
)
```

### Progress Tracking

```python
# Update progress (shows progress bar and ETA)
monitor.update_progress(state)

# Calculate progress percentage
progress = monitor.calculate_progress_percentage()
print(f"Progress: {progress:.1f}%")

# Calculate estimated time to completion
eta_seconds = monitor.calculate_eta()
```

### State Visualization

```python
# Generate ASCII diagram
ascii_diagram = monitor.visualize_state_ascii(state)
print(ascii_diagram)

# Generate JSON representation
json_state = monitor.visualize_state_json(state)
print(json.dumps(json_state, indent=2))
```

### Metrics Collection and Export

```python
# Collect all metrics
metrics = monitor.collect_metrics()

# Export to JSON
monitor.export_metrics_json(Path("metrics.json"))

# Export to CSV
monitor.export_metrics_csv(Path("metrics.csv"))

# Print summary to console
monitor.print_summary()
```

### Complete Workflow Example

```python
from workflow.monitoring import WorkflowMonitor
from workflow.models import WorkflowState, TaskDefinition

# Initialize monitor
monitor = WorkflowMonitor(
    log_file=Path("workflow.log"),
    enable_console=True
)

# Create workflow state
state = WorkflowState(
    thread_id="workflow-123",
    user_requirements="Build a todo app",
    execution_plan=[...],  # Your tasks
)

# Start workflow
monitor.start_workflow(state)

# Execute workflow with monitoring
for task in state.execution_plan:
    # Transition to agent
    monitor.log_agent_transition("supervisor", task.agent, state)
    
    # Execute task (your implementation)
    monitor.log_agent_activity(task.agent, f"Executing {task.description}")
    # ... task execution logic ...
    
    # Update progress
    state.completed_task_ids.append(task.id)
    monitor.update_progress(state)

# End workflow
monitor.end_workflow(state)

# Display summary
monitor.print_summary()

# Export metrics
monitor.export_metrics_json(Path("metrics.json"))
monitor.export_metrics_csv(Path("metrics.csv"))
```

## Console Output Examples

### Workflow Start
```
============================================================
🚀 WORKFLOW STARTED: demo-workflow-20260726-230727
📋 Total Tasks: 5
============================================================
```

### Agent Transitions
```
🔄 planning → supervisor (Planning complete)
🔄 supervisor → backend (Execute task_2)
```

### Agent Activities
```
  ⚙️  backend: Generating API endpoints
  ⚙️  backend: Running type checks
```

### Progress Updates
```
📊 Progress: [████████████████░░░░░░░░░░░░░░░░░░░░░░░░] 40.0% (2/5 tasks)
⏱️  ETA: 2.6s
```

### Error Notifications
```
  ❌ ERROR in backend: Type checking failed on 2 functions
  🔄 Retry #1 - backend: Fix type errors
```

### Approval Requests
```
⏸️  HUMAN APPROVAL REQUIRED - deployment
   Message: Deploy to production environment?
```

### Workflow Completion
```
============================================================
✅ WORKFLOW COMPLETED: demo-workflow-20260726-230727
📊 Status: complete
⏱️  Duration: 4.3s
✔️  Completed: 5/5
============================================================
```

## ASCII State Visualization Example

```
======================================================================
WORKFLOW STATE VISUALIZATION
======================================================================
Thread ID: demo-workflow-20260726-230727
Status: running
Current Task: task_2

Task Execution Flow:
----------------------------------------------------------------------
    1. ✅ [database] Initialize PostgreSQL database
>>> 2. 🔄 [backend] Generate backend API code (deps: task_1)
    3. ⏳ [frontend] Generate frontend components (deps: task_1)
    4. ⏳ [testing] Run comprehensive tests (deps: task_2, task_3)
    5. ⏳ [deployment] Deploy to Docker containers (deps: task_4)
----------------------------------------------------------------------
Completed: 1/5
Errors: 0
Retries: 0
======================================================================
```

Legend:
- `✅` = Complete
- `🔄` = In Progress
- `⏳` = Pending
- `❌` = Failed
- `>>>` = Current task

## JSON Log Format

Each log entry is a JSON object with the following structure:

```json
{
  "timestamp": "2026-07-26T23:07:27.901008",
  "level": "INFO",
  "logger": "workflow_monitor",
  "message": "Agent transition: planning -> backend",
  "agent": "planning",
  "transition": {
    "from": "planning",
    "to": "backend",
    "reason": "Task ready"
  },
  "state_info": {
    "current_task": "task_2",
    "completed_tasks": 1,
    "workflow_status": "running"
  }
}
```

## Metrics JSON Structure

```json
{
  "workflow_start_time": "2026-07-26T23:07:53.358098",
  "workflow_end_time": "2026-07-26T23:07:57.628485",
  "workflow_duration": 4.270387,
  "agent_execution_times": {
    "backend": [0.716853, 0.512341],
    "frontend": [0.301234]
  },
  "agent_avg_execution_times": {
    "backend": 0.614597,
    "frontend": 0.301234
  },
  "agent_total_execution_times": {
    "backend": 1.229194,
    "frontend": 0.301234
  },
  "retry_counts": {
    "backend": 1
  },
  "total_tasks": 5,
  "completed_tasks": 5,
  "failed_tasks": 0,
  "error_count": 1,
  "approval_count": 1,
  "agent_transitions": [
    {
      "timestamp": "2026-07-26T23:07:27.901136",
      "from_agent": "planning",
      "to_agent": "backend",
      "task_id": "task_2",
      "reason": "Task ready",
      "workflow_status": "running"
    }
  ]
}
```

## Metrics CSV Format

```csv
metric_type,metric_name,value,unit
workflow,duration,4.270387,seconds
workflow,total_tasks,5,count
workflow,completed_tasks,5,count
workflow,failed_tasks,0,count
workflow,error_count,1,count
agent,backend_avg_execution_time,0.614597,seconds
agent,backend_total_execution_time,1.229194,seconds
retry,backend_retry_count,1,count
```

## Thread Safety

The `WorkflowMonitor` class is thread-safe for concurrent logging operations:

```python
import threading

def agent_work(monitor, agent_num):
    for i in range(10):
        monitor.log_agent_activity(
            agent=f"agent_{agent_num}",
            activity=f"Processing item {i}"
        )

# Create multiple threads
threads = [
    threading.Thread(target=agent_work, args=(monitor, i))
    for i in range(5)
]

for t in threads:
    t.start()
for t in threads:
    t.join()
```

All logging operations use internal locking to ensure consistency.

## Integration with Workflow System

To integrate monitoring into the workflow system:

1. **Initialize monitor** when creating the workflow
2. **Call `start_workflow`** at workflow initialization
3. **Log transitions** in the supervisor routing logic
4. **Log activities** in each specialist agent
5. **Update progress** after each task completion
6. **Call `end_workflow`** when workflow completes
7. **Export metrics** for analysis

Example integration in supervisor agent:

```python
class SupervisorAgent:
    def __init__(self, monitor: WorkflowMonitor):
        self.monitor = monitor
    
    def route_next_agent(self, state: WorkflowState) -> str:
        current_agent = self._get_current_agent(state)
        next_agent = self._determine_next_agent(state)
        
        # Log transition
        self.monitor.log_agent_transition(
            from_agent=current_agent,
            to_agent=next_agent,
            state=state,
            reason=self._get_transition_reason(state)
        )
        
        return next_agent
```

## Performance Considerations

- **Log file size**: Use log rotation for long-running workflows
- **Metrics storage**: Metrics are kept in memory; export periodically for long workflows
- **Console output**: Disable with `enable_console=False` for production
- **Thread safety**: Minimal locking overhead for high-throughput logging

## Requirements Mapping

This module validates the following requirements from **Requirement 15**:

| Requirement | Implementation |
|------------|----------------|
| 15.1 - Log agent transitions | `log_agent_transition()` |
| 15.2 - Provide progress updates | `update_progress()`, console output |
| 15.3 - Log agent activity | `log_agent_activity()` |
| 15.4 - Calculate ETA | `calculate_eta()` |
| 15.5 - Visualize state graph | `visualize_state_ascii()`, `visualize_state_json()` |
| 15.6 - Expose metrics | `collect_metrics()`, `export_metrics_json()`, `export_metrics_csv()` |

## Demo Script

Run the demonstration script to see all features in action:

```bash
python3 demo_monitoring.py
```

This will:
- Simulate a complete workflow execution
- Display real-time progress updates
- Show ASCII and JSON state visualizations
- Export metrics to JSON and CSV
- Print comprehensive execution summary

Generated files:
- `demo_workflow_execution.log` - Structured JSON logs
- `demo_metrics.json` - Complete metrics in JSON format
- `demo_metrics.csv` - Metrics in CSV format

## Testing

Run the comprehensive test suite:

```bash
python3 -m pytest tests/test_monitoring.py -v
```

The test suite includes:
- Structured logging tests
- Metrics collection tests
- Progress tracking tests
- State visualization tests
- Metrics export tests
- Thread safety tests
- Edge case handling

All 28 tests validate correct behavior across various scenarios.
