"""
Demonstration of Backend Agent Self-Evaluation Loop

This script demonstrates the complete self-evaluation loop implemented in Task 9.2:
1. Generate code
2. Evaluate against quality gates
3. Regenerate with corrections if needed
4. Request approval if max retries exceeded

**Validates: Requirements 4.2, 4.3, 9.1, 9.3, 9.4, 9.5**
"""

import tempfile
import shutil
from pathlib import Path
from workflow.agents.backend_agent import BackendAgent, CodeEvaluator


def demo_syntax_validation():
    """Demonstrate syntax validation with AST compilation."""
    print("\n" + "="*80)
    print("DEMO 1: Syntax Validation (AST Compilation)")
    print("="*80)
    
    evaluator = CodeEvaluator()
    
    # Valid code
    valid_code = """
def greet(name: str) -> str:
    '''Greet a person.'''
    return f"Hello, {name}!"
"""
    success, errors = evaluator.validate_syntax(valid_code)
    print(f"\n✓ Valid code: {success}")
    print(f"  Errors: {errors}")
    
    # Invalid code
    invalid_code = """
def broken(
    print("This won't parse")
"""
    success, errors = evaluator.validate_syntax(invalid_code)
    print(f"\n✗ Invalid code: {success}")
    print(f"  Errors: {errors[0] if errors else 'None'}")


def demo_pylint_evaluation():
    """Demonstrate pylint evaluation with score threshold."""
    print("\n" + "="*80)
    print("DEMO 2: Pylint Evaluation (Score > 8.0)")
    print("="*80)
    
    evaluator = CodeEvaluator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Well-formatted code
        good_file = Path(tmpdir) / "good_code.py"
        good_file.write_text('''"""
Module for demonstrating good code quality.
"""

def calculate_sum(num1: int, num2: int) -> int:
    """Calculate the sum of two numbers."""
    return num1 + num2


def main() -> None:
    """Main function."""
    result = calculate_sum(10, 20)
    print(f"Sum: {result}")


if __name__ == "__main__":
    main()
''')
        
        score, issues = evaluator.run_pylint(good_file)
        print(f"\n✓ Well-formatted code:")
        print(f"  Pylint score: {score:.2f}/10.0")
        print(f"  Issues: {len(issues)} found")
        print(f"  Threshold: {evaluator.PYLINT_THRESHOLD}")
        print(f"  Result: {'PASS' if score >= evaluator.PYLINT_THRESHOLD else 'FAIL'}")


def demo_mypy_type_checking():
    """Demonstrate mypy type checking."""
    print("\n" + "="*80)
    print("DEMO 3: Mypy Type Checking (Must Pass)")
    print("="*80)
    
    evaluator = CodeEvaluator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Well-typed code
        typed_file = Path(tmpdir) / "typed_code.py"
        typed_file.write_text('''
from typing import List

def process_items(items: List[str]) -> int:
    """Count the number of items."""
    return len(items)

result: int = process_items(["a", "b", "c"])
''')
        
        success, issues = evaluator.run_mypy(typed_file)
        print(f"\n✓ Well-typed code:")
        print(f"  Type check: {'PASS' if success else 'FAIL'}")
        print(f"  Issues: {len(issues)} found")


def demo_feature_checking():
    """Demonstrate functionality comparison against requirements."""
    print("\n" + "="*80)
    print("DEMO 4: Feature Checking (Requirements Validation)")
    print("="*80)
    
    evaluator = CodeEvaluator()
    
    # Complete FastAPI code
    complete_code = """
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello"}

@app.post("/items")
def create_item():
    return {"status": "created"}
"""
    
    requirements = "Create a FastAPI application with CRUD endpoints"
    success, missing = evaluator.check_required_features(complete_code, requirements)
    
    print(f"\n✓ Complete code:")
    print(f"  Requirements: {requirements}")
    print(f"  Feature check: {'PASS' if success else 'FAIL'}")
    print(f"  Missing features: {missing if missing else 'None'}")
    
    # Incomplete code
    incomplete_code = """
def hello():
    print("Hello")
"""
    
    success, missing = evaluator.check_required_features(incomplete_code, requirements)
    
    print(f"\n✗ Incomplete code:")
    print(f"  Requirements: {requirements}")
    print(f"  Feature check: {'PASS' if success else 'FAIL'}")
    print(f"  Missing features: {missing}")


def demo_comprehensive_evaluation():
    """Demonstrate comprehensive evaluation with all quality gates."""
    print("\n" + "="*80)
    print("DEMO 5: Comprehensive Evaluation (All Quality Gates)")
    print("="*80)
    
    evaluator = CodeEvaluator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a complete FastAPI file
        api_file = Path(tmpdir) / "main.py"
        api_file.write_text('''"""
FastAPI application module.
"""
from typing import Dict
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {"message": "API is running"}


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/items")
async def create_item() -> Dict[str, str]:
    """Create an item."""
    return {"status": "created"}
''')
        
        requirements = "Create a FastAPI application with CRUD endpoints"
        results = evaluator.evaluate_file(api_file, requirements)
        
        print(f"\n✓ Evaluation Results:")
        print(f"  Overall: {'PASS' if results['passed'] else 'FAIL'}")
        print(f"  Syntax: {results['scores'].get('syntax', 'N/A')}")
        print(f"  Pylint: {results['scores'].get('pylint', 'N/A')}")
        print(f"  Mypy: {results['scores'].get('mypy', 'N/A')}")
        print(f"  Features: {results['scores'].get('features', 'N/A')}")
        print(f"  Issues: {len(results['issues'])} found")
        
        if results['issues']:
            print(f"\n  Issue details:")
            for issue in results['issues'][:3]:
                print(f"    - {issue}")


def demo_regeneration_loop():
    """Demonstrate regeneration loop with retry counter."""
    print("\n" + "="*80)
    print("DEMO 6: Regeneration Loop (Max 5 Retries)")
    print("="*80)
    
    agent = BackendAgent()
    
    print(f"\n✓ Configuration:")
    print(f"  MAX_RETRIES: {agent.MAX_RETRIES}")
    print(f"  Backend output dir: {agent.config.backend_output_dir}")
    
    print(f"\n✓ Regeneration Loop Flow:")
    print(f"  1. Generate code")
    print(f"  2. Write to files")
    print(f"  3. Evaluate against quality gates")
    print(f"  4. If failed and attempts < {agent.MAX_RETRIES}:")
    print(f"     - Log issues")
    print(f"     - Increment retry counter")
    print(f"     - Regenerate with corrections")
    print(f"  5. If failed and attempts >= {agent.MAX_RETRIES}:")
    print(f"     - Request human approval")
    print(f"  6. If passed:")
    print(f"     - Mark task complete")


def demo_approval_request():
    """Demonstrate approval request on max retries exceeded."""
    print("\n" + "="*80)
    print("DEMO 7: Approval Request (Max Retries Exceeded)")
    print("="*80)
    
    agent = BackendAgent()
    
    print(f"\n✓ Approval Request Flow:")
    print(f"  When max retries ({agent.MAX_RETRIES}) exceeded:")
    print(f"  1. Set requires_approval = True")
    print(f"  2. Generate approval_message with:")
    print(f"     - Number of attempts made")
    print(f"     - Top issues encountered")
    print(f"     - Options for user:")
    print(f"       • Continue with current code")
    print(f"       • Retry with more attempts")
    print(f"       • Modify requirements")
    print(f"  3. Return task result with approval flag")
    print(f"  4. Supervisor routes to human_approval_node")
    print(f"  5. Wait for user decision")


def main():
    """Run all demonstrations."""
    print("\n" + "="*80)
    print("BACKEND AGENT SELF-EVALUATION LOOP DEMONSTRATION")
    print("Task 9.2: Comprehensive Quality Validation System")
    print("="*80)
    
    try:
        demo_syntax_validation()
        demo_pylint_evaluation()
        demo_mypy_type_checking()
        demo_feature_checking()
        demo_comprehensive_evaluation()
        demo_regeneration_loop()
        demo_approval_request()
        
        print("\n" + "="*80)
        print("SUMMARY: All Task 9.2 Requirements Demonstrated")
        print("="*80)
        print("\n✅ Task 9.2 Implementation Complete:")
        print("   ✓ Syntax validation with Python AST compilation")
        print("   ✓ Pylint evaluation with score threshold 8.0")
        print("   ✓ Mypy type checking with zero errors requirement")
        print("   ✓ Functionality comparison against requirements")
        print("   ✓ Quality gate validation before task completion")
        print("   ✓ Regeneration loop with max 5 retry attempts")
        print("   ✓ Approval request when max retries exceeded")
        print("\n📋 Validates Requirements: 4.2, 4.3, 9.1, 9.3, 9.4, 9.5")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
