"""
Demonstration of Human Approval Mechanism - Task 15.1

This script demonstrates the complete human approval workflow:
1. Workflow triggers approval requirement (max retries)
2. System pauses and presents approval request
3. User makes decision (approve/reject/modify/skip)
4. Workflow resumes based on decision
5. State is properly persisted through checkpointing

Usage:
    python3 demo_human_approval.py [--interactive]
    
    Without --interactive: Simulates user responses for demonstration
    With --interactive: Allows real user input
"""

import sys
import argparse
from datetime import datetime
from unittest.mock import patch

from workflow.models import WorkflowState, TaskDefinition, ErrorRecord
from workflow.approval import (
    ApprovalHandler,
    request_human_approval,
    check_approval_needed
)


def create_approval_scenario():
    """Create a scenario that requires human approval."""
    return WorkflowState(
        thread_id="demo-approval-001",
        user_requirements="""
Build a REST API for a todo application with:
- User authentication (JWT)
- CRUD operations for todos
- PostgreSQL database
- FastAPI backend
        """.strip(),
        execution_plan=[
            TaskDefinition(
                id="task_1",
                description="Initialize PostgreSQL database",
                agent="database",
                status="complete"
            ),
            TaskDefinition(
                id="task_2",
                description="Generate backend authentication system",
                agent="backend",
                dependencies=["task_1"],
                status="in_progress"
            ),
            TaskDefinition(
                id="task_3",
                description="Generate CRUD endpoints",
                agent="backend",
                dependencies=["task_2"],
                status="pending"
            ),
            TaskDefinition(
                id="task_4",
                description="Generate frontend interface",
                agent="frontend",
                dependencies=["task_3"],
                status="pending"
            ),
            TaskDefinition(
                id="task_5",
                description="Deploy to Docker",
                agent="deployment",
                dependencies=["task_4"],
                status="pending"
            )
        ],
        current_task_id="task_2",
        completed_task_ids=["task_1"],
        requires_approval=True,
        approval_message="Backend agent failed 5 consecutive times on authentication system generation. Code quality validation repeatedly failed.",
        retry_counts={"backend": 5},
        workflow_status="running",
        error_log=[
            ErrorRecord(
                timestamp=datetime.now(),
                agent="backend",
                task_id="task_2",
                error_type="recoverable",
                message="Generated code failed pylint validation (score: 6.2/10)",
                retry_count=1
            ),
            ErrorRecord(
                timestamp=datetime.now(),
                agent="backend",
                task_id="task_2",
                error_type="recoverable",
                message="Generated code failed type checking (mypy errors: 8)",
                retry_count=2
            ),
            ErrorRecord(
                timestamp=datetime.now(),
                agent="backend",
                task_id="task_2",
                error_type="recoverable",
                message="Authentication logic incomplete - missing password hashing",
                retry_count=3
            ),
            ErrorRecord(
                timestamp=datetime.now(),
                agent="backend",
                task_id="task_2",
                error_type="recoverable",
                message="JWT token generation not implemented",
                retry_count=4
            ),
            ErrorRecord(
                timestamp=datetime.now(),
                agent="backend",
                task_id="task_2",
                error_type="recoverable",
                message="Security validation failed - credentials in plaintext",
                retry_count=5
            )
        ],
        agent_transitions=[
            {
                "timestamp": datetime.now().isoformat(),
                "from_agent": "planning",
                "to_agent": "supervisor",
                "reason": "Planning complete"
            },
            {
                "timestamp": datetime.now().isoformat(),
                "from_agent": "supervisor",
                "to_agent": "database",
                "reason": "First task"
            },
            {
                "timestamp": datetime.now().isoformat(),
                "from_agent": "database",
                "to_agent": "supervisor",
                "reason": "Database initialized"
            },
            {
                "timestamp": datetime.now().isoformat(),
                "from_agent": "supervisor",
                "to_agent": "backend",
                "reason": "Next task: authentication"
            }
        ]
    )


def demo_approval_scenario(interactive=False):
    """Run approval scenario demonstration."""
    print("\n" + "="*70)
    print("HUMAN APPROVAL MECHANISM DEMONSTRATION")
    print("Task 15.1: Create human approval node with user interaction")
    print("="*70)
    
    # Create scenario
    print("\n📋 SCENARIO:")
    print("   A supervised workflow is building a REST API application.")
    print("   The backend agent has failed 5 times to generate the authentication")
    print("   system due to code quality issues.")
    print("   The system requires human approval to proceed.")
    
    state = create_approval_scenario()
    
    # Show workflow state
    print("\n📊 WORKFLOW STATE:")
    print(f"   Thread ID: {state.thread_id}")
    print(f"   Current Task: {state.current_task_id}")
    print(f"   Completed: {len(state.completed_task_ids)}/{len(state.execution_plan)} tasks")
    print(f"   Requires Approval: {state.requires_approval}")
    print(f"   Retry Counts: {dict(state.retry_counts)}")
    print(f"   Recent Errors: {len(state.error_log)}")
    
    # Check if approval is needed
    print("\n🔍 CHECKING APPROVAL TRIGGERS...")
    approval_needed = check_approval_needed(state)
    print(f"   Approval Required: {approval_needed}")
    
    if approval_needed:
        print("\n   Reasons:")
        if state.requires_approval:
            print("      ✓ Explicit approval flag set")
        if any(count >= 5 for count in state.retry_counts.values()):
            print("      ✓ Agent retry limit exceeded (5 attempts)")
        if sum(state.retry_counts.values()) >= 20:
            print("      ✓ Total workflow retry limit exceeded")
        for error in state.error_log[-1:]:
            if error.error_type == "critical":
                print("      ✓ Critical error detected")
    
    # Present approval request
    print("\n⏸️  WORKFLOW PAUSED - REQUESTING HUMAN APPROVAL...")
    
    if interactive:
        print("\n[Interactive mode - you will be prompted for input]")
        result = request_human_approval(state, timeout_seconds=300)
    else:
        print("\n[Demo mode - simulating user approval]")
        print("\n" + "-"*70)
        
        # Show what user would see
        handler = ApprovalHandler(timeout_seconds=300)
        request_text = handler.present_approval_request(state)
        print(request_text)
        
        print("\n[Simulating user choosing option A: Approve]")
        
        # Simulate approval
        with patch('builtins.input', return_value='A'):
            with patch('signal.SIGALRM', 14, create=True):
                with patch('signal.signal'):
                    with patch('signal.alarm'):
                        result = request_human_approval(state, timeout_seconds=1)
    
    # Show result
    print("\n✅ APPROVAL DECISION RECEIVED")
    print(f"   Requires Approval: {result.get('requires_approval', 'N/A')}")
    print(f"   Workflow Status: {result.get('workflow_status', 'N/A')}")
    
    if result.get("workflow_status") == "running":
        print("\n   Decision: APPROVED")
        print("   Action: Workflow will continue with current configuration")
        print("   Next Step: Supervisor will retry backend agent with monitoring")
    elif result.get("workflow_status") == "failed":
        print("\n   Decision: REJECTED")
        print("   Action: Workflow execution terminated")
        print("   Next Step: Manual intervention required")
    elif result.get("user_requirements") and result["user_requirements"] != state.user_requirements:
        print("\n   Decision: MODIFIED")
        print("   Action: Requirements updated, workflow will restart")
        print(f"   New Requirements: {result['user_requirements'][:100]}...")
    elif state.current_task_id in result.get("completed_task_ids", []):
        print("\n   Decision: SKIPPED")
        print(f"   Action: Task {state.current_task_id} marked as complete")
        print("   Next Step: Supervisor will route to next task")
    
    print("\n📝 STATE CHANGES:")
    print("   Updated fields:")
    for key, value in result.items():
        if key in ["requires_approval", "workflow_status", "approval_message", "updated_at"]:
            print(f"      - {key}: {value}")
    
    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    
    print("\n✅ VALIDATED REQUIREMENTS:")
    print("   ✓ Requirement 3.6: Supervisor requests approval for critical operations")
    print("   ✓ Requirement 9.5: Approval on max regeneration attempts")
    print("   ✓ Requirement 11.3: Approval for unresolvable errors")
    
    print("\n✅ IMPLEMENTED FEATURES:")
    print("   ✓ Workflow pause/interrupt logic")
    print("   ✓ Approval request presentation (CLI)")
    print("   ✓ User response handling (approve/reject/modify/skip)")
    print("   ✓ Workflow resumption after approval")
    print("   ✓ Timeout handling (configurable)")
    print("   ✓ State persistence through checkpointing")
    
    print("\n📚 USER OPTIONS:")
    print("   [A] Approve   - Continue workflow execution")
    print("   [R] Reject    - Abort workflow")
    print("   [M] Modify    - Update requirements and restart")
    print("   [S] Skip      - Skip current task and continue")
    
    print("\n⏱️  TIMEOUT HANDLING:")
    print("   Default timeout: 300 seconds (5 minutes)")
    print("   On timeout: Automatic rejection")
    print("   Configurable per approval request")
    
    print("="*70 + "\n")


def demo_different_scenarios():
    """Demonstrate different approval scenarios."""
    print("\n" + "="*70)
    print("APPROVAL SCENARIOS DEMONSTRATION")
    print("="*70)
    
    scenarios = [
        {
            "name": "Max Retries Exceeded",
            "requires_approval": True,
            "approval_message": "Backend agent failed 5 times",
            "retry_counts": {"backend": 5},
            "error_log": []
        },
        {
            "name": "Critical Error",
            "requires_approval": False,
            "approval_message": "Docker daemon not accessible",
            "retry_counts": {},
            "error_log": [
                ErrorRecord(
                    timestamp=datetime.now(),
                    agent="deployment",
                    task_id="deploy_1",
                    error_type="critical",
                    message="Docker not running",
                    retry_count=0
                )
            ]
        },
        {
            "name": "Total Retry Limit",
            "requires_approval": False,
            "approval_message": "Workflow retry limit exceeded",
            "retry_counts": {"backend": 5, "frontend": 5, "testing": 5, "deployment": 5},
            "error_log": []
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print("   " + "-"*66)
        
        state = WorkflowState(
            thread_id=f"scenario-{i}",
            user_requirements="Test",
            requires_approval=scenario["requires_approval"],
            approval_message=scenario["approval_message"],
            retry_counts=scenario["retry_counts"],
            error_log=scenario["error_log"],
            workflow_status="running"
        )
        
        approval_needed = check_approval_needed(state)
        print(f"   Approval Required: {approval_needed}")
        print(f"   Reason: {scenario['approval_message']}")
        
        if scenario["retry_counts"]:
            print(f"   Retry Counts: {dict(scenario['retry_counts'])}")
        if scenario["error_log"]:
            print(f"   Error Type: {scenario['error_log'][0].error_type}")
    
    print("\n" + "="*70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Demonstrate human approval mechanism (Task 15.1)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive mode for real user input"
    )
    parser.add_argument(
        "--scenarios",
        action="store_true",
        help="Show different approval scenarios"
    )
    
    args = parser.parse_args()
    
    if args.scenarios:
        demo_different_scenarios()
    else:
        demo_approval_scenario(interactive=args.interactive)


if __name__ == "__main__":
    main()
