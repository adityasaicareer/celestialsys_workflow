"""
Unit tests for configuration validation system (Task 19.1).

Tests validate:
- Environment variable validation (required variables present)
- Configuration file templates for different environments
- Secrets validation (ensure no hardcoded credentials)
- Configuration documentation generation

**Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5**
"""

import os
import tempfile
from pathlib import Path
import pytest

from workflow.config import (
    ConfigValidator,
    ConfigTemplateGenerator,
    ConfigDocGenerator,
    Environment,
    ValidationResult,
    get_config
)


class TestEnvironmentValidation:
    """Test environment variable validation functionality."""
    
    def test_validate_workflow_environment_with_all_required(self, monkeypatch):
        """Test workflow validation passes when all required variables are set."""
        # Set required environment variable
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789012345678901234567890")
        
        result = ConfigValidator.validate_workflow_environment()
        
        assert result.passed
        assert any("Required variable OPENAI_API_KEY is set" in info for info in result.info)
    
    def test_validate_workflow_environment_missing_required(self, monkeypatch):
        """Test workflow validation fails when required variables are missing."""
        # Remove required environment variable
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        result = ConfigValidator.validate_workflow_environment()
        
        assert not result.passed
        assert any("Required environment variable missing: OPENAI_API_KEY" in error 
                  for error in result.errors)
    
    def test_validate_workflow_environment_placeholder_value(self, monkeypatch):
        """Test validation detects placeholder values."""
        monkeypatch.setenv("OPENAI_API_KEY", "your_openai_api_key_here")
        
        result = ConfigValidator.validate_workflow_environment()
        
        assert not result.passed
        assert any("placeholder value" in error.lower() for error in result.errors)
    
    def test_validate_workflow_environment_invalid_api_key_format(self, monkeypatch):
        """Test validation warns on invalid API key format."""
        monkeypatch.setenv("OPENAI_API_KEY", "invalid_key_format")
        
        result = ConfigValidator.validate_workflow_environment()
        
        # Should pass but with warning
        assert any("does not match expected format" in warning for warning in result.warnings)
    
    def test_validate_workflow_environment_invalid_port(self, monkeypatch):
        """Test validation catches invalid port numbers."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789012345678901234567890")
        monkeypatch.setenv("BACKEND_PORT", "99999")  # Out of valid range
        
        result = ConfigValidator.validate_workflow_environment()
        
        assert not result.passed
        assert any("BACKEND_PORT" in error and "65535" in error for error in result.errors)
    
    def test_validate_workflow_environment_non_integer_port(self, monkeypatch):
        """Test validation catches non-integer port values."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789012345678901234567890")
        monkeypatch.setenv("POSTGRES_PORT", "not_a_number")
        
        result = ConfigValidator.validate_workflow_environment()
        
        assert not result.passed
        assert any("must be a valid integer" in error for error in result.errors)


class TestBackendEnvironmentValidation:
    """Test backend application environment validation."""
    
    def test_validate_backend_environment_file_not_found(self):
        """Test validation handles missing backend .env file gracefully."""
        result = ConfigValidator.validate_backend_environment(
            env_file="/nonexistent/path/.env"
        )
        
        assert any("not found" in warning.lower() for warning in result.warnings)
    
    def test_validate_backend_environment_with_postgres(self):
        """Test validation of backend environment with PostgreSQL config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("""
APP_ENV=development
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=testdb
POSTGRES_USER=testuser
POSTGRES_PASSWORD=testpass
DATABASE_URL=postgresql://testuser:testpass@localhost:5432/testdb
""")
            
            result = ConfigValidator.validate_backend_environment(str(env_file))
            
            assert result.passed
            assert any("APP_ENV" in info for info in result.info)
            assert any("POSTGRES_HOST" in info for info in result.info)
    
    def test_validate_backend_environment_incomplete_postgres(self):
        """Test validation catches incomplete PostgreSQL configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("""
APP_ENV=development
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
# Missing POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, DATABASE_URL
""")
            
            result = ConfigValidator.validate_backend_environment(str(env_file))
            
            assert not result.passed
            assert any("PostgreSQL configuration incomplete" in error for error in result.errors)
    
    def test_validate_backend_environment_with_mongo(self):
        """Test validation of backend environment with MongoDB config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("""
APP_ENV=development
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=testdb
MONGO_USER=testuser
MONGO_PASSWORD=testpass
MONGO_URL=mongodb://testuser:testpass@localhost:27017/testdb?authSource=admin
""")
            
            result = ConfigValidator.validate_backend_environment(str(env_file))
            
            assert result.passed
            assert any("MongoDB variable" in info for info in result.info)


class TestFrontendEnvironmentValidation:
    """Test frontend application environment validation."""
    
    def test_validate_frontend_environment_with_required_vars(self):
        """Test validation passes with required frontend variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env.local"
            env_file.write_text("""
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=development
""")
            
            result = ConfigValidator.validate_frontend_environment(str(env_file))
            
            assert result.passed
            assert any("NEXT_PUBLIC_API_URL" in info for info in result.info)
    
    def test_validate_frontend_environment_missing_required(self):
        """Test validation catches missing required frontend variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env.local"
            env_file.write_text("""
NEXT_PUBLIC_ENVIRONMENT=development
# Missing NEXT_PUBLIC_API_URL
""")
            
            result = ConfigValidator.validate_frontend_environment(str(env_file))
            
            assert not result.passed
            assert any("Required frontend variable missing" in error for error in result.errors)
    
    def test_validate_frontend_environment_missing_prefix(self):
        """Test validation warns about variables missing NEXT_PUBLIC_ prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env.local"
            env_file.write_text("""
NEXT_PUBLIC_API_URL=http://localhost:8000
API_KEY=some_key
""")
            
            result = ConfigValidator.validate_frontend_environment(str(env_file))
            
            assert any("does not use NEXT_PUBLIC_ prefix" in warning 
                      for warning in result.warnings)


class TestSecretsScanning:
    """Test hardcoded secrets detection functionality."""
    
    def test_scan_for_secrets_hardcoded_password(self):
        """Test detection of hardcoded password."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "config.py"
            test_file.write_text("""
# Bad practice - hardcoded password
password = "supersecretpassword123"
""")
            
            result = ConfigValidator.scan_for_secrets(str(test_file))
            
            assert not result.passed
            assert any("hardcoded password" in error.lower() for error in result.errors)
    
    def test_scan_for_secrets_hardcoded_api_key(self):
        """Test detection of hardcoded API key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "api_client.py"
            test_file.write_text("""
# Bad practice - hardcoded API key
api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz1234567890"
""")
            
            result = ConfigValidator.scan_for_secrets(str(test_file))
            
            assert not result.passed
            assert any("api key" in error.lower() for error in result.errors)
    
    def test_scan_for_secrets_database_connection_string(self):
        """Test detection of hardcoded database credentials in connection string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "database.py"
            test_file.write_text("""
# Bad practice - hardcoded database credentials
DATABASE_URL = "postgresql://user:password123@localhost:5432/db"
""")
            
            result = ConfigValidator.scan_for_secrets(str(test_file))
            
            assert not result.passed
            assert any("PostgreSQL credentials" in error for error in result.errors)
    
    def test_scan_for_secrets_env_files_skipped(self):
        """Test that .env files are skipped (they're supposed to contain secrets)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("""
PASSWORD=mysecretpassword
API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz
""")
            
            result = ConfigValidator.scan_for_secrets(str(env_file))
            
            # Should pass because .env files are expected to contain credentials
            assert result.passed
            assert any("Skipping .env file" in info for info in result.info)
    
    def test_scan_for_secrets_clean_code(self):
        """Test that clean code with environment variables passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "config.py"
            test_file.write_text("""
import os

# Good practice - read from environment
password = os.environ.get("PASSWORD")
api_key = os.environ.get("API_KEY")
database_url = os.environ.get("DATABASE_URL")
""")
            
            result = ConfigValidator.scan_for_secrets(str(test_file))
            
            assert result.passed
            assert len(result.errors) == 0
    
    def test_scan_directory_for_secrets(self):
        """Test recursive directory scanning for secrets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory structure with some files
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "clean.py").write_text("""
import os
password = os.environ.get("PASSWORD")
""")
            (Path(tmpdir) / "src" / "dirty.py").write_text("""
password = "hardcoded_password_value"
""")
            
            result = ConfigValidator.scan_directory_for_secrets(tmpdir)
            
            assert not result.passed
            assert any("hardcoded password" in error.lower() for error in result.errors)
            assert any("Scanned" in info and "files" in info for info in result.info)


class TestConfigTemplateGeneration:
    """Test configuration template generation for different environments."""
    
    def test_generate_backend_template_development(self):
        """Test backend template generation for development environment."""
        template = ConfigTemplateGenerator.generate_backend_template(
            environment=Environment.DEVELOPMENT,
            include_postgres=True,
            include_mongo=False
        )
        
        assert "APP_ENV=development" in template
        assert "DEBUG=True" in template
        assert "LOG_LEVEL=DEBUG" in template
        assert "POSTGRES_HOST" in template
        assert "MONGO_HOST" not in template
    
    def test_generate_backend_template_production(self):
        """Test backend template generation for production environment."""
        template = ConfigTemplateGenerator.generate_backend_template(
            environment=Environment.PRODUCTION,
            include_postgres=True,
            include_mongo=True
        )
        
        assert "APP_ENV=production" in template
        assert "DEBUG=False" in template
        assert "LOG_LEVEL=WARNING" in template
        assert "POSTGRES_HOST" in template
        assert "MONGO_HOST" in template
    
    def test_generate_backend_template_writes_file(self):
        """Test that backend template is written to file when output_path provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "backend" / ".env.dev"
            
            template = ConfigTemplateGenerator.generate_backend_template(
                environment=Environment.DEVELOPMENT,
                include_postgres=True,
                output_path=str(output_path)
            )
            
            assert output_path.exists()
            content = output_path.read_text()
            assert content == template
    
    def test_generate_frontend_template_development(self):
        """Test frontend template generation for development environment."""
        template = ConfigTemplateGenerator.generate_frontend_template(
            environment=Environment.DEVELOPMENT
        )
        
        assert "NEXT_PUBLIC_API_URL=http://localhost:8000" in template
        assert "NEXT_PUBLIC_ENVIRONMENT=development" in template
        assert "NEXT_PUBLIC_ENABLE_DEBUG=true" in template
    
    def test_generate_frontend_template_production(self):
        """Test frontend template generation for production environment."""
        template = ConfigTemplateGenerator.generate_frontend_template(
            environment=Environment.PRODUCTION,
            backend_url="https://api.example.com"
        )
        
        assert "NEXT_PUBLIC_API_URL=https://api.example.com" in template
        assert "NEXT_PUBLIC_ENVIRONMENT=production" in template
        assert "NEXT_PUBLIC_ENABLE_DEBUG=false" in template
    
    def test_generate_frontend_template_writes_file(self):
        """Test that frontend template is written to file when output_path provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "frontend" / ".env.production"
            
            template = ConfigTemplateGenerator.generate_frontend_template(
                environment=Environment.PRODUCTION,
                output_path=str(output_path)
            )
            
            assert output_path.exists()
            content = output_path.read_text()
            assert content == template
    
    def test_generate_docker_compose_template_development(self):
        """Test Docker Compose template generation for development."""
        template = ConfigTemplateGenerator.generate_docker_compose_template(
            environment=Environment.DEVELOPMENT,
            include_postgres=True,
            include_mongo=True
        )
        
        assert "version: '3.8'" in template
        assert "backend:" in template
        assert "frontend:" in template
        assert "postgres:" in template
        assert "mongo:" in template
        assert "backend_development" in template
    
    def test_generate_docker_compose_template_production(self):
        """Test Docker Compose template generation for production."""
        template = ConfigTemplateGenerator.generate_docker_compose_template(
            environment=Environment.PRODUCTION,
            include_postgres=True,
            include_mongo=False
        )
        
        assert "backend_production" in template
        assert "postgres:" in template
        assert "mongo:" not in template
        assert "restart: unless-stopped" in template
    
    def test_generate_docker_compose_template_writes_file(self):
        """Test that Docker Compose template is written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "docker-compose.dev.yml"
            
            template = ConfigTemplateGenerator.generate_docker_compose_template(
                environment=Environment.DEVELOPMENT,
                include_postgres=True,
                output_path=str(output_path)
            )
            
            assert output_path.exists()
            content = output_path.read_text()
            assert content == template


class TestConfigDocumentation:
    """Test configuration documentation generation."""
    
    def test_generate_configuration_guide(self):
        """Test configuration guide generation."""
        guide = ConfigDocGenerator.generate_configuration_guide()
        
        # Check for key sections
        assert "Configuration Guide" in guide
        assert "Required Environment Variables" in guide
        assert "OPENAI_API_KEY" in guide
        assert "Backend Configuration" in guide
        assert "Frontend Configuration" in guide
        assert "Security Best Practices" in guide
        assert "Never Hardcode Credentials" in guide
        assert "Docker Compose Configuration" in guide
    
    def test_generate_configuration_guide_writes_file(self):
        """Test that configuration guide is written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "CONFIGURATION.md"
            
            guide = ConfigDocGenerator.generate_configuration_guide(
                output_path=str(output_path)
            )
            
            assert output_path.exists()
            content = output_path.read_text()
            assert content == guide


class TestValidationResult:
    """Test ValidationResult helper class."""
    
    def test_validation_result_passed_by_default(self):
        """Test that ValidationResult starts as passed."""
        result = ValidationResult()
        assert result.passed
        assert len(result.errors) == 0
    
    def test_validation_result_add_error_fails(self):
        """Test that adding an error sets passed to False."""
        result = ValidationResult()
        result.add_error("Test error")
        
        assert not result.passed
        assert "Test error" in result.errors
    
    def test_validation_result_add_warning(self):
        """Test that adding a warning doesn't fail validation."""
        result = ValidationResult()
        result.add_warning("Test warning")
        
        assert result.passed
        assert "Test warning" in result.warnings
    
    def test_validation_result_string_formatting(self):
        """Test ValidationResult string formatting."""
        result = ValidationResult()
        result.add_error("Error message")
        result.add_warning("Warning message")
        result.add_info("Info message")
        
        output = str(result)
        
        assert "❌ Configuration validation failed" in output
        assert "Error message" in output
        assert "Warning message" in output
        assert "Info message" in output


class TestConfigIntegration:
    """Integration tests for configuration system."""
    
    def test_get_config_loads_settings(self, monkeypatch):
        """Test that get_config() loads configuration settings."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789012345678901234567890")
        monkeypatch.setenv("LLM_MODEL", "gpt-4")
        
        config = get_config()
        
        assert config.openai_api_key == "sk-test123456789012345678901234567890"
        assert config.llm_model == "gpt-4"
    
    def test_full_validation_workflow(self, monkeypatch):
        """Test complete validation workflow for a project."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test123456789012345678901234567890")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate templates
            backend_env = Path(tmpdir) / "backend" / ".env.dev"
            ConfigTemplateGenerator.generate_backend_template(
                environment=Environment.DEVELOPMENT,
                include_postgres=True,
                output_path=str(backend_env)
            )
            
            frontend_env = Path(tmpdir) / "frontend" / ".env.local"
            ConfigTemplateGenerator.generate_frontend_template(
                environment=Environment.DEVELOPMENT,
                output_path=str(frontend_env)
            )
            
            # Validate workflow environment
            workflow_result = ConfigValidator.validate_workflow_environment()
            assert workflow_result.passed
            
            # Validate generated files exist
            assert backend_env.exists()
            assert frontend_env.exists()
            
            # Create a clean Python file to demonstrate the workflow
            clean_code = Path(tmpdir) / "src" / "config.py"
            clean_code.parent.mkdir(parents=True, exist_ok=True)
            clean_code.write_text("""
import os

# Good practice - read from environment
DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY = os.environ.get("API_KEY")
""")
            
            # Scan for secrets in the source code directory (not .env files)
            secrets_result = ConfigValidator.scan_directory_for_secrets(
                str(clean_code.parent)
            )
            # Should pass because code uses environment variables
            assert secrets_result.passed
            assert any("No hardcoded secrets detected" in info for info in secrets_result.info)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
