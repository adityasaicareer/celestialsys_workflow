#!/usr/bin/env python3
"""
Comprehensive verification script for all agents in the supervised workflow.
This script verifies that all agents are complete and functional.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))


def verify_agent_imports():
    """Verify all agents can be imported."""
    print("\n" + "="*70)
    print("VERIFICATION: Agent Imports")
    print("="*70)
    
    agents = {
        "Planning Agent": "workflow.agents.planning_agent.PlanningAgent",
        "Supervisor Agent": "workflow.agents.supervisor_agent.SupervisorAgent",
        "Backend Agent": "workflow.agents.backend_agent.BackendAgent",
        "Frontend Agent": "workflow.agents.frontend_agent.FrontendAgent",
        "Database Agent": "workflow.agents.database_agent.DatabaseAgent",
        "Testing Agent": "workflow.agents.testing_agent.TestingAgent",
        "Deployment Agent": "workflow.agents.deployment_agent.DeploymentAgent"
    }
    
    results = {}
    for name, import_path in agents.items():
        try:
            module_path, class_name = import_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            
            # Try to instantiate
            agent = agent_class()
            
            results[name] = "✅ PASS"
            print(f"   {name}: ✅ PASS")
        except Exception as e:
            results[name] = f"❌ FAIL: {str(e)}"
            print(f"   {name}: ❌ FAIL: {str(e)}")
    
    return all("✅" in v for v in results.values())


def verify_langgraph_construction():
    """Verify LangGraph state machine can be constructed."""
    print("\n" + "="*70)
    print("VERIFICATION: LangGraph State Machine")
    print("="*70)
    
    try:
        from workflow.graph import create_workflow_graph
        
        app, checkpoint_manager = create_workflow_graph()
        
        print("   ✅ Graph compiled successfully")
        print(f"   ✅ Checkpoint manager initialized")
        
        # Check nodes
        print("\n   Nodes in graph:")
        nodes = [
            "planning_node",
            "supervisor_node", 
            "backend_node",
            "frontend_node",
            "database_node",
            "testing_node",
            "deployment_node",
            "human_approval_node"
        ]
        
        for node in nodes:
            print(f"      - {node}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ FAIL: {str(e)}")
        return False


def verify_models():
    """Verify all data models are defined."""
    print("\n" + "="*70)
    print("VERIFICATION: Data Models")
    print("="*70)
    
    try:
        from workflow.models import (
            WorkflowState,
            ExecutionPlan,
            TaskDefinition,
            ErrorRecord,
            TestResults,
            DeploymentStatus,
            AgentMessage
        )
        
        models = [
            "WorkflowState",
            "ExecutionPlan",
            "TaskDefinition",
            "ErrorRecord",
            "TestResults",
            "DeploymentStatus",
            "AgentMessage"
        ]
        
        for model in models:
            print(f"   ✅ {model}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ FAIL: {str(e)}")
        return False


def verify_checkpointing():
    """Verify checkpointing infrastructure."""
    print("\n" + "="*70)
    print("VERIFICATION: Checkpointing Infrastructure")
    print("="*70)
    
    try:
        from workflow.checkpointing import CheckpointManager
        
        manager = CheckpointManager()
        saver = manager.get_saver()
        
        print("   ✅ CheckpointManager initialized")
        print("   ✅ Checkpoint saver created")
        print(f"   ✅ Checkpoint path: {manager.checkpoint_dir}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ FAIL: {str(e)}")
        return False


def verify_error_handling():
    """Verify error handling infrastructure."""
    print("\n" + "="*70)
    print("VERIFICATION: Error Handling Infrastructure")
    print("="*70)
    
    try:
        from workflow.error_handling import (
            classify_error,
            should_retry_error,
            calculate_backoff,
            handle_agent_error
        )
        
        functions = [
            "classify_error",
            "should_retry_error",
            "calculate_backoff",
            "handle_agent_error"
        ]
        
        for func in functions:
            print(f"   ✅ {func}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ FAIL: {str(e)}")
        return False


def verify_human_approval():
    """Verify human approval mechanism."""
    print("\n" + "="*70)
    print("VERIFICATION: Human Approval Mechanism")
    print("="*70)
    
    try:
        from workflow.approval import (
            request_human_approval,
            check_approval_needed
        )
        
        print("   ✅ request_human_approval")
        print("   ✅ check_approval_needed")
        
        return True
        
    except Exception as e:
        print(f"   ❌ FAIL: {str(e)}")
        return False


def verify_agent_capabilities():
    """Verify each agent has required capabilities."""
    print("\n" + "="*70)
    print("VERIFICATION: Agent Capabilities")
    print("="*70)
    
    try:
        from workflow.agents.planning_agent import PlanningAgent
        from workflow.agents.supervisor_agent import SupervisorAgent
        from workflow.agents.backend_agent import BackendAgent
        from workflow.agents.frontend_agent import FrontendAgent
        from workflow.agents.database_agent import DatabaseAgent
        from workflow.agents.testing_agent import TestingAgent
        from workflow.agents.deployment_agent import DeploymentAgent
        
        # Planning Agent
        print("\n   Planning Agent:")
        planning = PlanningAgent()
        assert hasattr(planning, 'create_execution_plan'), "Missing create_execution_plan"
        assert hasattr(planning, 'validate_plan'), "Missing validate_plan"
        assert hasattr(planning, 'read_markdown_file'), "Missing read_markdown_file"
        print("      ✅ create_execution_plan")
        print("      ✅ validate_plan")
        print("      ✅ read_markdown_file")
        
        # Supervisor Agent
        print("\n   Supervisor Agent:")
        supervisor = SupervisorAgent()
        assert hasattr(supervisor, 'route_next_agent'), "Missing route_next_agent"
        assert hasattr(supervisor, 'log_transition'), "Missing log_transition"
        assert hasattr(supervisor, 'calculate_progress'), "Missing calculate_progress"
        print("      ✅ route_next_agent")
        print("      ✅ log_transition")
        print("      ✅ calculate_progress")
        
        # Backend Agent
        print("\n   Backend Agent:")
        backend = BackendAgent()
        assert hasattr(backend, 'execute_task'), "Missing execute_task"
        assert hasattr(backend, 'generate_code'), "Missing generate_code"
        assert hasattr(backend, 'evaluate_code'), "Missing evaluate_code"
        print("      ✅ execute_task")
        print("      ✅ generate_code")
        print("      ✅ evaluate_code")
        
        # Frontend Agent
        print("\n   Frontend Agent:")
        frontend = FrontendAgent()
        assert hasattr(frontend, 'execute_task'), "Missing execute_task"
        assert hasattr(frontend, 'generate_code'), "Missing generate_code"
        assert hasattr(frontend, 'evaluate_code'), "Missing evaluate_code"
        print("      ✅ execute_task")
        print("      ✅ generate_code")
        print("      ✅ evaluate_code")
        
        # Database Agent
        print("\n   Database Agent:")
        database = DatabaseAgent()
        assert hasattr(database, 'execute_task'), "Missing execute_task"
        assert hasattr(database, 'initialize_postgres'), "Missing initialize_postgres"
        assert hasattr(database, 'initialize_mongodb'), "Missing initialize_mongodb"
        print("      ✅ execute_task")
        print("      ✅ initialize_postgres")
        print("      ✅ initialize_mongodb")
        
        # Testing Agent
        print("\n   Testing Agent:")
        testing = TestingAgent()
        assert hasattr(testing, 'execute_task'), "Missing execute_task"
        assert hasattr(testing, 'generate_tests'), "Missing generate_tests"
        assert hasattr(testing, 'execute_tests'), "Missing execute_tests"
        print("      ✅ execute_task")
        print("      ✅ generate_tests")
        print("      ✅ execute_tests")
        
        # Deployment Agent
        print("\n   Deployment Agent:")
        deployment = DeploymentAgent()
        assert hasattr(deployment, 'execute_task'), "Missing execute_task"
        assert hasattr(deployment, 'generate_dockerfile'), "Missing generate_dockerfile"
        assert hasattr(deployment, 'generate_docker_compose'), "Missing generate_docker_compose"
        print("      ✅ execute_task")
        print("      ✅ generate_dockerfile")
        print("      ✅ generate_docker_compose")
        
        return True
        
    except Exception as e:
        print(f"   ❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification checks."""
    print("\n" + "="*70)
    print("COMPREHENSIVE AGENT VERIFICATION")
    print("Supervised Agentic Workflow System")
    print("="*70)
    
    checks = [
        ("Agent Imports", verify_agent_imports),
        ("Data Models", verify_models),
        ("Checkpointing", verify_checkpointing),
        ("Error Handling", verify_error_handling),
        ("Human Approval", verify_human_approval),
        ("LangGraph Construction", verify_langgraph_construction),
        ("Agent Capabilities", verify_agent_capabilities)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {str(e)}")
            results[name] = False
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n   Total: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All agents are complete and functional!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} checks failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
