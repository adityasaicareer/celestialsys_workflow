#!/usr/bin/env python3
"""
Test script to verify Testing Agent import structure scanning works correctly.
"""

from pathlib import Path
from workflow.agents.testing_agent import TestingAgent

def test_backend_structure_scanning():
    """Test that backend structure scanning extracts correct import paths."""
    
    # Initialize testing agent
    testing_agent = TestingAgent()
    
    # Scan backend structure
    backend_path = Path("backend")
    if not backend_path.exists():
        print("❌ Backend directory not found")
        return False
    
    print("📂 Scanning backend structure...")
    structure = testing_agent._scan_backend_structure(backend_path)
    
    print("\n✅ Backend Structure Scan Results:")
    print(f"   Main file: {structure['main_file']}")
    print(f"   Modules found: {list(structure['modules'].keys())}")
    
    print("\n📋 Import Examples Extracted:")
    for name, import_path in structure['import_examples'].items():
        print(f"   {name:30} -> {import_path}")
    
    # Verify expected imports are found
    expected_classes = ['Todo', 'Base']
    expected_functions = ['create_todo', 'get_todo', 'list_todos', 'delete_todo', 'toggle_or_rename_todo']
    
    found_classes = [name for name in structure['import_examples'].keys() if name in expected_classes]
    found_functions = [name for name in structure['import_examples'].keys() if name in expected_functions]
    
    print(f"\n✅ Found {len(found_classes)}/{len(expected_classes)} expected classes")
    print(f"✅ Found {len(found_functions)}/{len(expected_functions)} expected functions")
    
    # Verify import paths are correct format
    all_imports_correct = all(
        import_path.startswith("from ") and " import " in import_path
        for import_path in structure['import_examples'].values()
    )
    
    if all_imports_correct:
        print("✅ All import paths use correct format (from X import Y)")
    else:
        print("❌ Some import paths have incorrect format")
        return False
    
    # Check specific important imports
    if 'Todo' in structure['import_examples']:
        todo_import = structure['import_examples']['Todo']
        print(f"\n📌 Todo import path: {todo_import}")
        if todo_import == "from models.todo import Todo":
            print("   ✅ Correct! (matches actual backend structure)")
        else:
            print(f"   ❌ Expected 'from models.todo import Todo', got '{todo_import}'")
    
    if 'create_todo' in structure['import_examples']:
        service_import = structure['import_examples']['create_todo']
        print(f"📌 create_todo import path: {service_import}")
        if service_import == "from services.todo_service import create_todo":
            print("   ✅ Correct! (matches actual backend structure)")
        else:
            print(f"   ❌ Expected 'from services.todo_service import create_todo', got '{service_import}'")
    
    print("\n🎉 Backend structure scanning is working correctly!")
    return True

if __name__ == "__main__":
    success = test_backend_structure_scanning()
    exit(0 if success else 1)
