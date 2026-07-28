"""
Human approval mechanism for workflow control.

This module implements the human-in-the-loop approval system that allows
users to approve, reject, or modify workflow execution at critical points.
"""

import sys
import signal
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .models import WorkflowState


class ApprovalTimeout(Exception):
    """Raised when approval request times out."""
    pass


class ApprovalHandler:
    """
    Handles human approval requests with timeout support.
    
    This class presents approval requests to users via CLI (stdin/stdout),
    collects responses, validates input, and handles timeout scenarios.
    """
    
    def __init__(self, timeout_seconds: int = 300):
        """
        Initialize approval handler.
        
        Args:
            timeout_seconds: Timeout for approval requests in seconds (default: 5 minutes)
        """
        self.timeout_seconds = timeout_seconds
        self._timeout_triggered = False
    
    def _timeout_handler(self, signum, frame):
        """Signal handler for approval timeout."""
        self._timeout_triggered = True
        raise ApprovalTimeout(f"Approval request timed out after {self.timeout_seconds} seconds")
    
    def present_approval_request(self, state: WorkflowState) -> str:
        """
        Present approval request to user with context.
        
        Args:
            state: Current workflow state
            
        Returns:
            Formatted approval request string
        """
        lines = []
        lines.append("\n" + "="*70)
        lines.append("🚨 HUMAN APPROVAL REQUIRED")
        lines.append("="*70)
        lines.append("")
        lines.append(f"Reason: {state.approval_message or 'Critical operation pending'}")
        lines.append("")
        
        # Show context
        lines.append("Context:")
        lines.append(f"  - Current Task: {state.current_task_id or 'None'}")
        lines.append(f"  - Completed Tasks: {len(state.completed_task_ids)}/{len(state.execution_plan)}")
        lines.append(f"  - Workflow Status: {state.workflow_status}")
        
        # Show error log if applicable
        if state.error_log:
            lines.append(f"  - Recent Errors: {len(state.error_log)}")
            if state.error_log:
                last_error = state.error_log[-1]
                lines.append(f"    Last Error: {last_error.message}")
                lines.append(f"    Agent: {last_error.agent}")
                lines.append(f"    Retry Count: {last_error.retry_count}")
        
        # Show retry counts
        if state.retry_counts:
            lines.append(f"  - Retry Counts: {dict(state.retry_counts)}")
        
        lines.append("")
        lines.append("Options:")
        lines.append("  [A] Approve - Continue workflow execution")
        lines.append("  [R] Reject - Abort workflow")
        lines.append("  [M] Modify - Modify requirements and retry")
        lines.append("  [S] Skip - Skip current task and continue")
        lines.append("")
        lines.append(f"⏰ This request will timeout in {self.timeout_seconds} seconds")
        lines.append("="*70)
        
        return "\n".join(lines)
    
    def get_user_response(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Get user response with timeout handling.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dictionary with decision and optional modifications
            
        Raises:
            ApprovalTimeout: If user doesn't respond within timeout
        """
        # Present request
        request_text = self.present_approval_request(state)
        print(request_text)
        
        # Set up timeout (Unix-like systems only)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.timeout_seconds)
        
        try:
            # Get user input
            response = input("Enter your choice (A/R/M/S): ").strip().upper()
            
            # Cancel timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            # Validate and process response
            if response == 'A':
                return self._process_approval(state)
            elif response == 'R':
                return self._process_rejection(state)
            elif response == 'M':
                return self._process_modification(state)
            elif response == 'S':
                return self._process_skip(state)
            else:
                print(f"Invalid choice: {response}. Please enter A, R, M, or S.")
                return self.get_user_response(state)
        
        except ApprovalTimeout:
            print("\n⏰ Approval request timed out. Automatically rejecting workflow.")
            return self._process_timeout(state)
        
        except KeyboardInterrupt:
            print("\n\n⚠️  User interrupted. Rejecting workflow.")
            return self._process_rejection(state)
        
        finally:
            # Ensure timeout is cancelled
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
    
    def _process_approval(self, state: WorkflowState) -> Dict[str, Any]:
        """Process approval decision."""
        print("\n✅ Approval granted. Resuming workflow...")
        
        return {
            "requires_approval": False,
            "approval_message": None,
            "workflow_status": "running",
            "updated_at": datetime.now()
        }
    
    def _process_rejection(self, state: WorkflowState) -> Dict[str, Any]:
        """Process rejection decision."""
        print("\n❌ Workflow rejected by user. Aborting...")
        
        return {
            "requires_approval": False,
            "approval_message": None,
            "workflow_status": "failed",
            "updated_at": datetime.now()
        }
    
    def _process_modification(self, state: WorkflowState) -> Dict[str, Any]:
        """Process modification decision with new requirements."""
        print("\n📝 Modifying requirements...")
        print("\nCurrent requirements:")
        print(f"  {state.user_requirements[:200]}..." if len(state.user_requirements) > 200 else f"  {state.user_requirements}")
        print("\nEnter new requirements (or press Enter to keep current):")
        
        new_requirements = input("> ").strip()
        
        if new_requirements:
            print(f"\n✅ Requirements updated. Workflow will restart with new requirements.")
            
            # Clear execution plan to force re-planning
            return {
                "requires_approval": False,
                "approval_message": None,
                "user_requirements": new_requirements,
                "execution_plan": [],
                "completed_task_ids": [],
                "current_task_id": None,
                "workflow_status": "running",
                "updated_at": datetime.now()
            }
        else:
            print("\n⚠️  No changes made. Resuming with current requirements.")
            return self._process_approval(state)
    
    def _process_skip(self, state: WorkflowState) -> Dict[str, Any]:
        """Process skip decision."""
        print("\n⏭️  Skipping current task and continuing...")
        
        # Mark current task as skipped
        if state.current_task_id:
            # Add to completed so supervisor moves to next task
            completed_ids = list(state.completed_task_ids) if state.completed_task_ids else []
            if state.current_task_id not in completed_ids:
                completed_ids.append(state.current_task_id)
            
            return {
                "requires_approval": False,
                "approval_message": None,
                "completed_task_ids": completed_ids,
                "current_task_id": None,
                "workflow_status": "running",
                "updated_at": datetime.now()
            }
        else:
            # No task to skip, just approve
            return self._process_approval(state)
    
    def _process_timeout(self, state: WorkflowState) -> Dict[str, Any]:
        """Process timeout scenario (automatic rejection)."""
        return {
            "requires_approval": False,
            "approval_message": "Approval request timed out",
            "workflow_status": "failed",
            "updated_at": datetime.now()
        }


def request_human_approval(
    state: WorkflowState,
    timeout_seconds: int = 300
) -> Dict[str, Any]:
    """
    Request human approval for workflow continuation.
    
    This function pauses workflow execution and presents an approval request
    to the user via CLI. The user can approve, reject, modify requirements,
    or skip the current task.
    
    Args:
        state: Current workflow state
        timeout_seconds: Timeout in seconds (default: 5 minutes)
        
    Returns:
        Dictionary with state updates based on user decision
        
    Example:
        >>> result = request_human_approval(state, timeout_seconds=180)
        >>> # User approves
        >>> result["requires_approval"]  # False
        >>> result["workflow_status"]    # "running"
    """
    handler = ApprovalHandler(timeout_seconds=timeout_seconds)
    return handler.get_user_response(state)


def request_approval_with_reason(
    state: WorkflowState,
    reason: str,
    timeout_seconds: int = 300
) -> Dict[str, Any]:
    """
    Request human approval with a specific reason message.
    
    Args:
        state: Current workflow state
        reason: Reason for approval request
        timeout_seconds: Timeout in seconds
        
    Returns:
        Dictionary with state updates
    """
    # Update state with approval message
    state.approval_message = reason
    state.requires_approval = True
    
    return request_human_approval(state, timeout_seconds=timeout_seconds)


def check_approval_needed(state: WorkflowState) -> bool:
    """
    Check if approval is needed based on workflow state.
    
    Args:
        state: Current workflow state
        
    Returns:
        True if approval is required, False otherwise
    """
    # Check if explicitly flagged
    if state.requires_approval:
        return True
    
    # Check retry limits
    for agent, count in state.retry_counts.items():
        if count >= 5:
            return True
    
    # Check total retries
    total_retries = sum(state.retry_counts.values())
    if total_retries >= 20:
        return True
    
    # Check critical errors
    if state.error_log:
        last_error = state.error_log[-1]
        if last_error.error_type in ["critical", "CriticalError"]:
            return True
    
    return False
