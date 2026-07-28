#!/usr/bin/env python3
"""
Demonstration of workflow monitoring and observability features.

This script simulates a workflow execution and demonstrates all monitoring
capabilities including logging, metrics collection, progress tracking, and
state visualization.
"""

import time
from pathlib import Path
from datetime import datetime

from workflow.monitoring import WorkflowMonitor
from workflow.models import WorkflowState, TaskDefinition, ErrorRecord


def simulate_workflow():
    """Simulate a complete workflow execution with monitoring."""
    
    print("="*70)
    print("WORKFLOW MONITORING DEMONSTRATION")
    print("="*70)
    print()
    
    # Create monitor
    log_file = Path("demo_workflow_execution.log")
    monitor = WorkflowMonitor(log_file=log_file, enable_console=True)
    
    # Define tasks
    tasks = [
        TaskDefinition(
            id="task_1",
            description="Initialize PostgreSQL database",
            agent="database",
            dependencies=[],
            estimated_duration="2 minutes",
            status="pending"
        ),
        TaskDefinition(
            id="task_2",
            description="Generate backend API code",
            agent="backend",
            dependencies=["task_1"],
            estimated_duration="5 minutes",
            status="pending"
        ),
        TaskDefinition(
            id="task_3",
            description="Generate frontend components",
            agent="frontend",
            dependencies=["task_1"],
            estimated_duration="4 minutes",
            status="pending"
        ),
        TaskDefinition(
            id="task_4",
            description="Run comprehensive tests",
            agent="testing",
            dependencies=["task_2", "task_3"],
            estimated_duration="3 minutes",
            status="pending"
        ),
        TaskDefinition(
            id="task_5",
            description="Deploy to Docker containers",
            agent="deployment",
            dependencies=["task_4"],
            estimated_duration="2 minutes",
            status="pending"
        ),
    ]
    
    # Create initial state
    state = WorkflowState(
        thread_id=f"demo-workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        user_requirements="Build a todo application with authentication",
        requirements_source="text",
        execution_plan=tasks,
        current_task_id=None,
        completed_task_ids=[],
        workflow_status="running",
    )
    
    # Start workflow
    monitor.start_workflow(state)
    
    # Simulate planning phase
    print("\n📋 Planning Phase")
    monitor.log_agent_transition("system", "planning", state, reason="Initialize workflow")
    monitor.log_agent_activity("planning", "Analyzing requirements", details={"requirement_count": 5})
    time.sleep(0.3)
    monitor.log_agent_activity("planning", "Creating task dependency graph")
    time.sleep(0.2)
    monitor.log_agent_transition("planning", "supervisor", state, reason="Planning complete")
    
    # Execute tasks
    for i, task in enumerate(tasks):
        print(f"\n📌 Executing Task {i+1}/{len(tasks)}: {task.description}")
        
        # Update state
        state.current_task_id = task.id
        task.status = "in_progress"
        
        # Supervisor routes to agent
        monitor.log_agent_transition("supervisor", task.agent, state, reason=f"Execute {task.id}")
        
        # Simulate agent work
        monitor.log_agent_activity(task.agent, f"Started: {task.description}", task_id=task.id)
        time.sleep(0.3)
        
        # Simulate potential error and retry for backend task
        if task.agent == "backend":
            error = ErrorRecord(
                agent=task.agent,
                task_id=task.id,
                error_type="recoverable",
                message="Type checking failed on 2 functions",
                retry_count=1
            )
            monitor.log_error(error)
            monitor.log_retry(task.agent, task.id, 1, "Fix type errors")
            time.sleep(0.2)
            monitor.log_agent_activity(task.agent, "Fixed type errors, regenerating code", task_id=task.id)
            time.sleep(0.2)
        
        # Simulate approval request for deployment
        if task.agent == "deployment":
            state.requires_approval = True
            state.approval_message = "Deploy to production environment?"
            monitor.log_approval_request(task.agent, state.approval_message)
            time.sleep(0.5)
            state.requires_approval = False
            monitor.log_agent_activity(task.agent, "Approval granted, proceeding with deployment", task_id=task.id)
            time.sleep(0.3)
        
        # Complete task
        monitor.log_agent_activity(task.agent, f"Completed: {task.description}", task_id=task.id)
        task.status = "complete"
        state.completed_task_ids.append(task.id)
        
        # Return to supervisor
        monitor.log_agent_transition(task.agent, "supervisor", state, reason="Task complete")
        
        # Update progress
        monitor.update_progress(state)
        time.sleep(0.2)
    
    # Complete workflow
    state.workflow_status = "complete"
    state.current_task_id = None
    monitor.end_workflow(state)
    
    # Display visualizations
    print("\n" + "="*70)
    print("WORKFLOW STATE VISUALIZATION")
    print("="*70)
    
    # ASCII visualization
    print(monitor.visualize_state_ascii(state))
    
    # Print summary
    monitor.print_summary()
    
    # Export metrics
    print("\n📤 Exporting Metrics...")
    monitor.export_metrics_json(Path("demo_metrics.json"))
    monitor.export_metrics_csv(Path("demo_metrics.csv"))
    
    # Show JSON state
    print("\n" + "="*70)
    print("JSON STATE REPRESENTATION (sample)")
    print("="*70)
    import json
    json_state = monitor.visualize_state_json(state)
    # Show first 3 tasks as sample
    json_state_sample = {
        "thread_id": json_state["thread_id"],
        "workflow_status": json_state["workflow_status"],
        "total_tasks": json_state["total_tasks"],
        "completed_count": json_state["completed_count"],
        "tasks": json_state["tasks"][:3],
        "error_count": json_state["error_count"],
    }
    print(json.dumps(json_state_sample, indent=2))
    
    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print(f"\n📁 Generated files:")
    print(f"  - Log file: {log_file}")
    print(f"  - Metrics JSON: demo_metrics.json")
    print(f"  - Metrics CSV: demo_metrics.csv")
    print()


if __name__ == "__main__":
    simulate_workflow()
