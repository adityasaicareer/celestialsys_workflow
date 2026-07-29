#!/usr/bin/env python3
"""
Quick test to verify Testing Agent backend reading fix is working.
This script checks if the new _read_backend_code_content method exists.
"""

from workflow.agents.testing_agent import TestingAgent
from pathlib import Path
import inspect


def test_backend_reading_method():
    """Test that _read_backend_code_content method exists."""
    agent = TestingAgent()
    
    print("Testing Testing Agent Backend Reading Fix...")
    print("=" * 60)
    
    # Check if method exists
    if hasattr(agent, '_read_backend_code_content'):
        print("✅ Method _read_backend_code_content exists")
        
        # Check method signature
        method = getattr(agent, '_read_backend_code_content')
        sig = inspect.signature(method)
        
        if 'backend_path' in sig.parameters:
            print("✅ Method has backend_path parameter")
        else:
            print("❌ Method missing backend_path parameter")
            return False
        
        # Check if method is callable
        if callable(method):
            print("✅ Method is callable")
        else:
            print("❌ Method is not callable")
            return False
        
        return True
    else:
        print("❌ Method _read_backend_code_content does NOT exist")
        return False


def test_generate_backend_tests_signature():
    """Test that generate_backend_tests uses the new method."""
    agent = TestingAgent()
    
    print("\nTesting generate_backend_tests Integration...")
    print("=" * 60)
    
    # Get the source code of generate_backend_tests
    method = agent.generate_backend_tests
    source = inspect.getsource(method)
    
    checks = [
        "_read_backend_code_content",
        "backend_code_content",
        "Reading backend code content"
    ]
    
    all_passed = True
    for check in checks:
        if check in source:
            print(f"✅ Found: '{check}' in generate_backend_tests")
        else:
            print(f"❌ Missing: '{check}' in generate_backend_tests")
            all_passed = False
    
    return all_passed


def test_method_functionality():
    """Test that the method can actually read backend code."""
    agent = TestingAgent()
    
    print("\nTesting Method Functionality...")
    print("=" * 60)
    
    # Try reading the actual backend directory
    backend_path = Path(__file__).parent / "backend"
    
    if not backend_path.exists():
        print("⚠️  Backend directory not found - skipping functionality test")
        return True
    
    try:
        # Call the method
        result = agent._read_backend_code_content(backend_path)
        
        if result and len(result) > 0:
            print(f"✅ Method returned {len(result)} characters of code")
            
            # Check if it contains file markers
            if "## FILE:" in result:
                print("✅ Contains file markers")
            else:
                print("⚠️  No file markers found")
            
            # Check if it read main.py
            if "main.py" in result:
                print("✅ Read main.py")
            else:
                print("⚠️  Did not read main.py")
            
            return True
        else:
            print("❌ Method returned empty result")
            return False
    except Exception as e:
        print(f"❌ Method raised exception: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING AGENT BACKEND READING FIX VERIFICATION")
    print("=" * 60 + "\n")
    
    test1 = test_backend_reading_method()
    test2 = test_generate_backend_tests_signature()
    test3 = test_method_functionality()
    
    print("\n" + "=" * 60)
    if test1 and test2 and test3:
        print("✅ ALL TESTS PASSED - Testing Agent fix is working!")
    else:
        print("❌ SOME TESTS FAILED - Review the fix implementation")
    print("=" * 60 + "\n")
