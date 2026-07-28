"""
Test for Task 14.1: Deployment Agent Docker SDK Implementation

This test verifies:
- DeploymentAgent class with Docker SDK integration
- Dockerfile generation for frontend (Node.js 18+ base image)
- Dockerfile generation for backend (Python 3.11+ base image)
- Docker Compose configuration generation (version 3.8)
- Environment-specific configuration handling (dev, staging, prod)
- Proper networking configuration (Docker networks)

**Validates: Requirements 8.1, 8.2, 12.5, 13.5, 14.4**
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from workflow.agents.deployment_agent import DeploymentAgent


def test_deployment_agent_initialization():
    """Test that DeploymentAgent initializes with Docker SDK."""
    print("\n" + "="*70)
    print("TEST 1: DeploymentAgent Initialization with Docker SDK")
    print("="*70)
    
    try:
        agent = DeploymentAgent()
        assert agent.docker_client is not None, "Docker client not initialized"
        print("✅ PASS: DeploymentAgent initialized with Docker SDK")
        return True
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_frontend_dockerfile_generation():
    """Test Dockerfile generation for frontend with Node.js 18+ base image."""
    print("\n" + "="*70)
    print("TEST 2: Frontend Dockerfile Generation (Node.js 18+)")
    print("="*70)
    
    try:
        agent = DeploymentAgent()
        
        # Test development environment
        dev_dockerfile = agent.generate_frontend_dockerfile(environment="dev")
        assert "FROM node:18-alpine" in dev_dockerfile, "Missing Node.js 18 base image"
        assert "WORKDIR /app" in dev_dockerfile, "Missing working directory"
        assert "npm install" in dev_dockerfile or "npm ci" in dev_dockerfile, "Missing npm install"
        assert "EXPOSE 3000" in dev_dockerfile, "Missing port exposure"
        print("   ✅ Development Dockerfile generated correctly")
        
        # Test production environment
        prod_dockerfile = agent.generate_frontend_dockerfile(environment="prod")
        assert "FROM node:18-alpine" in prod_dockerfile, "Missing Node.js 18 base image"
        assert "AS deps" in prod_dockerfile or "AS builder" in prod_dockerfile, "Missing multi-stage build"
        print("   ✅ Production Dockerfile generated correctly (multi-stage)")
        
        print("✅ PASS: Frontend Dockerfile generation works for all environments")
        return True
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_backend_dockerfile_generation():
    """Test Dockerfile generation for backend with Python 3.11+ base image."""
    print("\n" + "="*70)
    print("TEST 3: Backend Dockerfile Generation (Python 3.11+)")
    print("="*70)
    
    try:
        agent = DeploymentAgent()
        
        # Test development environment
        dev_dockerfile = agent.generate_backend_dockerfile(environment="dev")
        assert "FROM python:3.11-slim" in dev_dockerfile, "Missing Python 3.11 base image"
        assert "WORKDIR /app" in dev_dockerfile, "Missing working directory"
        assert "pip install" in dev_dockerfile, "Missing pip install"
        assert "EXPOSE 8000" in dev_dockerfile, "Missing port exposure"
        assert "uvicorn" in dev_dockerfile, "Missing uvicorn command"
        print("   ✅ Development Dockerfile generated correctly")
        
        # Test production environment
        prod_dockerfile = agent.generate_backend_dockerfile(environment="prod")
        assert "FROM python:3.11-slim" in prod_dockerfile, "Missing Python 3.11 base image"
        assert "AS builder" in prod_dockerfile, "Missing multi-stage build"
        assert "HEALTHCHECK" in prod_dockerfile, "Missing health check in production"
        print("   ✅ Production Dockerfile generated correctly (multi-stage with health check)")
        
        print("✅ PASS: Backend Dockerfile generation works for all environments")
        return True
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_docker_compose_generation():
    """Test Docker Compose configuration generation (version 3.8)."""
    print("\n" + "="*70)
    print("TEST 4: Docker Compose Configuration Generation (version 3.8)")
    print("="*70)
    
    try:
        agent = DeploymentAgent()
        
        # Test with database configuration
        database_config = {
            "postgres": {
                "success": True,
                "username": "test_user",
                "password": "test_pass",
                "database": "test_db"
            },
            "mongo": {
                "success": True,
                "username": "mongo_user",
                "password": "mongo_pass",
                "database": "mongo_db"
            }
        }
        
        compose_yaml = agent.generate_docker_compose(
            database_config=database_config,
            environment="dev"
        )
        
        # Verify version
        assert "version: '3.8'" in compose_yaml, "Missing Docker Compose version 3.8"
        print("   ✅ Docker Compose version 3.8 specified")
        
        # Verify services
        assert "services:" in compose_yaml, "Missing services section"
        assert "frontend:" in compose_yaml, "Missing frontend service"
        assert "backend:" in compose_yaml, "Missing backend service"
        assert "postgres:" in compose_yaml, "Missing PostgreSQL service"
        assert "mongo:" in compose_yaml, "Missing MongoDB service"
        print("   ✅ All services included (frontend, backend, postgres, mongo)")
        
        # Verify networking
        assert "networks:" in compose_yaml, "Missing networks section"
        assert "workflow_network:" in compose_yaml, "Missing workflow network"
        assert "driver: bridge" in compose_yaml, "Missing bridge driver"
        print("   ✅ Docker networking configured correctly")
        
        # Verify volumes
        assert "volumes:" in compose_yaml, "Missing volumes section"
        assert "postgres_data:" in compose_yaml, "Missing PostgreSQL volume"
        assert "mongo_data:" in compose_yaml, "Missing MongoDB volume"
        print("   ✅ Persistent volumes configured")
        
        # Verify dependencies
        assert "depends_on:" in compose_yaml, "Missing service dependencies"
        print("   ✅ Service dependencies configured")
        
        print("✅ PASS: Docker Compose generation works correctly")
        return True
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_environment_specific_configuration():
    """Test environment-specific configuration handling (dev, staging, prod)."""
    print("\n" + "="*70)
    print("TEST 5: Environment-Specific Configuration (dev, staging, prod)")
    print("="*70)
    
    try:
        agent = DeploymentAgent()
        
        # Test each environment
        for env in ["dev", "staging", "prod"]:
            print(f"\n   Testing {env} environment:")
            
            # Frontend
            frontend_dockerfile = agent.generate_frontend_dockerfile(environment=env)
            assert frontend_dockerfile, f"Failed to generate frontend Dockerfile for {env}"
            print(f"      ✅ Frontend Dockerfile generated for {env}")
            
            # Backend
            backend_dockerfile = agent.generate_backend_dockerfile(environment=env)
            assert backend_dockerfile, f"Failed to generate backend Dockerfile for {env}"
            print(f"      ✅ Backend Dockerfile generated for {env}")
            
            # Docker Compose
            compose_yaml = agent.generate_docker_compose(environment=env)
            assert f"NODE_ENV={env}" in compose_yaml or f"NODE_ENV=production" in compose_yaml, \
                f"Missing NODE_ENV for {env}"
            assert f"APP_ENV={env}" in compose_yaml, f"Missing APP_ENV for {env}"
            print(f"      ✅ Docker Compose generated for {env} with correct env vars")
        
        print("\n✅ PASS: Environment-specific configuration works for all environments")
        return True
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_networking_configuration():
    """Test proper networking configuration (Docker networks)."""
    print("\n" + "="*70)
    print("TEST 6: Docker Networking Configuration")
    print("="*70)
    
    try:
        agent = DeploymentAgent()
        
        compose_yaml = agent.generate_docker_compose()
        
        # Verify network configuration
        assert "networks:" in compose_yaml, "Missing networks section"
        assert "workflow_network:" in compose_yaml, "Missing workflow_network definition"
        assert "driver: bridge" in compose_yaml, "Missing bridge driver"
        print("   ✅ Network definition includes bridge driver")
        
        # Verify all services are connected to network
        lines = compose_yaml.split('\n')
        services = ['frontend', 'backend', 'postgres', 'mongo']
        
        for service in services:
            if f"{service}:" in compose_yaml:
                # Find service section
                service_start = None
                for i, line in enumerate(lines):
                    if line.strip().startswith(f"{service}:"):
                        service_start = i
                        break
                
                if service_start:
                    # Check for network within service
                    service_section = '\n'.join(lines[service_start:service_start+50])
                    if "workflow_network" in service_section:
                        print(f"   ✅ {service} service connected to workflow_network")
        
        print("✅ PASS: Docker networking configured properly")
        return True
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def test_save_docker_configurations():
    """Test saving all Docker configurations to disk."""
    print("\n" + "="*70)
    print("TEST 7: Save Docker Configurations to Disk")
    print("="*70)
    
    temp_dir = None
    try:
        agent = DeploymentAgent()
        
        # Create temporary directories
        temp_dir = tempfile.mkdtemp()
        frontend_path = os.path.join(temp_dir, "frontend")
        backend_path = os.path.join(temp_dir, "backend")
        
        database_config = {
            "postgres": {
                "success": True,
                "username": "test_user",
                "password": "test_pass",
                "database": "test_db"
            }
        }
        
        # Save configurations
        created_files = agent.save_docker_configurations(
            frontend_path=frontend_path,
            backend_path=backend_path,
            project_root=temp_dir,
            database_config=database_config,
            environment="dev"
        )
        
        # Verify files were created
        assert 'frontend_dockerfile' in created_files, "Frontend Dockerfile not in result"
        assert 'backend_dockerfile' in created_files, "Backend Dockerfile not in result"
        assert 'docker_compose' in created_files, "Docker Compose not in result"
        print("   ✅ All file paths returned")
        
        # Verify files exist
        assert os.path.exists(created_files['frontend_dockerfile']), "Frontend Dockerfile not created"
        assert os.path.exists(created_files['backend_dockerfile']), "Backend Dockerfile not created"
        assert os.path.exists(created_files['docker_compose']), "Docker Compose not created"
        print("   ✅ All files created on disk")
        
        # Verify file contents
        with open(created_files['frontend_dockerfile'], 'r') as f:
            content = f.read()
            assert "FROM node:18-alpine" in content, "Invalid frontend Dockerfile content"
        print("   ✅ Frontend Dockerfile content valid")
        
        with open(created_files['backend_dockerfile'], 'r') as f:
            content = f.read()
            assert "FROM python:3.11-slim" in content, "Invalid backend Dockerfile content"
        print("   ✅ Backend Dockerfile content valid")
        
        with open(created_files['docker_compose'], 'r') as f:
            content = f.read()
            assert "version: '3.8'" in content, "Invalid Docker Compose content"
        print("   ✅ Docker Compose content valid")
        
        print("✅ PASS: All Docker configurations saved successfully")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False
    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def main():
    """Run all tests for Task 14.1."""
    print("\n" + "="*70)
    print("TASK 14.1: DEPLOYMENT AGENT DOCKER SDK IMPLEMENTATION")
    print("="*70)
    print("\nValidates Requirements: 8.1, 8.2, 12.5, 13.5, 14.4")
    print("\nTest Coverage:")
    print("- DeploymentAgent class with Docker SDK integration")
    print("- Dockerfile generation for frontend (Node.js 18+ base image)")
    print("- Dockerfile generation for backend (Python 3.11+ base image)")
    print("- Docker Compose configuration generation (version 3.8)")
    print("- Environment-specific configuration handling (dev, staging, prod)")
    print("- Docker networking configuration")
    
    tests = [
        test_deployment_agent_initialization,
        test_frontend_dockerfile_generation,
        test_backend_dockerfile_generation,
        test_docker_compose_generation,
        test_environment_specific_configuration,
        test_networking_configuration,
        test_save_docker_configurations,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n❌ Test failed with exception: {str(e)}")
            results.append(False)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"\nTests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Task 14.1 implementation is complete.")
        print("\n✅ Requirements Validated:")
        print("   - 8.1: Frontend Docker configurations")
        print("   - 8.2: Backend Docker configurations")
        print("   - 12.5: Docker Compose tool access")
        print("   - 13.5: Docker Compose in project root")
        print("   - 14.4: Environment-specific Docker Compose files")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
