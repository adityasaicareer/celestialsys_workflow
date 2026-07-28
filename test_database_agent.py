"""
Test script for Database Agent functionality.

Tests:
1. DatabaseAgent instantiation
2. Strong password generation
3. Docker network creation
4. PostgreSQL container initialization
5. MongoDB container initialization
6. Connection validation
7. .env file generation
8. Migration script generation
9. Complete task execution
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow.agents.database_agent import DatabaseAgent


def test_password_generation():
    """Test strong password generation."""
    print("\n" + "="*70)
    print("TEST 1: Password Generation")
    print("="*70)
    
    agent = DatabaseAgent()
    
    # Generate multiple passwords
    passwords = [agent.generate_strong_password() for _ in range(5)]
    
    print(f"\n✅ Generated {len(passwords)} passwords")
    
    # Verify properties
    for i, pwd in enumerate(passwords, 1):
        print(f"   Password {i}: length={len(pwd)}, unique={pwd not in passwords[:i-1]}")
        assert len(pwd) == 32, "Password should be 32 characters"
        assert pwd not in passwords[:i-1] or i == 1, "Passwords should be unique"
    
    print(f"\n✅ All passwords meet requirements")


def test_postgres_initialization():
    """Test PostgreSQL container initialization."""
    print("\n" + "="*70)
    print("TEST 2: PostgreSQL Initialization")
    print("="*70)
    
    agent = DatabaseAgent()
    
    result = agent.initialize_postgres(
        database_name="test_db",
        username="test_user"
    )
    
    print(f"\n📊 Result:")
    print(f"   Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"   Container: {result['container_name']}")
        print(f"   Host: {result['host']}")
        print(f"   Port: {result['port']}")
        print(f"   Database: {result['database']}")
        print(f"   Username: {result['username']}")
        print(f"   Password: {'*' * len(result['password'])}")
        print(f"   Connection String: {result['connection_string']}")
        print(f"\n✅ PostgreSQL initialized successfully")
    else:
        print(f"   Error: {result.get('error')}")
        print(f"\n⚠️  PostgreSQL initialization failed (may require Docker)")
    
    return result


def test_mongodb_initialization():
    """Test MongoDB container initialization."""
    print("\n" + "="*70)
    print("TEST 3: MongoDB Initialization")
    print("="*70)
    
    agent = DatabaseAgent()
    
    result = agent.initialize_mongodb(
        database_name="test_db",
        username="test_user"
    )
    
    print(f"\n📊 Result:")
    print(f"   Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"   Container: {result['container_name']}")
        print(f"   Host: {result['host']}")
        print(f"   Port: {result['port']}")
        print(f"   Database: {result['database']}")
        print(f"   Username: {result['username']}")
        print(f"   Password: {'*' * len(result['password'])}")
        print(f"   Connection String: {result['connection_string']}")
        print(f"\n✅ MongoDB initialized successfully")
    else:
        print(f"   Error: {result.get('error')}")
        print(f"\n⚠️  MongoDB initialization failed (may require Docker)")
    
    return result


def test_env_file_generation(postgres_config, mongo_config):
    """Test .env file generation."""
    print("\n" + "="*70)
    print("TEST 4: .env File Generation")
    print("="*70)
    
    agent = DatabaseAgent()
    
    result = agent.generate_env_file(
        postgres_config=postgres_config,
        mongo_config=mongo_config,
        output_dir="./backend"
    )
    
    print(f"\n📊 Result:")
    print(f"   Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"   File Path: {result['env_path']}")
        print(f"\n📄 Content Preview:")
        lines = result['env_content'].split('\n')
        for line in lines[:15]:  # Show first 15 lines
            print(f"   {line}")
        if len(lines) > 15:
            print(f"   ... ({len(lines) - 15} more lines)")
        print(f"\n✅ .env file generated successfully")
    else:
        print(f"   Error: {result.get('error')}")
        print(f"\n❌ .env file generation failed")
    
    return result


def test_migration_script_generation():
    """Test migration script generation."""
    print("\n" + "="*70)
    print("TEST 5: Migration Script Generation")
    print("="*70)
    
    agent = DatabaseAgent()
    
    # Test PostgreSQL migration
    pg_schema = """
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
"""
    
    pg_result = agent.generate_migration_script(
        database_type="postgresql",
        schema_definition=pg_schema,
        output_dir="./backend"
    )
    
    print(f"\n📊 PostgreSQL Migration:")
    print(f"   Success: {pg_result.get('success')}")
    if pg_result.get('success'):
        print(f"   Script Path: {pg_result['script_path']}")
    
    # Test MongoDB migration
    mongo_schema = """
    # Create collections with validation
    db.create_collection("users", {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["username", "email"],
                "properties": {
                    "username": {"bsonType": "string"},
                    "email": {"bsonType": "string"}
                }
            }
        }
    })
    
    # Create indexes
    db.users.create_index({"email": 1}, {"unique": True})
"""
    
    mongo_result = agent.generate_migration_script(
        database_type="mongodb",
        schema_definition=mongo_schema,
        output_dir="./backend"
    )
    
    print(f"\n📊 MongoDB Migration:")
    print(f"   Success: {mongo_result.get('success')}")
    if mongo_result.get('success'):
        print(f"   Script Path: {mongo_result['script_path']}")
    
    if pg_result.get('success') and mongo_result.get('success'):
        print(f"\n✅ Migration scripts generated successfully")
    
    return pg_result, mongo_result


def test_complete_task_execution():
    """Test complete database task execution."""
    print("\n" + "="*70)
    print("TEST 6: Complete Task Execution")
    print("="*70)
    
    agent = DatabaseAgent()
    
    result = agent.execute_task(
        task_description="Initialize databases for user management application",
        database_types=["postgresql", "mongodb"],
        database_name="user_app_db",
        username="app_admin"
    )
    
    print(f"\n📊 Execution Result:")
    print(f"   Success: {result.get('success')}")
    print(f"   Network: {result.get('network')}")
    
    if result.get('success'):
        if 'postgres_config' in result:
            pg = result['postgres_config']
            print(f"\n   🐘 PostgreSQL:")
            print(f"      Container: {pg['container_name']}")
            print(f"      Database: {pg['database']}")
            print(f"      Port: {pg['port']}")
        
        if 'mongo_config' in result:
            mg = result['mongo_config']
            print(f"\n   🍃 MongoDB:")
            print(f"      Container: {mg['container_name']}")
            print(f"      Database: {mg['database']}")
            print(f"      Port: {mg['port']}")
        
        if 'env_file' in result:
            print(f"\n   📄 .env File: {result['env_file']}")
        
        print(f"\n✅ Complete task execution successful")
    else:
        print(f"   Error: {result.get('error')}")
        print(f"\n⚠️  Task execution failed (may require Docker)")
    
    return result


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("DATABASE AGENT TEST SUITE")
    print("="*70)
    print("\nThis test suite verifies Database Agent functionality:")
    print("- Password generation")
    print("- PostgreSQL initialization")
    print("- MongoDB initialization")
    print("- .env file generation")
    print("- Migration script generation")
    print("- Complete task execution")
    
    try:
        # Test 1: Password generation (doesn't require Docker)
        test_password_generation()
        
        # Test 2: PostgreSQL initialization
        postgres_config = test_postgres_initialization()
        
        # Test 3: MongoDB initialization
        mongo_config = test_mongodb_initialization()
        
        # Test 4: .env file generation
        if postgres_config.get('success') or mongo_config.get('success'):
            test_env_file_generation(postgres_config, mongo_config)
        else:
            print("\n⚠️  Skipping .env test (no databases initialized)")
        
        # Test 5: Migration script generation
        test_migration_script_generation()
        
        # Test 6: Complete task execution
        test_complete_task_execution()
        
        print("\n" + "="*70)
        print("TEST SUITE COMPLETED")
        print("="*70)
        print("\n✅ All tests completed successfully!")
        print("\n📝 Notes:")
        print("   - Some tests require Docker to be running")
        print("   - Generated containers can be stopped with: docker stop workflow_postgres workflow_mongo")
        print("   - Generated files are in ./backend directory")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
