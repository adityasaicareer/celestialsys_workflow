# Monitoring Quick Start Guide

## 5-Minute Setup

### 1. Import and Initialize

```python
from pathlib import Path
from workflow.monitoring import WorkflowMonitor

# Create monitor
monitor = WorkflowMonitor(
    log_file=Path("workflow.log"),
    enable_console=True
)
```

### 2. Start Monitoring

```python
from workflow.models import WorkflowState

# At workflow start
monitor.start_workflow(state)
```

### 3. Log Events

```python
# Agent transitions
monitor.log_agent_transition("planning", "backend", state, "Task ready")

# Agent activities
monitor.log_agent_activity("backend", "Generating code", "task_1")

# Errors
monitor.log_error(error_record)

# Progress
monitor.update_progress(state)
```

### 4. End and Export

```python
# At workflow end
monitor.end_workflow(state)

# Print summary
monitor.print_summary()

# Export metrics
monitor.export_metrics_json(Path("metrics.json"))
monitor.export_metrics_csv(Path("metrics.csv"))
```

## Console Output

```
============================================================
🚀 WORKFLOW STARTED: workflow-123
📋 Total Tasks: 5
============================================================

🔄 planning → backend (Task ready)
  ⚙️  backend: Generating code

📊 Progress: [████████░░░░░░░░░░░░] 40.0% (2/5 tasks)
⏱️  ETA: 2.6s

============================================================
✅ WORKFLOW COMPLETED: workflow-123
📊 Status: complete
⏱️  Duration: 4.3s
✔️  Completed: 5/5
============================================================
```

## Visualization

```python
# ASCII diagram
print(monitor.visualize_state_ascii(state))

# JSON representation
json_state = monitor.visualize_state_json(state)
```

## Run Demo

```bash
python3 demo_monitoring.py
```

See `MONITORING_GUIDE.md` for complete documentation.
