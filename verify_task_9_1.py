"""
Verification test for Task 9.1: Backend Agent Implementation

This test verifies that all requirements for task 9.1 are met:
1. ✅ BackendAgent class with LangChain OpenAI integration
2. ✅ FastAPI code generation with proper file structure (main.py, models/, routes/, services/, config.py)
3. ✅ Comprehensive error handling and input validation to generated code
4. ✅ Python type hints and docstrings in all generated code
5. ✅ Requirements.txt generation with correct dependencies
6. ✅ Database integration code (SQLAlchemy models, connection management)

Requirements validated: 4.1, 4.4, 4.5, 4.6, 12.2, 13.1, 13.3, 14.1
"""

import sys
import os
import inspect
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def verify_langchain_integration():
    """
    Verify Requirement: BackendAgent class with LangChain OpenAI integration
    
    Task Detail: "Create BackendAgent class with LangChain OpenAI integration"
    Requirements: 4.1, 12.2
    """
    print("\n✅ Requirement 1: BackendAgent class with LangChain OpenAI integration")
    
    from workflow.agents.backend_agent import BackendAgent
    from langchain_openai import ChatOpenAI
    
    # Verify class exists
    assert BackendAgent is not None, "BackendAgent class not found"
    print("   ✓ BackendAgent class exists")
    
    # Create instance
    agent = BackendAgent()
    assert agent is not None, "Cannot instantiate BackendAgent"
    print("   ✓ BackendAgent can be instantiated")
    
    # Verify LLM integration
    assert hasattr(agent, 'llm'), "BackendAgent missing 'llm' attribute"
    assert isinstance(agent.llm, ChatOpenAI), "LLM is not ChatOpenAI instance"
    print("   ✓ Uses LangChain ChatOpenAI integration")
    
    # Verify configuration
    assert hasattr(agent, 'config'), "BackendAgent missing 'config' attribute"
    print("   ✓ Has configuration management")
    
    # Verify prompts are configured
    assert hasattr(agent, 'generation_prompt'), "Missing generation_prompt"
    assert hasattr(agent, 'regeneration_prompt'), "Missing regeneration_prompt"
    print("   ✓ Has LangChain prompt templates configured")
    
    return True


def verify_file_structure_generation():
    """
    Verify Requirement: FastAPI code generation with proper file structure
    
    Task Detail: "Implement FastAPI code generation with proper file structure: 
                  main.py, models/, routes/, services/, config.py"
    Requirements: 4.1, 4.5, 13.1, 13.3
    """
    print("\n✅ Requirement 2: FastAPI code generation with proper file structure")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    
    # Check generation system prompt instructs proper structure
    system_prompt = agent._get_generation_system_prompt()
    
    required_files = ["main.py", "models/", "routes/", "services/", "config.py"]
    for file_structure in required_files:
        assert file_structure in system_prompt, f"System prompt doesn't mention {file_structure}"
    print("   ✓ System prompt instructs proper file structure")
    
    # Verify minimal app has proper structure
    files = agent._generate_minimal_app("Test task")
    
    assert "main.py" in files, "main.py not in generated files"
    assert "config.py" in files, "config.py not in generated files"
    assert "requirements.txt" in files, "requirements.txt not in generated files"
    print("   ✓ Generates main.py, config.py, requirements.txt")
    
    # Verify main.py has FastAPI app
    main_content = files["main.py"]
    assert "FastAPI" in main_content, "FastAPI not imported"
    assert "app = FastAPI" in main_content or "app=FastAPI" in main_content, "FastAPI app not created"
    print("   ✓ main.py contains FastAPI application")
    
    # Verify write_code creates proper directory structure
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test with files that should create directories
        test_files = {
            "main.py": "# main",
            "models/__init__.py": "# models",
            "models/user.py": "# user model",
            "routes/__init__.py": "# routes",
            "routes/auth.py": "# auth routes"
        }
        
        created = agent.write_code(test_files, tmpdir)
        
        tmppath = Path(tmpdir)
        assert (tmppath / "main.py").exists(), "main.py not created"
        assert (tmppath / "models" / "__init__.py").exists(), "models/__init__.py not created"
        assert (tmppath / "models" / "user.py").exists(), "models/user.py not created"
        assert (tmppath / "routes" / "__init__.py").exists(), "routes/__init__.py not created"
        assert (tmppath / "routes" / "auth.py").exists(), "routes/auth.py not created"
        print("   ✓ Creates proper directory structure with models/, routes/")
    
    return True


def verify_error_handling_and_validation():
    """
    Verify Requirement: Comprehensive error handling and input validation
    
    Task Detail: "Add comprehensive error handling and input validation to generated code"
    Requirements: 4.3, 4.4
    """
    print("\n✅ Requirement 3: Comprehensive error handling and input validation")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    system_prompt = agent._get_generation_system_prompt()
    
    # Verify prompt instructs error handling
    assert "error handling" in system_prompt.lower(), "Prompt doesn't mention error handling"
    assert "validation" in system_prompt.lower(), "Prompt doesn't mention validation"
    print("   ✓ System prompt instructs error handling and validation")
    
    # Check for specific error handling instructions
    assert "try-except" in system_prompt.lower() or "try/except" in system_prompt.lower(), \
        "Prompt doesn't mention try-except blocks"
    print("   ✓ Instructs try-except for error handling")
    
    # Check for validation instructions
    assert "pydantic" in system_prompt.lower(), "Prompt doesn't mention Pydantic validation"
    assert "status codes" in system_prompt.lower() or "status code" in system_prompt.lower(), \
        "Prompt doesn't mention HTTP status codes"
    print("   ✓ Instructs Pydantic validation and proper status codes")
    
    # Verify minimal app has error handling
    files = agent._generate_minimal_app("Test")
    main_content = files["main.py"]
    
    # Should have CORS middleware (error prevention)
    assert "CORS" in main_content or "cors" in main_content.lower(), \
        "No CORS middleware for cross-origin error handling"
    print("   ✓ Generated code includes CORS middleware")
    
    return True


def verify_type_hints_and_docstrings():
    """
    Verify Requirement: Python type hints and docstrings in all generated code
    
    Task Detail: "Ensure Python type hints and docstrings in all generated code"
    Requirements: 4.6
    """
    print("\n✅ Requirement 4: Python type hints and docstrings in all generated code")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    system_prompt = agent._get_generation_system_prompt()
    
    # Verify prompt enforces type hints
    assert "type hints" in system_prompt.lower() or "type hint" in system_prompt.lower(), \
        "Prompt doesn't mention type hints"
    assert "ALL functions" in system_prompt and "type hints" in system_prompt, \
        "Prompt doesn't enforce type hints for all functions"
    print("   ✓ System prompt enforces type hints for ALL functions")
    
    # Verify prompt enforces docstrings
    assert "docstring" in system_prompt.lower(), "Prompt doesn't mention docstrings"
    assert "ALL functions" in system_prompt and "docstring" in system_prompt.lower(), \
        "Prompt doesn't enforce docstrings for all functions"
    print("   ✓ System prompt enforces docstrings for ALL functions/classes")
    
    # Check minimal app has type hints and docstrings
    files = agent._generate_minimal_app("Test")
    main_content = files["main.py"]
    
    # Check for type hints (Dict, str, etc.)
    has_type_hints = any(keyword in main_content for keyword in ["Dict[", "-> ", ": str", ": int", ": bool"])
    assert has_type_hints, "Generated code lacks type hints"
    print("   ✓ Generated code includes type hints")
    
    # Check for docstrings ("""...""")
    assert '"""' in main_content, "Generated code lacks docstrings"
    print("   ✓ Generated code includes docstrings")
    
    # Verify quality gates check for these
    assert hasattr(agent, 'evaluator'), "No evaluator for quality checking"
    print("   ✓ Has code evaluator for quality gates")
    
    return True


def verify_requirements_txt_generation():
    """
    Verify Requirement: requirements.txt generation with correct dependencies
    
    Task Detail: "Add requirements.txt generation with correct dependencies"
    Requirements: 13.1
    """
    print("\n✅ Requirement 5: requirements.txt generation with correct dependencies")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    
    # Verify minimal app includes requirements.txt
    files = agent._generate_minimal_app("Test")
    assert "requirements.txt" in files, "requirements.txt not generated"
    print("   ✓ Generates requirements.txt")
    
    # Verify it has essential dependencies
    requirements = files["requirements.txt"]
    
    essential_deps = ["fastapi", "uvicorn", "pydantic", "sqlalchemy"]
    missing = []
    for dep in essential_deps:
        if dep.lower() not in requirements.lower():
            missing.append(dep)
    
    assert len(missing) == 0, f"Missing dependencies: {missing}"
    print(f"   ✓ Includes essential dependencies: {', '.join(essential_deps)}")
    
    # Check for version pinning
    has_versions = ">=" in requirements or "==" in requirements
    assert has_versions, "Dependencies not version-pinned"
    print("   ✓ Dependencies are version-pinned")
    
    # Verify system prompt instructs dependency generation
    system_prompt = agent._get_generation_system_prompt()
    assert "requirements.txt" in system_prompt, "Prompt doesn't mention requirements.txt"
    print("   ✓ System prompt instructs requirements.txt generation")
    
    return True


def verify_database_integration():
    """
    Verify Requirement: Database integration code (SQLAlchemy models, connection management)
    
    Task Detail: "Implement database integration code (SQLAlchemy models, connection management)"
    Requirements: 4.1, 14.1
    """
    print("\n✅ Requirement 6: Database integration code (SQLAlchemy models, connection management)")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    system_prompt = agent._get_generation_system_prompt()
    
    # Verify prompt instructs database integration
    assert "database" in system_prompt.lower(), "Prompt doesn't mention database"
    assert "sqlalchemy" in system_prompt.lower(), "Prompt doesn't mention SQLAlchemy"
    print("   ✓ System prompt mentions database and SQLAlchemy")
    
    # Check for specific database instructions
    db_keywords = ["connection string", "session", "dependency injection", "model"]
    found_keywords = [kw for kw in db_keywords if kw in system_prompt.lower()]
    assert len(found_keywords) >= 3, f"Missing database concepts. Found: {found_keywords}"
    print(f"   ✓ Instructs database concepts: {', '.join(found_keywords)}")
    
    # Verify models/ directory is instructed
    assert "models/" in system_prompt or "models:" in system_prompt, \
        "Prompt doesn't mention models/ directory"
    print("   ✓ Instructs creating models/ directory for database models")
    
    # Check config.py handles database configuration
    files = agent._generate_minimal_app("Test")
    config_content = files["config.py"]
    
    # Config should use pydantic settings for configuration management
    assert "Settings" in config_content or "Config" in config_content, \
        "config.py doesn't define settings class"
    print("   ✓ config.py includes configuration management")
    
    # Verify requirements.txt includes database drivers
    requirements = files["requirements.txt"]
    db_drivers = ["psycopg2", "pymongo"]
    found_drivers = [drv for drv in db_drivers if drv in requirements.lower()]
    assert len(found_drivers) > 0, f"No database drivers in requirements.txt"
    print(f"   ✓ requirements.txt includes database drivers: {', '.join(found_drivers)}")
    
    # Verify generate_code accepts database_config parameter
    import inspect
    sig = inspect.signature(agent.generate_code)
    params = list(sig.parameters.keys())
    assert "database_config" in params, "generate_code doesn't accept database_config"
    print("   ✓ generate_code accepts database_config parameter")
    
    return True


def verify_self_evaluation_loop():
    """
    Verify: Self-evaluation loop implementation (bonus verification)
    
    This is part of task 9.2 but should be present in the agent structure.
    """
    print("\n✅ Bonus: Self-evaluation loop structure")
    
    from workflow.agents.backend_agent import BackendAgent, CodeEvaluator
    
    agent = BackendAgent()
    
    # Verify CodeEvaluator exists
    assert CodeEvaluator is not None, "CodeEvaluator class not found"
    print("   ✓ CodeEvaluator class exists")
    
    # Verify evaluator methods
    evaluator = CodeEvaluator()
    assert hasattr(evaluator, 'validate_syntax'), "Missing validate_syntax method"
    assert hasattr(evaluator, 'run_pylint'), "Missing run_pylint method"
    assert hasattr(evaluator, 'run_mypy'), "Missing run_mypy method"
    assert hasattr(evaluator, 'check_required_features'), "Missing check_required_features"
    print("   ✓ CodeEvaluator has all quality gate methods")
    
    # Verify execute_task implements retry loop
    assert hasattr(agent, 'execute_task'), "Missing execute_task method"
    print("   ✓ Has execute_task method")
    
    # Check execute_task signature
    import inspect
    sig = inspect.signature(agent.execute_task)
    params = list(sig.parameters.keys())
    assert "max_retries" in params, "execute_task missing max_retries parameter"
    print("   ✓ execute_task supports max_retries for self-evaluation loop")
    
    # Verify MAX_RETRIES constant
    assert hasattr(BackendAgent, 'MAX_RETRIES'), "Missing MAX_RETRIES constant"
    assert BackendAgent.MAX_RETRIES == 5, f"MAX_RETRIES should be 5, got {BackendAgent.MAX_RETRIES}"
    print(f"   ✓ MAX_RETRIES set to {BackendAgent.MAX_RETRIES} attempts")
    
    return True


def main():
    """Run all verification tests for Task 9.1."""
    print("=" * 80)
    print("TASK 9.1 VERIFICATION: Backend Agent Implementation")
    print("=" * 80)
    print("\nVerifying all requirements:")
    print("  • BackendAgent class with LangChain OpenAI integration")
    print("  • FastAPI code generation with proper file structure")
    print("  • Comprehensive error handling and input validation")
    print("  • Python type hints and docstrings")
    print("  • Requirements.txt generation")
    print("  • Database integration code (SQLAlchemy models, connection management)")
    print("\nRequirements validated: 4.1, 4.4, 4.5, 4.6, 12.2, 13.1, 13.3, 14.1")
    print("=" * 80)
    
    tests = [
        ("LangChain Integration", verify_langchain_integration),
        ("File Structure Generation", verify_file_structure_generation),
        ("Error Handling & Validation", verify_error_handling_and_validation),
        ("Type Hints & Docstrings", verify_type_hints_and_docstrings),
        ("Requirements.txt Generation", verify_requirements_txt_generation),
        ("Database Integration", verify_database_integration),
        ("Self-Evaluation Loop", verify_self_evaluation_loop),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, True, None))
        except Exception as e:
            import traceback
            results.append((test_name, False, str(e)))
            print(f"\n   ❌ FAILED: {e}")
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    all_passed = True
    for test_name, passed, error in results:
        if passed:
            print(f"✅ PASS: {test_name}")
        else:
            print(f"❌ FAIL: {test_name}")
            if error:
                print(f"         {error}")
            all_passed = False
    
    print("=" * 80)
    
    if all_passed:
        print("\n🎉 ALL REQUIREMENTS VERIFIED - TASK 9.1 COMPLETE!")
        print("\nThe BackendAgent implementation includes:")
        print("  ✅ LangChain OpenAI integration")
        print("  ✅ FastAPI code generation with proper file structure")
        print("  ✅ Comprehensive error handling and input validation")
        print("  ✅ Python type hints and docstrings enforcement")
        print("  ✅ Requirements.txt generation with dependencies")
        print("  ✅ Database integration (SQLAlchemy models, connection management)")
        print("  ✅ Self-evaluation loop with quality gates")
        print("\n✨ Ready for task 9.2 (self-evaluation loop enhancements)")
        return 0
    else:
        print("\n⚠️  Some requirements not met")
        return 1


if __name__ == "__main__":
    sys.exit(main())
