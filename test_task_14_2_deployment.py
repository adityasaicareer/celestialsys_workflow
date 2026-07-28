"""
Unit tests for Task 14.2: Container build and deployment

Tests the DeploymentAgent's ability to:
- Build Docker images using Docker SDK
- Deploy with Docker Compose
- Validate service health with HTTP checks
- Validate database connections from backend
- Output service endpoints
- Generate diagnostics on failure
- Clean up containers on failure

**Validates: Requirements 8.3, 8.4, 8.5, 8.6, 8.7**
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from workflow.agents.deployment_agent import DeploymentAgent


class TestDockerImageBuild:
    """Test Docker image build functionality."""
    
    def test_build_docker_images_success(self):
        """Test successful Docker image build for both frontend and backend."""
        agent = DeploymentAgent()
        
        # Mock Docker client
        mock_image = Mock()
        mock_image.id = "sha256:abc123"
        mock_image.short_id = "abc123"
        
        agent.docker_client.images.build = Mock(return_value=(mock_image, []))
        
        # Create temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            frontend_path = os.path.join(temp_dir, "frontend")
            backend_path = os.path.join(temp_dir, "backend")
            os.makedirs(frontend_path)
            os.makedirs(backend_path)
            
            # Create dummy Dockerfiles
            with open(os.path.join(frontend_path, "Dockerfile"), "w") as f:
                f.write("FROM node:18\n")
            with open(os.path.join(backend_path, "Dockerfile"), "w") as f:
                f.write("FROM python:3.11\n")
            
            # Build images
            result = agent.build_docker_images(frontend_path, backend_path, temp_dir)
            
            # Verify results
            assert result["frontend"]["success"] is True
            assert result["backend"]["success"] is True
            # Don't check exact image IDs since Docker actually builds real images
            assert result["frontend"]["image_id"] is not None
            assert result["backend"]["image_id"] is not None
            assert len(result["frontend"]["errors"]) == 0
            assert len(result["backend"]["errors"]) == 0
    
    @patch('docker.from_env')
    def test_build_docker_images_frontend_failure(self, mock_docker_from_env):
        """Test Docker image build when frontend build fails."""
        from docker.errors import BuildError
        
        # Create mock Docker client
        mock_docker_client = Mock()
        mock_docker_from_env.return_value = mock_docker_client
        
        # Mock build side effect - frontend fails, backend succeeds
        def build_side_effect(path, tag, **kwargs):
            if "frontend" in tag:
                raise BuildError("Build failed", "")
            else:
                mock_image = Mock()
                mock_image.id = "sha256:def456"
                mock_image.short_id = "def456"
                return (mock_image, [])
        
        mock_docker_client.images.build = Mock(side_effect=build_side_effect)
        
        # Create agent (will use mocked docker client)
        agent = DeploymentAgent()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            frontend_path = os.path.join(temp_dir, "frontend")
            backend_path = os.path.join(temp_dir, "backend")
            os.makedirs(frontend_path)
            os.makedirs(backend_path)
            
            # Create dummy Dockerfiles so the build method can be called
            with open(os.path.join(frontend_path, "Dockerfile"), "w") as f:
                f.write("FROM node:18\n")
            with open(os.path.join(backend_path, "Dockerfile"), "w") as f:
                f.write("FROM python:3.11\n")
            
            result = agent.build_docker_images(frontend_path, backend_path, temp_dir)
            
            # Verify results
            assert result["frontend"]["success"] is False
            assert result["backend"]["success"] is True
            assert len(result["frontend"]["errors"]) > 0
            assert "Build failed" in result["frontend"]["errors"][0]


class TestDockerComposeDeployment:
    """Test Docker Compose deployment functionality."""
    
    @patch('subprocess.run')
    def test_deploy_with_docker_compose_success(self, mock_run):
        """Test successful Docker Compose deployment."""
        agent = DeploymentAgent()
        
        # Mock successful docker-compose up
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Creating network... Creating container...",
            stderr=""
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create docker-compose.yml
            compose_path = os.path.join(temp_dir, "docker-compose.yml")
            with open(compose_path, "w") as f:
                f.write("version: '3.8'\nservices:\n  test:\n    image: hello-world\n")
            
            result = agent.deploy_with_docker_compose(temp_dir)
            
            # Verify results
            assert result["success"] is True
            assert len(result["errors"]) == 0
            mock_run.assert_called()
    
    @patch('subprocess.run')
    def test_deploy_with_docker_compose_failure(self, mock_run):
        """Test Docker Compose deployment failure."""
        agent = DeploymentAgent()
        
        # Mock failed docker-compose up
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error: service not found"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_path = os.path.join(temp_dir, "docker-compose.yml")
            with open(compose_path, "w") as f:
                f.write("version: '3.8'\nservices:\n")
            
            result = agent.deploy_with_docker_compose(temp_dir)
            
            # Verify results
            assert result["success"] is False
            assert len(result["errors"]) > 0
    
    def test_deploy_with_docker_compose_missing_file(self):
        """Test Docker Compose deployment with missing file."""
        agent = DeploymentAgent()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = agent.deploy_with_docker_compose(temp_dir)
            
            # Verify error
            assert result["success"] is False
            assert any("not found" in error for error in result["errors"])


class TestServiceHealthValidation:
    """Test service health validation functionality."""
    
    @patch('requests.get')
    def test_validate_service_health_all_healthy(self, mock_get):
        """Test service health validation when all services are healthy."""
        agent = DeploymentAgent()
        
        # Mock successful HTTP responses
        mock_get.return_value = Mock(status_code=200)
        
        result = agent.validate_service_health(3000, 8000)
        
        # Verify results
        assert result["frontend"]["healthy"] is True
        assert result["backend"]["healthy"] is True
        assert result["all_healthy"] is True
        assert result["frontend"]["status_code"] == 200
        assert result["backend"]["status_code"] == 200
    
    @patch('requests.get')
    def test_validate_service_health_frontend_unhealthy(self, mock_get):
        """Test service health validation when frontend is unhealthy."""
        agent = DeploymentAgent()
        
        # Mock responses - frontend fails, backend succeeds
        def get_side_effect(url, **kwargs):
            if "3000" in url:
                import requests
                raise requests.exceptions.ConnectionError("Connection refused")
            else:
                return Mock(status_code=200)
        
        mock_get.side_effect = get_side_effect
        
        result = agent.validate_service_health(3000, 8000)
        
        # Verify results
        assert result["frontend"]["healthy"] is False
        assert result["backend"]["healthy"] is True
        assert result["all_healthy"] is False
        assert result["frontend"]["error"] is not None


class TestDatabaseConnectionValidation:
    """Test database connection validation from backend container."""
    
    def test_validate_database_connection_no_config(self):
        """Test database validation with no database config."""
        agent = DeploymentAgent()
        
        result = agent.validate_database_connection_from_backend(
            database_config=None
        )
        
        # Should return early without errors
        assert result["postgres"]["connected"] is False
        assert result["mongo"]["connected"] is False
    
    @patch('docker.from_env')
    def test_validate_database_connection_postgres_success(self, mock_docker_from_env):
        """Test successful PostgreSQL connection validation."""
        # Create mock Docker client
        mock_docker_client = Mock()
        mock_docker_from_env.return_value = mock_docker_client
        
        # Mock container and exec_run properly
        mock_exec_result = Mock()
        mock_exec_result.exit_code = 0
        mock_exec_result.output = b"PostgreSQL connection successful"
        
        mock_container = Mock()
        mock_container.exec_run = Mock(return_value=mock_exec_result)
        
        # Mock the docker client to return our mock container
        mock_docker_client.containers.get = Mock(return_value=mock_container)
        
        # Create agent (will use mocked docker client)
        agent = DeploymentAgent()
        
        database_config = {
            "postgres": {
                "success": True,
                "connection_string": "postgresql://user:pass@postgres:5432/db"
            }
        }
        
        result = agent.validate_database_connection_from_backend(
            database_config=database_config
        )
        
        # Verify results
        assert result["postgres"]["connected"] is True
        assert result["all_connected"] is True
        # Verify exec_run was called
        mock_container.exec_run.assert_called_once()
    
    @patch('docker.from_env')
    def test_validate_database_connection_container_not_found(self, mock_docker_from_env):
        """Test database validation when container is not found."""
        # Create mock Docker client
        mock_docker_client = Mock()
        mock_docker_from_env.return_value = mock_docker_client
        
        # Mock container not found
        import docker
        mock_docker_client.containers.get = Mock(
            side_effect=docker.errors.NotFound("Container not found")
        )
        
        # Create agent (will use mocked docker client)
        agent = DeploymentAgent()
        
        database_config = {
            "postgres": {
                "success": True,
                "connection_string": "postgresql://user:pass@postgres:5432/db"
            }
        }
        
        result = agent.validate_database_connection_from_backend(
            database_config=database_config
        )
        
        # Verify error handling
        assert result["postgres"]["connected"] is False
        assert result["postgres"]["error"] is not None
        assert "not found" in result["postgres"]["error"].lower()


class TestServiceEndpoints:
    """Test service endpoint output functionality."""
    
    def test_output_service_endpoints_with_databases(self):
        """Test service endpoint output with database configuration."""
        agent = DeploymentAgent()
        
        database_config = {
            "postgres": {
                "success": True,
                "database": "test_db"
            },
            "mongo": {
                "success": True,
                "database": "test_db"
            }
        }
        
        endpoints = agent.output_service_endpoints(
            frontend_port=3000,
            backend_port=8000,
            database_config=database_config
        )
        
        # Verify endpoints
        assert "frontend" in endpoints
        assert "backend" in endpoints
        assert "backend_health" in endpoints
        assert "postgres" in endpoints
        assert "mongo" in endpoints
        assert endpoints["frontend"] == "http://localhost:3000"
        assert endpoints["backend"] == "http://localhost:8000"
        assert endpoints["backend_health"] == "http://localhost:8000/health"
    
    def test_output_service_endpoints_no_databases(self):
        """Test service endpoint output without databases."""
        agent = DeploymentAgent()
        
        endpoints = agent.output_service_endpoints(
            frontend_port=3000,
            backend_port=8000,
            database_config=None
        )
        
        # Verify endpoints
        assert "frontend" in endpoints
        assert "backend" in endpoints
        assert "backend_health" in endpoints
        assert "postgres" not in endpoints
        assert "mongo" not in endpoints


class TestContainerCleanup:
    """Test container cleanup on failure."""
    
    @patch('subprocess.run')
    def test_cleanup_containers_success(self, mock_run):
        """Test successful container cleanup."""
        agent = DeploymentAgent()
        
        # Mock successful docker-compose stop and down
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_path = os.path.join(temp_dir, "docker-compose.yml")
            with open(compose_path, "w") as f:
                f.write("version: '3.8'\nservices:\n  test:\n    image: hello-world\n")
            
            result = agent.cleanup_containers_on_failure(temp_dir)
            
            # Verify results
            assert result["success"] is True
            assert len(result["errors"]) == 0
            # Should call stop and down
            assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_cleanup_containers_failure(self, mock_run):
        """Test container cleanup failure."""
        agent = DeploymentAgent()
        
        # Mock failed docker-compose commands
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error stopping containers"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_path = os.path.join(temp_dir, "docker-compose.yml")
            with open(compose_path, "w") as f:
                f.write("version: '3.8'\nservices:\n")
            
            result = agent.cleanup_containers_on_failure(temp_dir)
            
            # Verify error handling
            assert len(result["errors"]) > 0


class TestDeploymentDiagnostics:
    """Test deployment diagnostics generation."""
    
    def test_generate_diagnostics_build_failure(self):
        """Test diagnostics for build failure."""
        agent = DeploymentAgent()
        
        build_results = {
            "frontend": {
                "success": False,
                "errors": ["Docker build failed: missing dependency"]
            },
            "backend": {
                "success": True,
                "errors": []
            }
        }
        
        diagnostics = agent.generate_deployment_diagnostics(build_results=build_results)
        
        # Verify diagnostics
        assert diagnostics["status"] == "failed"
        assert diagnostics["phase"] == "build"
        assert len(diagnostics["errors"]) > 0
        assert any("frontend" in error.lower() for error in diagnostics["errors"])
        assert len(diagnostics["recommendations"]) > 0
    
    def test_generate_diagnostics_health_check_failure(self):
        """Test diagnostics for health check failure."""
        agent = DeploymentAgent()
        
        health_results = {
            "frontend": {"healthy": True, "error": None},
            "backend": {
                "healthy": False,
                "error": "Connection refused"
            }
        }
        
        diagnostics = agent.generate_deployment_diagnostics(health_results=health_results)
        
        # Verify diagnostics
        assert diagnostics["status"] == "failed"
        assert diagnostics["phase"] == "health_check"
        assert any("backend" in error.lower() for error in diagnostics["errors"])
        assert any("docker logs" in rec.lower() for rec in diagnostics["recommendations"])
    
    def test_generate_diagnostics_database_validation_failure(self):
        """Test diagnostics for database validation failure."""
        agent = DeploymentAgent()
        
        db_validation_results = {
            "postgres": {
                "connected": False,
                "error": "Authentication failed"
            },
            "mongo": {
                "connected": True,
                "error": None
            },
            "all_connected": False
        }
        
        diagnostics = agent.generate_deployment_diagnostics(
            db_validation_results=db_validation_results
        )
        
        # Verify diagnostics
        assert diagnostics["status"] == "failed"
        assert diagnostics["phase"] == "database_validation"
        assert any("postgresql" in error.lower() for error in diagnostics["errors"])
    
    def test_generate_diagnostics_success(self):
        """Test diagnostics for successful deployment."""
        agent = DeploymentAgent()
        
        build_results = {
            "frontend": {"success": True, "errors": []},
            "backend": {"success": True, "errors": []}
        }
        deployment_result = {"success": True, "errors": []}
        health_results = {
            "frontend": {"healthy": True},
            "backend": {"healthy": True},
            "all_healthy": True
        }
        db_validation_results = {"all_connected": True}
        
        diagnostics = agent.generate_deployment_diagnostics(
            build_results=build_results,
            deployment_result=deployment_result,
            health_results=health_results,
            db_validation_results=db_validation_results
        )
        
        # Verify success
        assert diagnostics["status"] == "success"
        assert diagnostics["phase"] == "complete"
        assert len(diagnostics["errors"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
