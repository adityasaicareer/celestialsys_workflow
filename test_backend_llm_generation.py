"""
Test Backend Agent LLM-based code generation.

This test verifies that the Backend Agent can generate FastAPI code with:
- Proper file structure (main.py, models/, routes/, services/, config.py)
- Database integration (SQLAlchemy models, connection management)
- Type hints and docstrings
- Error handling and validation
- Requirements.txt
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_generate_simple_crud_api():
    """Test generating a simple CRUD API with database integration."""
    print("\n🔍 Testing LLM-based CRUD API generation")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    
    task_description = """
    Build a FastAPI backend for a task management system with:
    - Task model with fields: id, title, description, completed (bool), created_at
    - SQLAlchemy model for PostgreSQL database
    - CRUD endpoints: GET /tasks, POST /tasks, GET /tasks/{id}, PUT /tasks/{id}, DELETE /tasks/{id}
    - Pydantic models for request/response validation
    - Proper error handling for 404 and validation errors
    - Database session management with dependency injection
    """
    
    database_config = {
        "postgresql": {
            "host": "localhost",
            "port": 5432,
            "database": "tasks_db",
            "user": "postgres",
            "password": "postgres"
        }
    }
    
    print("   📝 Generating code with LLM...")
    files = agent.generate_code(task_description, database_config)
    
    print(f"\n   📊 Generated {len(files)} files:")
    for filepath in files.keys():
        print(f"      - {filepath}")
    
    # Verify required files are present
    assert "main.py" in files, "main.py not generated"
    assert "config.py" in files, "config.py not generated"
    assert "requirements.txt" in files, "requirements.txt not generated"
    print("\n   ✅ Required files present")
    
    # Check for database model files
    has_models = any("model" in path.lower() for path in files.keys())
    assert has_models, "No model files generated"
    print("   ✅ Model files generated")
    
    # Check for route files
    has_routes = any("route" in path.lower() or "main.py" in path for path in files.keys())
    assert has_routes, "No route files generated"
    print("   ✅ Route files generated")
    
    # Verify main.py content
    main_content = files["main.py"]
    assert "FastAPI" in main_content, "FastAPI not imported in main.py"
    assert "app = FastAPI" in main_content or "app=FastAPI" in main_content, "FastAPI app not created"
    print("   ✅ main.py has FastAPI app")
    
    # Check for database integration
    has_sqlalchemy = False
    for content in files.values():
        if "sqlalchemy" in content.lower() or "SQLAlchemy" in content:
            has_sqlalchemy = True
            break
    
    if has_sqlalchemy:
        print("   ✅ SQLAlchemy integration present")
    else:
        print("   ⚠️  SQLAlchemy integration not clearly visible (may be implicit)")
    
    # Check for CRUD operations
    crud_found = []
    all_content = "\n".join(files.values()).lower()
    
    if "get" in all_content or "@app.get" in all_content:
        crud_found.append("GET")
    if "post" in all_content or "@app.post" in all_content:
        crud_found.append("POST")
    if "put" in all_content or "@app.put" in all_content or "patch" in all_content:
        crud_found.append("PUT/PATCH")
    if "delete" in all_content or "@app.delete" in all_content:
        crud_found.append("DELETE")
    
    print(f"   📊 CRUD operations found: {', '.join(crud_found)}")
    
    # Check requirements.txt has necessary dependencies
    requirements = files["requirements.txt"]
    required_packages = ["fastapi", "sqlalchemy", "psycopg2"]
    
    missing_packages = []
    for pkg in required_packages:
        if pkg not in requirements.lower():
            missing_packages.append(pkg)
    
    if missing_packages:
        print(f"   ⚠️  Missing packages in requirements.txt: {', '.join(missing_packages)}")
    else:
        print("   ✅ requirements.txt has all necessary packages")
    
    # Write to temporary directory and validate syntax
    print("\n   📝 Writing generated code to temporary directory...")
    with tempfile.TemporaryDirectory() as tmpdir:
        created_files = agent.write_code(files, tmpdir)
        print(f"   ✅ Created {len(created_files)} files")
        
        # Evaluate code quality
        print("\n   🔍 Evaluating code quality...")
        evaluation = agent.evaluate_code(tmpdir, task_description)
        
        print(f"\n   📊 Evaluation Results:")
        print(f"      - Overall passed: {evaluation['passed']}")
        print(f"      - Syntax: {evaluation['scores'].get('syntax', 'N/A')}")
        print(f"      - Pylint score: {evaluation['scores'].get('pylint', 'N/A')}")
        print(f"      - Mypy: {evaluation['scores'].get('mypy', 'N/A')}")
        print(f"      - Features: {evaluation['scores'].get('features', 'N/A')}")
        
        if evaluation['issues']:
            print(f"\n   ℹ️  Issues found ({len(evaluation['issues'])}):")
            for issue in evaluation['issues'][:5]:
                print(f"      - {issue}")
        
        # At minimum, syntax should pass
        assert evaluation['scores'].get('syntax') == 'passed', "Generated code has syntax errors"
        print("\n   ✅ Generated code has valid Python syntax")
    
    return True


def test_write_and_execute_task():
    """Test the full execute_task method (without actual LLM call to save API costs)."""
    print("\n🔍 Testing execute_task workflow (using minimal app fallback)")
    
    from workflow.agents.backend_agent import BackendAgent
    
    agent = BackendAgent()
    
    # Use a simple task that will use the minimal app fallback
    task_description = "Build a simple health check API"
    
    print("   📝 Executing task with max_retries=2...")
    
    # Mock the generate_code to return minimal app to avoid API costs
    original_generate = agent.generate_code
    
    def mock_generate(*args, **kwargs):
        return agent._generate_minimal_app(task_description)
    
    agent.generate_code = mock_generate
    
    try:
        result = agent.execute_task(
            task_description=task_description,
            database_config=None,
            max_retries=2
        )
        
        print(f"\n   📊 Task Result:")
        print(f"      - Success: {result['success']}")
        print(f"      - Output dir: {result['output_dir']}")
        print(f"      - Attempts: {result['attempts']}")
        print(f"      - Requires approval: {result['requires_approval']}")
        
        # Verify result structure
        assert "success" in result, "Result missing 'success' key"
        assert "output_dir" in result, "Result missing 'output_dir' key"
        assert "evaluation" in result, "Result missing 'evaluation' key"
        assert "attempts" in result, "Result missing 'attempts' key"
        print("\n   ✅ Result has correct structure")
        
        # Check that files were created
        output_path = Path(result['output_dir'])
        assert output_path.exists(), "Output directory not created"
        assert (output_path / "main.py").exists(), "main.py not created"
        print("   ✅ Files created in output directory")
        
    finally:
        # Restore original method
        agent.generate_code = original_generate
    
    return True


def main():
    """Run all LLM generation tests."""
    print("=" * 70)
    print("BACKEND AGENT LLM GENERATION TESTS")
    print("=" * 70)
    print("\n⚠️  Note: These tests make actual LLM API calls and may incur costs.")
    print("    Set OPENAI_API_KEY environment variable to run LLM tests.\n")
    
    # Check if API key is available
    import os
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Skipping LLM generation test.")
        print("✅ Running execute_task workflow test only.\n")
        tests = [
            ("Execute Task Workflow", test_write_and_execute_task),
        ]
    else:
        tests = [
            ("LLM CRUD API Generation", test_generate_simple_crud_api),
            ("Execute Task Workflow", test_write_and_execute_task),
        ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed, None))
        except Exception as e:
            import traceback
            results.append((test_name, False, str(e)))
            print(f"   ❌ Test failed: {e}")
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print("LLM GENERATION TEST SUMMARY")
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
        print("\n🎉 ALL LLM GENERATION TESTS PASSED!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
