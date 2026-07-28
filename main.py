#!/usr/bin/env python3
"""
Main entry point for the Supervised Agentic Workflow System.

Usage:
    python main.py "Build a todo app with authentication"
    python main.py path/to/requirements.md
    python main.py --list-workflows
    python main.py --resume THREAD_ID
"""

import sys
import os
import uuid
import argparse
import shutil
from datetime import datetime
from typing import Optional

import docker
from docker.errors import DockerException

from workflow.models import WorkflowState
from workflow.graph import create_workflow_graph
from workflow.config import get_config
from workflow.checkpointing import CheckpointManager


def validate_docker() -> bool:
    """
    Validate that Docker daemon is running and accessible.
    
    Returns:
        True if Docker is available, False otherwise
    """
    try:
        client = docker.from_env()
        client.ping()
        return True
    except DockerException:
        return False
    except Exception:
        return False


def validate_nodejs() -> bool:
    """
    Validate that Node.js is installed and accessible.
    
    Returns:
        True if Node.js is available, False otherwise
    """
    return shutil.which("node") is not None


def validate_python_packages() -> tuple[bool, list[str]]:
    """
    Validate that required Python packages are installed.
    
    Returns:
        Tuple of (all_installed, missing_packages)
    """
    required_packages = [
        "langchain",
        "langgraph",
        "docker",
        "fastapi",
        "pydantic",
        "pydantic_settings",
        "openai"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    return len(missing) == 0, missing


def run_preflight_checks() -> bool:
    """
    Run pre-flight checks for required tools and configuration.
    
    Returns:
        True if all checks pass, False otherwise
    """
    print("🔍 Running pre-flight checks...")
    print()
    
    all_passed = True
    
    # Check Docker
    print("   ⚙️  Checking Docker daemon...", end=" ")
    if validate_docker():
        print("✅")
    else:
        print("❌")
        print("      Error: Docker daemon is not running or not accessible")
        print("      Please start Docker and try again")
        all_passed = False
    
    # Check Node.js
    print("   ⚙️  Checking Node.js...", end=" ")
    if validate_nodejs():
        print("✅")
    else:
        print("❌")
        print("      Error: Node.js is not installed or not in PATH")
        print("      Please install Node.js and try again")
        all_passed = False
    
    # Check Python packages
    print("   ⚙️  Checking Python packages...", end=" ")
    packages_ok, missing = validate_python_packages()
    if packages_ok:
        print("✅")
    else:
        print("❌")
        print(f"      Error: Missing required packages: {', '.join(missing)}")
        print("      Please run: pip install -r requirements.txt")
        all_passed = False
    
    print()
    
    if all_passed:
        print("✅ All pre-flight checks passed")
    else:
        print("❌ Pre-flight checks failed")
    
    print()
    return all_passed


def create_output_directories() -> None:
    """
    Create output directories for frontend and backend code if they don't exist.
    """
    config = get_config()
    
    frontend_dir = config.frontend_output_dir
    backend_dir = config.backend_output_dir
    
    print("📁 Creating output directories...")
    
    if not os.path.exists(frontend_dir):
        os.makedirs(frontend_dir, exist_ok=True)
        print(f"   ✅ Created: {frontend_dir}")
    else:
        print(f"   ℹ️  Already exists: {frontend_dir}")
    
    if not os.path.exists(backend_dir):
        os.makedirs(backend_dir, exist_ok=True)
        print(f"   ✅ Created: {backend_dir}")
    else:
        print(f"   ℹ️  Already exists: {backend_dir}")
    
    print()


def list_workflows() -> None:
    """
    List all incomplete workflows that can be resumed.
    """
    print("=" * 80)
    print("📋 Incomplete Workflows")
    print("=" * 80)
    print()
    
    checkpoint_manager = CheckpointManager()
    incomplete_threads = checkpoint_manager.get_incomplete_workflows()
    
    if not incomplete_threads:
        print("No incomplete workflows found.")
        print()
        return
    
    print(f"Found {len(incomplete_threads)} incomplete workflow(s):")
    print()
    
    for thread_id in incomplete_threads:
        checkpoints = checkpoint_manager.list_checkpoints(thread_id)
        if checkpoints:
            latest = checkpoints[0]
            print(f"🆔 Thread ID: {thread_id}")
            print(f"   Last checkpoint: {latest.checkpoint_id}")
            print(f"   Status: {latest.workflow_status}")
            print(f"   Updated: {latest.created_at}")
            print()
    
    print("To resume a workflow, use:")
    print("  python main.py --resume THREAD_ID")
    print()


def resume_workflow(thread_id: str) -> None:
    """
    Resume an existing workflow from checkpoint.
    
    Args:
        thread_id: Thread ID of the workflow to resume
    """
    print("=" * 80)
    print("🔄 Resuming Workflow")
    print("=" * 80)
    print()
    print(f"🆔 Thread ID: {thread_id}")
    print()
    
    # Validate checkpoint exists
    checkpoint_manager = CheckpointManager()
    
    if not checkpoint_manager.verify_checkpoint_integrity(thread_id):
        print("❌ Error: No valid checkpoint found for this thread ID")
        print()
        print("To list available workflows, use:")
        print("  python main.py --list-workflows")
        sys.exit(1)
    
    # Display workflow state
    checkpoints = checkpoint_manager.list_checkpoints(thread_id)
    if checkpoints:
        latest = checkpoints[0]
        print("📊 Workflow State:")
        print(f"   Checkpoint ID: {latest.checkpoint_id}")
        print(f"   Last node: {latest.node_name}")
        print(f"   Status: {latest.workflow_status}")
        print(f"   Updated: {latest.created_at}")
        print()
    
    # Ask for user confirmation
    print("⚠️  This will continue the workflow from the last checkpoint.")
    response = input("Do you want to proceed? (yes/no): ").strip().lower()
    
    if response not in ["yes", "y"]:
        print("❌ Resume cancelled by user")
        sys.exit(0)
    
    print()
    
    # Run pre-flight checks
    if not run_preflight_checks():
        print("❌ Pre-flight checks failed. Cannot resume workflow.")
        sys.exit(1)
    
    # Create output directories
    create_output_directories()
    
    # Create workflow graph
    print("🔧 Initializing workflow graph...")
    app, checkpoint_manager = create_workflow_graph()
    print("✅ Workflow graph created")
    print()
    
    # Execute workflow from checkpoint
    print("🚀 Resuming workflow execution...")
    print("-" * 80)
    
    try:
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run the workflow (it will automatically resume from checkpoint)
        for event in app.stream(None, config):
            print()
            print(f"📦 Event: {list(event.keys())}")
        
        print()
        print("-" * 80)
        print("✅ Workflow completed successfully!")
        print()
        
        # Get final state
        final_state = app.get_state(config)
        state_dict = final_state.values
        
        # Print summary
        print("📊 Workflow Summary:")
        print(f"   Status: {state_dict.get('workflow_status', 'unknown')}")
        print(f"   Tasks completed: {len(state_dict.get('completed_task_ids', []))}")
        print(f"   Agent transitions: {len(state_dict.get('agent_transitions', []))}")
        
        if state_dict.get('deployment_status'):
            dep = state_dict['deployment_status']
            print()
            print("🚀 Deployment Info:")
            # Handle both dict and Pydantic model
            if hasattr(dep, 'frontend_url'):
                print(f"   Frontend: {dep.frontend_url or 'N/A'}")
                print(f"   Backend: {dep.backend_url or 'N/A'}")
                print(f"   Containers: {', '.join(dep.containers_running or [])}")
            else:
                print(f"   Frontend: {dep.get('frontend_url', 'N/A')}")
                print(f"   Backend: {dep.get('backend_url', 'N/A')}")
                print(f"   Containers: {', '.join(dep.get('containers_running', []))}")
        
        # Clean up checkpoint on successful completion
        print()
        print("🧹 Cleaning up checkpoints...")
        if checkpoint_manager.cleanup_checkpoint(thread_id):
            print("✅ Checkpoint cleanup successful")
        else:
            print("⚠️  Checkpoint cleanup failed (this is non-critical)")
        
    except KeyboardInterrupt:
        print()
        print()
        print("⏸️  Workflow interrupted by user")
        print(f"   You can resume using: python main.py --resume {thread_id}")
        sys.exit(0)
    
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ Error: {str(e)}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def start_new_workflow(requirements: str) -> None:
    """
    Start a new workflow with the given requirements.
    
    Args:
        requirements: User requirements as text or file path to .md file
    """
    print("=" * 80)
    print("🤖 Supervised Agentic Workflow System")
    print("=" * 80)
    print()
    
    # Check if requirements is a file path
    requirements_text = requirements
    requirements_source = "text"
    context_file_path = None
    
    if requirements.endswith(".md") or os.path.isfile(requirements):
        # It's a file path
        context_file_path = requirements
        requirements_source = "file"
        
        try:
            with open(requirements, 'r', encoding='utf-8') as f:
                requirements_text = f.read()
            
            print(f"� Requirements file: {requirements}")
            print(f"   File size: {len(requirements_text)} characters")
            print()
        except FileNotFoundError:
            print(f"❌ Error: File not found: {requirements}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading file: {str(e)}")
            sys.exit(1)
    
    print(f"�📝 Requirements: {requirements_text[:100]}{'...' if len(requirements_text) > 100 else ''}")
    print()
    
    # Run pre-flight checks
    if not run_preflight_checks():
        print("❌ Pre-flight checks failed. Cannot start workflow.")
        sys.exit(1)
    
    # Create output directories
    create_output_directories()
    
    # Create workflow graph
    print("🔧 Initializing workflow graph...")
    app, checkpoint_manager = create_workflow_graph()
    print("✅ Workflow graph created")
    print()
    
    # Create initial state
    thread_id = str(uuid.uuid4())
    initial_state = WorkflowState(
        thread_id=thread_id,
        user_requirements=requirements_text,  # Use the actual content, not file path
        requirements_source=requirements_source,
        context_file_path=context_file_path,  # Store original file path if provided
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    print(f"🆔 Thread ID: {thread_id}")
    print()
    
    # Execute workflow
    print("🚀 Starting workflow execution...")
    print("-" * 80)
    
    try:
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run the workflow
        for event in app.stream(initial_state.model_dump(), config):
            print()
            print(f"📦 Event: {list(event.keys())}")
        
        print()
        print("-" * 80)
        print("✅ Workflow completed successfully!")
        print()
        
        # Get final state
        final_state = app.get_state(config)
        state_dict = final_state.values
        
        # Print summary
        print("📊 Workflow Summary:")
        print(f"   Status: {state_dict.get('workflow_status', 'unknown')}")
        print(f"   Tasks completed: {len(state_dict.get('completed_task_ids', []))}")
        print(f"   Agent transitions: {len(state_dict.get('agent_transitions', []))}")
        
        if state_dict.get('deployment_status'):
            dep = state_dict['deployment_status']
            print()
            print("🚀 Deployment Info:")
            # Handle both dict and Pydantic model
            if hasattr(dep, 'frontend_url'):
                print(f"   Frontend: {dep.frontend_url or 'N/A'}")
                print(f"   Backend: {dep.backend_url or 'N/A'}")
                print(f"   Containers: {', '.join(dep.containers_running or [])}")
            else:
                print(f"   Frontend: {dep.get('frontend_url', 'N/A')}")
                print(f"   Backend: {dep.get('backend_url', 'N/A')}")
                print(f"   Containers: {', '.join(dep.get('containers_running', []))}")
        
        # Clean up checkpoint on successful completion
        print()
        print("🧹 Cleaning up checkpoints...")
        checkpoint_manager = CheckpointManager()
        if checkpoint_manager.cleanup_checkpoint(thread_id):
            print("✅ Checkpoint cleanup successful")
        else:
            print("⚠️  Checkpoint cleanup failed (this is non-critical)")
        
    except KeyboardInterrupt:
        print()
        print()
        print("⏸️  Workflow interrupted by user")
        print(f"   You can resume using: python main.py --resume {thread_id}")
        sys.exit(0)
    
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ Error: {str(e)}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Supervised Agentic Workflow System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Start new workflow with text requirements:
    python main.py "Build a todo app with authentication"
  
  Start new workflow with requirements file:
    python main.py path/to/requirements.md
  
  List incomplete workflows:
    python main.py --list-workflows
  
  Resume an incomplete workflow:
    python main.py --resume THREAD_ID
        """
    )
    
    parser.add_argument(
        "requirements",
        nargs="?",
        help="User requirements as text or path to .md file (e.g., 'requirements.md' or 'Build a todo app')"
    )
    
    parser.add_argument(
        "--list-workflows",
        action="store_true",
        help="List all incomplete workflows that can be resumed"
    )
    
    parser.add_argument(
        "--resume",
        metavar="THREAD_ID",
        help="Resume an existing workflow by thread ID"
    )
    
    args = parser.parse_args()
    
    # Handle --list-workflows
    if args.list_workflows:
        list_workflows()
        return
    
    # Handle --resume
    if args.resume:
        resume_workflow(args.resume)
        return
    
    # Handle new workflow
    if not args.requirements:
        parser.print_help()
        sys.exit(1)
    
    start_new_workflow(args.requirements)


if __name__ == "__main__":
    main()
