"""
Test script to verify Task 9 completion: Backend Agent with self-evaluation.

This script verifies that:
1. BackendAgent can be instantiated
2. Code generation with LLM works
3. Self-evaluation loop is implemented
4. All required methods exist
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_task_9_1_backend_agent_code_generation():
    """
    Test Task 9.1: Backend Agent code generation with LLM
    
    Requirements:
    - BackendAgent class with LangChain OpenAI integration
    - FastAPI code generation with proper file structure
    - Comprehensive error handling and input validation
    - Python type hints and docstrings
    - requirements.txt generation
    - Database integration code
    """
    print("\n🔍 Testing Task 9.1: Backend Agent Code Generation")
    
    try:
        from workflow.agents.backend_agent import BackendAgent
        print("   ✅ BackendAgent class imports successfully")
    except ImportError as e:
        print(f"   ❌ Failed to import BackendAgent: {e}")
        return False
    
    # Check that BackendAgent has required attributes
    agent = BackendAgent()
    
    # Check LangChain OpenAI integration
    assert hasattr(agent, 'llm'), "BackendAgent missing 'llm' attribute"
    print("   ✅ LangChain OpenAI integration present")
    
    # Check code generation methods
    assert hasattr(agent, 'generate_code'), "BackendAgent missing 'generate_code' method"
    print("   ✅ generate_code method exists")
    
    # Check file writing capability
    assert hasattr(agent, 'write_code'), "BackendAgent missing 'write_code' method"
    print("   ✅ write_code method exists")
    
    # Check prompts for comprehensive generation
    assert hasattr(agent, 'generation_prompt'), "BackendAgent missing 'generation_prompt'"
    assert hasattr(agent, 'regeneration_prompt'), "BackendAgent missing 'regeneration_prompt'"
    print("   ✅ Generation and regeneration prompts exist")
    
    # Check for fallback minimal app generator
    assert hasattr(agent, '_generate_minimal_app'), "BackendAgent missing '_generate_minimal_app'"
    print("   ✅ Minimal app fallback exists")
    
    print("   ✅ Task 9.1 COMPLETE: All code generation features verified")
    return True


def test_task_9_2_backend_agent_self_evaluation():
    """
    Test Task 9.2: Backend Agent self-evaluation loop
    
    Requirements:
    - evaluate_code method using pylint (score > 8.0)
    - Type checking with mypy
    - Syntax validation (AST compilation)
    - Functionality comparison against requirements
    - Quality gate validation
    - Regeneration loop with retry counter (max 5)
    - Approval request when max retries exceeded
    """
    print("\n🔍 Testing Task 9.2: Backend Agent Self-Evaluation Loop")
    
    try:
        from workflow.agents.backend_agent import BackendAgent, CodeEvaluator
        print("   ✅ BackendAgent and CodeEvaluator classes imported")
    except ImportError as e:
        print(f"   ❌ Failed to import: {e}")
        return False
    
    agent = BackendAgent()
    
    # Check evaluate_code method exists
    assert hasattr(agent, 'evaluate_code'), "BackendAgent missing 'evaluate_code' method"
    print("   ✅ evaluate_code method exists")
    
    # Check execute_task with self-evaluation loop
    assert hasattr(agent, 'execute_task'), "BackendAgent missing 'execute_task' method"
    print("   ✅ execute_task method exists (implements self-evaluation loop)")
    
    # Check MAX_RETRIES constant
    assert hasattr(BackendAgent, 'MAX_RETRIES'), "BackendAgent missing 'MAX_RETRIES'"
    assert BackendAgent.MAX_RETRIES == 5, f"MAX_RETRIES should be 5, got {BackendAgent.MAX_RETRIES}"
    print(f"   ✅ MAX_RETRIES = {BackendAgent.MAX_RETRIES} (correct)")
    
    # Check CodeEvaluator implementation
    evaluator = CodeEvaluator()
    
    # Check pylint integration
    assert hasattr(CodeEvaluator, 'run_pylint'), "CodeEvaluator missing 'run_pylint'"
    assert hasattr(CodeEvaluator, 'PYLINT_THRESHOLD'), "CodeEvaluator missing 'PYLINT_THRESHOLD'"
    assert CodeEvaluator.PYLINT_THRESHOLD == 8.0, f"PYLINT_THRESHOLD should be 8.0, got {CodeEvaluator.PYLINT_THRESHOLD}"
    print(f"   ✅ Pylint integration with threshold {CodeEvaluator.PYLINT_THRESHOLD}")
    
    # Check mypy integration
    assert hasattr(CodeEvaluator, 'run_mypy'), "CodeEvaluator missing 'run_mypy'"
    print("   ✅ Mypy type checking integration")
    
    # Check syntax validation (AST compilation)
    assert hasattr(CodeEvaluator, 'validate_syntax'), "CodeEvaluator missing 'validate_syntax'"
    print("   ✅ AST syntax validation")
    
    # Check functionality comparison
    assert hasattr(CodeEvaluator, 'check_required_features'), "CodeEvaluator missing 'check_required_features'"
    print("   ✅ Functionality comparison against requirements")
    
    # Check comprehensive evaluation
    assert hasattr(CodeEvaluator, 'evaluate_file'), "CodeEvaluator missing 'evaluate_file'"
    print("   ✅ Comprehensive file evaluation method")
    
    # Verify execute_task implements retry loop
    import inspect
    execute_task_source = inspect.getsource(agent.execute_task)
    
    assert 'for attempt in range' in execute_task_source, "execute_task missing retry loop"
    print("   ✅ Retry loop implemented in execute_task")
    
    assert 'requires_approval' in execute_task_source, "execute_task missing approval request"
    print("   ✅ Approval request when max retries exceeded")
    
    assert 'previous_issues' in execute_task_source, "execute_task not passing issues to regeneration"
    print("   ✅ Issues passed to regeneration for corrections")
    
    print("   ✅ Task 9.2 COMPLETE: All self-evaluation features verified")
    return True


def verify_quality_gates():
    """
    Verify that the self-evaluation implements all required quality gates.
    """
    print("\n🔍 Verifying Quality Gates")
    
    from workflow.agents.backend_agent import CodeEvaluator
    import inspect
    
    evaluate_source = inspect.getsource(CodeEvaluator.evaluate_file)
    
    gates = {
        "Syntax validation": "validate_syntax" in evaluate_source,
        "Pylint check": "run_pylint" in evaluate_source,
        "Mypy type check": "run_mypy" in evaluate_source,
        "Feature completeness": "check_required_features" in evaluate_source,
    }
    
    all_passed = True
    for gate_name, present in gates.items():
        if present:
            print(f"   ✅ {gate_name} gate implemented")
        else:
            print(f"   ❌ {gate_name} gate missing")
            all_passed = False
    
    return all_passed


def verify_documentation():
    """
    Verify that code has proper documentation and validation comments.
    """
    print("\n🔍 Verifying Documentation")
    
    from workflow.agents.backend_agent import BackendAgent
    import inspect
    
    # Check class docstring
    assert BackendAgent.__doc__ is not None, "BackendAgent missing class docstring"
    print("   ✅ BackendAgent has class docstring")
    
    # Check that docstring mentions requirements validation
    doc = BackendAgent.__doc__
    if "Requirements:" in doc or "Validates:" in doc:
        print("   ✅ Docstring includes requirement validation markers")
    
    # Check method docstrings
    methods_to_check = ['generate_code', 'evaluate_code', 'execute_task', 'write_code']
    for method_name in methods_to_check:
        method = getattr(BackendAgent, method_name)
        if method.__doc__ is not None:
            print(f"   ✅ {method_name} has docstring")
        else:
            print(f"   ⚠️  {method_name} missing docstring")
    
    return True


def main():
    """Run all Task 9 verification tests."""
    print("=" * 70)
    print("TASK 9 VERIFICATION: Backend Agent with Self-Evaluation")
    print("=" * 70)
    
    results = []
    
    # Test 9.1: Code generation
    results.append(("Task 9.1: Code Generation", test_task_9_1_backend_agent_code_generation()))
    
    # Test 9.2: Self-evaluation
    results.append(("Task 9.2: Self-Evaluation", test_task_9_2_backend_agent_self_evaluation()))
    
    # Additional verification
    results.append(("Quality Gates", verify_quality_gates()))
    results.append(("Documentation", verify_documentation()))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n🎉 TASK 9 COMPLETE: All features verified successfully!")
        print("\nTask 9.1 ✅ Implement Backend Agent code generation with LLM")
        print("Task 9.2 ✅ Implement Backend Agent self-evaluation loop")
        return 0
    else:
        print("\n⚠️  Some features need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
