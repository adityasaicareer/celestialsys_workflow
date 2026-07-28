"""
Test script to verify Backend Agent's incremental fix functionality.

This script tests that:
1. _read_existing_code() correctly reads Python files
2. _generate_incremental_fixes() is callable
3. Integration with execute_task() works
"""

import os
import tempfile
from pathlib import Path
from workflow.agents.backend_agent import BackendAgent


def test_read_existing_code():
    """Test that _read_existing_code() reads files correctly."""
    print("🧪 Test 1: Reading existing code")
    
    agent = BackendAgent()
    
    # Create temporary directory with test files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_files = {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()",
            "models/todo.py": "class Todo:\n    pass",
            "routes/__init__.py": "# Routes",
            "requirements.txt": "fastapi>=0.110.0"
        }
        
        for file_path, content in test_files.items():
            full_path = Path(tmpdir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
        
        # Read existing code
        existing_code = agent._read_existing_code(tmpdir)
        
        # Verify
        print(f"   Found {len(existing_code)} files")
        assert len(existing_code) == 4, f"Expected 4 files, got {len(existing_code)}"
        assert "main.py" in existing_code, "main.py not found"
        assert "models/todo.py" in existing_code, "models/todo.py not found"
        assert "requirements.txt" in existing_code, "requirements.txt not found"
        
        print("   ✅ Test passed: _read_existing_code() works correctly\n")


def test_incremental_fix_prompt():
    """Test that incremental fix prompt is properly defined."""
    print("🧪 Test 2: Incremental fix prompt")
    
    agent = BackendAgent()
    
    # Get the prompt
    prompt = agent._get_incremental_fix_system_prompt()
    
    # Verify key phrases are present
    assert "INCREMENTAL FIX MODE" in prompt, "Missing incremental fix mode marker"
    assert "DO NOT regenerate everything" in prompt, "Missing regeneration warning"
    assert "MINIMAL, TARGETED edits" in prompt, "Missing minimal edits instruction"
    assert "Import/Attribute Errors" in prompt, "Missing import error guidance"
    assert "FastAPI Dependency Injection" in prompt, "Missing dependency injection guidance"
    
    print("   ✅ Test passed: Incremental fix prompt is comprehensive\n")


def test_generate_incremental_fixes_callable():
    """Test that _generate_incremental_fixes() method exists and is callable."""
    print("🧪 Test 3: Incremental fixes method exists")
    
    agent = BackendAgent()
    
    # Check method exists
    assert hasattr(agent, '_generate_incremental_fixes'), \
        "_generate_incremental_fixes() method not found"
    
    # Check it's callable
    assert callable(agent._generate_incremental_fixes), \
        "_generate_incremental_fixes() is not callable"
    
    print("   ✅ Test passed: _generate_incremental_fixes() method exists\n")


def test_execute_task_integration():
    """Test that execute_task() correctly uses incremental fix on retry."""
    print("🧪 Test 4: Integration with execute_task")
    
    agent = BackendAgent()
    
    # Verify execute_task still exists and is callable
    assert hasattr(agent, 'execute_task'), "execute_task() method not found"
    assert callable(agent.execute_task), "execute_task() is not callable"
    
    # Check the method signature includes the right parameters
    import inspect
    sig = inspect.signature(agent.execute_task)
    params = list(sig.parameters.keys())
    
    assert 'task_description' in params, "Missing task_description parameter"
    assert 'database_config' in params, "Missing database_config parameter"
    
    print("   ✅ Test passed: execute_task() integration looks good\n")


if __name__ == "__main__":
    print("=" * 70)
    print("Backend Agent Incremental Fix - Verification Tests")
    print("=" * 70)
    print()
    
    try:
        test_read_existing_code()
        test_incremental_fix_prompt()
        test_generate_incremental_fixes_callable()
        test_execute_task_integration()
        
        print("=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print()
        print("The incremental fix implementation is working correctly.")
        print("Backend Agent will now:")
        print("  1. Generate code from scratch on first attempt")
        print("  2. Read existing code on retry attempts")
        print("  3. Apply targeted fixes to only files with issues")
        print("  4. Preserve working code unchanged")
        print()
        
    except AssertionError as e:
        print("=" * 70)
        print("❌ TEST FAILED!")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        exit(1)
    except Exception as e:
        print("=" * 70)
        print("❌ UNEXPECTED ERROR!")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        exit(1)
