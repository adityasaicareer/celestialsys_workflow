"""
Functional test for Backend Agent - verifies actual code generation and evaluation.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_code_evaluator_syntax_validation():
    """Test that CodeEvaluator can validate Python syntax."""
    print("\n🔍 Testing CodeEvaluator syntax validation")
    
    from workflow.agents.backend_agent import CodeEvaluator
    
    evaluator = CodeEvaluator()
    
    # Test valid syntax
    valid_code = """
def hello_world():
    return "Hello, World!"
"""
    success, errors = evaluator.validate_syntax(valid_code)
    assert success == True, f"Valid code rejected: {errors}"
    assert len(errors) == 0, f"Valid code has errors: {errors}"
    print("   ✅ Valid syntax accepted")
    
    # Test invalid syntax
    invalid_code = """
def hello_world(
    return "Hello"
"""
    success, errors = evaluator.validate_syntax(invalid_code)
    assert success == False, "Invalid code accepted"
    assert len(errors) > 0, "No errors reported for invalid code"
    print("   ✅ Invalid syntax rejected")
    
    return True


def test_code_evaluator_feature_checking():
    """Test that CodeEvaluator can check for required features."""
    print("\n🔍 Testing CodeEvaluator feature checking")
    
    from workflow.agents.backend_agent import CodeEvaluator
    
    evaluator = CodeEvaluator()
    
    # Test FastAPI detection
    code_with_fastapi = """
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello"}
"""
    
    success, missing = evaluator.check_required_features(
        code_with_fastapi,
        "Build a REST API with FastAPI"
    )
    assert success == True, f"FastAPI code rejected: {missing}"
    print("   ✅ FastAPI features detected")
    
    # Test missing FastAPI
    code_without_fastapi = """
def hello():
    return "Hello"
"""
    
    success, missing = evaluator.check_required_features(
        code_without_fastapi,
        "Build a REST API with FastAPI"
    )
    assert success == False, "Missing FastAPI not detected"
    assert len(missing) > 0, "No missing features reported"
    print("   ✅ Missing FastAPI detected")
    
    return True


def test_minimal_app_generation():
    """Test that BackendAgent can generate minimal fallback app."""
    print("\n🔍 Testing minimal app generation")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    
    # Generate minimal app
    files = agent._generate_minimal_app("Build a simple API")
    
    # Check required files present
    assert "main.py" in files, "main.py not in minimal app"
    assert "config.py" in files, "config.py not in minimal app"
    assert "requirements.txt" in files, "requirements.txt not in minimal app"
    print("   ✅ All required files generated")
    
    # Check main.py has FastAPI
    main_content = files["main.py"]
    assert "FastAPI" in main_content, "FastAPI not in main.py"
    assert "app = FastAPI" in main_content or "app=FastAPI" in main_content, "FastAPI app not instantiated"
    assert "@app.get" in main_content, "No endpoints in main.py"
    print("   ✅ main.py has FastAPI app with endpoints")
    
    # Check requirements.txt has dependencies
    reqs = files["requirements.txt"]
    assert "fastapi" in reqs, "fastapi not in requirements.txt"
    assert "uvicorn" in reqs, "uvicorn not in requirements.txt"
    print("   ✅ requirements.txt has necessary dependencies")
    
    # Validate syntax of generated code
    from workflow.agents.backend_agent import CodeEvaluator
    evaluator = CodeEvaluator()
    
    success, errors = evaluator.validate_syntax(main_content, "main.py")
    assert success == True, f"Generated main.py has syntax errors: {errors}"
    print("   ✅ Generated code has valid syntax")
    
    return True


def test_write_code_creates_files():
    """Test that write_code creates files with proper structure."""
    print("\n🔍 Testing write_code file creation")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate minimal app
        files = agent._generate_minimal_app("Test app")
        
        # Write files
        created_files = agent.write_code(files, tmpdir)
        
        # Check files were created
        tmppath = Path(tmpdir)
        assert (tmppath / "main.py").exists(), "main.py not created"
        assert (tmppath / "config.py").exists(), "config.py not created"
        assert (tmppath / "requirements.txt").exists(), "requirements.txt not created"
        print("   ✅ All files created successfully")
        
        # Check file contents match
        with open(tmppath / "main.py", 'r') as f:
            content = f.read()
            assert content == files["main.py"], "main.py content mismatch"
        print("   ✅ File contents match expected")
        
        # Check that created_files list is accurate
        assert len(created_files) >= 3, f"Expected at least 3 files, got {len(created_files)}"
        print(f"   ✅ Created {len(created_files)} files")
    
    return True


def test_evaluate_code_quality_gates():
    """Test that evaluate_code runs all quality gates."""
    print("\n🔍 Testing evaluate_code quality gates")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    
    # Create temporary directory with code
    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate and write minimal app
        files = agent._generate_minimal_app("Test app")
        agent.write_code(files, tmpdir)
        
        # Evaluate the code
        results = agent.evaluate_code(tmpdir, "Build a REST API")
        
        # Check results structure
        assert "passed" in results, "Results missing 'passed' key"
        assert "issues" in results, "Results missing 'issues' key"
        assert "scores" in results, "Results missing 'scores' key"
        print("   ✅ Results have correct structure")
        
        # Check that quality gates ran
        assert "syntax" in results["scores"], "Syntax check not run"
        assert "pylint" in results["scores"], "Pylint not run"
        assert "mypy" in results["scores"], "Mypy not run"
        assert "features" in results["scores"], "Feature check not run"
        print("   ✅ All quality gates executed")
        
        # Check main.py was evaluated
        assert "file_evaluations" in results, "File evaluations missing"
        print("   ✅ File-level evaluation performed")
        
        # The minimal app should pass most checks (may fail pylint score)
        print(f"   📊 Overall passed: {results['passed']}")
        print(f"   📊 Syntax: {results['scores']['syntax']}")
        print(f"   📊 Pylint score: {results['scores']['pylint']}")
        print(f"   📊 Mypy: {results['scores']['mypy']}")
        print(f"   📊 Features: {results['scores']['features']}")
        
        if results["issues"]:
            print(f"   ℹ️  Issues found: {len(results['issues'])}")
            for issue in results["issues"][:3]:
                print(f"      - {issue}")
    
    return True


def test_execute_task_retry_logic():
    """Test that execute_task implements retry logic (dry run - no actual LLM calls)."""
    print("\n🔍 Testing execute_task retry logic structure")
    
    from workflow.agents.backend_agent import BackendAgent
    import inspect
    
    agent = BackendAgent()
    
    # Verify execute_task signature
    sig = inspect.signature(agent.execute_task)
    params = list(sig.parameters.keys())
    
    assert "task_description" in params, "execute_task missing task_description parameter"
    assert "database_config" in params, "execute_task missing database_config parameter"
    assert "max_retries" in params, "execute_task missing max_retries parameter"
    print("   ✅ execute_task has correct signature")
    
    # Check return value includes required keys
    source = inspect.getsource(agent.execute_task)
    required_keys = ["success", "output_dir", "evaluation", "attempts", "requires_approval"]
    
    for key in required_keys:
        assert f'"{key}"' in source or f"'{key}'" in source, f"execute_task result missing '{key}' key"
    print("   ✅ execute_task returns all required keys")
    
    # Check retry loop implementation
    assert "for attempt in range" in source, "No retry loop found"
    assert "previous_issues" in source, "Issues not passed to regeneration"
    assert "max_retries" in source.lower(), "max_retries not used"
    print("   ✅ Retry loop structure correct")
    
    # Check approval request logic
    assert "requires_approval" in source, "Approval request logic missing"
    assert "approval_message" in source, "Approval message not set"
    print("   ✅ Approval request logic present")
    
    return True


def test_regeneration_prompt_structure():
    """Test that regeneration prompt is properly configured."""
    print("\n🔍 Testing regeneration prompt")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    
    # Check regeneration prompt exists
    assert hasattr(agent, 'regeneration_prompt'), "regeneration_prompt missing"
    print("   ✅ regeneration_prompt exists")
    
    # Check system prompt for regeneration
    system_prompt = agent._get_regeneration_system_prompt()
    
    # Should mention fixing issues
    assert "fix" in system_prompt.lower() or "correct" in system_prompt.lower(), \
        "Regeneration prompt doesn't mention fixing"
    print("   ✅ Regeneration prompt mentions fixing issues")
    
    # Should mention quality standards
    assert "pylint" in system_prompt.lower(), "Regeneration prompt doesn't mention pylint"
    assert "type" in system_prompt.lower(), "Regeneration prompt doesn't mention types"
    print("   ✅ Regeneration prompt mentions quality standards")
    
    return True


def main():
    """Run all functional tests."""
    print("=" * 70)
    print("BACKEND AGENT FUNCTIONAL TESTS")
    print("=" * 70)
    
    tests = [
        ("Syntax Validation", test_code_evaluator_syntax_validation),
        ("Feature Checking", test_code_evaluator_feature_checking),
        ("Minimal App Generation", test_minimal_app_generation),
        ("File Writing", test_write_code_creates_files),
        ("Quality Gate Evaluation", test_evaluate_code_quality_gates),
        ("Retry Logic Structure", test_execute_task_retry_logic),
        ("Regeneration Prompt", test_regeneration_prompt_structure),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"   ❌ Test failed: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("FUNCTIONAL TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed, error in results:
        if passed:
            print(f"✅ PASS: {test_name}")
        else:
            print(f"❌ FAIL: {test_name}")
            if error:
                print(f"   Error: {error}")
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n🎉 ALL FUNCTIONAL TESTS PASSED!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
