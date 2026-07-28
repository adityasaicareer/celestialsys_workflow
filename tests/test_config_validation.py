"""
Unit tests for configuration validation system (Task 19.1).

Tests:
- Environment variable validation
- Configuration template generation
- Secrets detection
- Backend/Frontend environment validation

**Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5**
"""

import os
import pytest
from pathlib import Path
from workflow.config import (
    ConfigValidator,
    ConfigTemplateGenerator,
    ConfigDocGenerator,
    Environment,
    ValidationResult
)


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_validation_result_passes_by_default(self):
        """Test that ValidationResult passes by default."""
        result = ValidationResult()
        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.info) == 0
    
    def test_add_error_sets_passed_to_false(self):
        """Test that adding an error sets passed to False."""
        result = ValidationResult()
        result.add_error("Test error")
        assert result.passed is False
        assert len(result.errors) == 1
        assert "Test error" in result.errors
    
    def test_add_warning_does_not_affect_passed(self):
        """Test that adding a warning doesn't affect passed status."""
        result = ValidationResult()
        result.add_warning("Test warning")
        assert result.passed is True
        assert len(result.warnings) == 1
    
    def test_string_representation(self):
        """Test ValidationResult string representation."""
        result = ValidationResult()
        result.add_error("Error message")
        result.add_warning("Warning message")
        result.add_info("Info message")
        
        str_repr = str(result)
        assert "Configuration validation failed" in str_repr
        assert "Error message" in str_repr
        assert "Warning message" in str_repr
        assert "Info message" in str_repr


class TestConfigValidator:
    """Test ConfigValidator class."""
    
    def test_validate_workflow_environment_missing_api_key(self):
        """Test workflow validation fails when OPENAI_API_KEY is missing."""
        # Remove API key if present
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        
        try:
            result = ConfigValidator.validate_workflow_environment()
            assert result.passed is False
            assert any("OPENAI_API_KEY" in error for error in result.errors)
        finally:
            # Restore original key
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
    
    def test_validate_workflow_environment_with_api_key(self):
        """Test workflow validation passes with valid OPENAI_API_KEY."""
        # Set a valid API key
        original_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "sk-test1234567890abcdefghijklmnopqrstuvwxyz123456"
        
        try:
            result = ConfigValidator.validate_workflow_environment()
            # Should pass (no missing required vars)
            assert result.passed is True
            assert any("OPENAI_API_KEY" in info for info in result.info)
        finally:
            # Restore original key
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)
    
    def test_validate_workflow_environment_invalid_port(self):
        """Test workflow validation catches invalid port numbers."""
        original_port = os.environ.get("POSTGRES_PORT")
        os.environ["POSTGRES_PORT"] = "invalid"
        
        try:
            result = ConfigValidator.validate_workflow_environment()
            assert result.passed is False
            assert any("POSTGRES_PORT" in error and "integer" in error for error in result.errors)
        finally:
            if original_port:
                os.environ["POSTGRES_PORT"] = original_port
            else:
                os.environ.pop("POSTGRES_PORT", None)
    
    def test_scan_for_secrets_detects_hardcoded_password(self, tmp_path):
        """Test that secrets scanner detects hardcoded passwords."""
        # Create a file with hardcoded password
        test_file = tmp_path / "test_config.py"
        test_file.write_text('password = "my_secret_password123"')
        
        result = ConfigValidator.scan_for_secrets(str(test_file))
        assert result.passed is False
        assert any("password" in error.lower() for error in result.errors)
    
    def test_scan_for_secrets_detects_api_key(self, tmp_path):
        """Test that secrets scanner detects hardcoded API keys."""
        test_file = tmp_path / "test_config.py"
        test_file.write_text('api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz123456"')
        
        result = ConfigValidator.scan_for_secrets(str(test_file))
        assert result.passed is False
        assert any("api" in error.lower() or "key" in error.lower() for error in result.errors)
    
    def test_scan_for_secrets_detects_connection_string(self, tmp_path):
        """Test that secrets scanner detects credentials in connection strings."""
        test_file = tmp_path / "test_config.py"
        test_file.write_text('db_url = "postgresql://user:password@localhost:5432/db"')
        
        result = ConfigValidator.scan_for_secrets(str(test_file))
        assert result.passed is False
        assert any("postgresql" in error.lower() or "credentials" in error.lower() 
                  for error in result.errors)
    
    def test_scan_for_secrets_ignores_env_files(self, tmp_path):
        """Test that secrets scanner skips .env files."""
        env_file = tmp_path / ".env"
        env_file.write_text('PASSWORD=my_password')
        
        result = ConfigValidator.scan_for_secrets(str(env_file))
        # Should skip .env files
        assert result.passed is True
        assert any("env" in info.lower() for info in result.info)
    
    def test_scan_for_secrets_passes_clean_code(self, tmp_path):
        """Test that secrets scanner passes code using environment variables."""
        test_file = tmp_path / "clean_config.py"
        test_file.write_text("""
import os
password = os.environ.get("PASSWORD")
api_key = os.environ.get("API_KEY")
""")
        
        result = ConfigValidator.scan_for_secrets(str(test_file))
        assert result.passed is True
    
    def test_scan_directory_for_secrets(self, tmp_path):
        """Test directory scanning for secrets."""
        # Create clean file
        clean_file = tmp_path / "clean.py"
        clean_file.write_text('password = os.environ.get("PASSWORD")')
        
        # Create dirty file
        dirty_file = tmp_path / "dirty.py"
        dirty_file.write_text('password = "hardcoded_password_12345"')
        
        result = ConfigValidator.scan_directory_for_secrets(str(tmp_path))
        assert result.passed is False
        assert any("dirty.py" in error for error in result.errors)
    
    def test_validate_backend_environment_missing_file(self):
        """Test backend validation with missing .env file."""
        result = ConfigValidator.validate_backend_environment("/nonexistent/.env")
        # Should return warning, not error
        assert len(result.warnings) > 0
    
    def test_validate_backend_environment_with_postgres(self, tmp_path):
        """Test backend validation with PostgreSQL configuration."""
        env_file = tmp_path / ".env"
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
        assert result.passed is True
        assert any("APP_ENV" in info for info in result.info)
    
    def test_validate_frontend_environment_missing_file(self):
        """Test frontend validation with missing .env file."""
        result = ConfigValidator.validate_frontend_environment("/nonexistent/.env.local")
        # Should return warning, not error
        assert len(result.warnings) > 0
    
    def test_validate_frontend_environment_with_required_vars(self, tmp_path):
        """Test frontend validation with required variables."""
        env_file = tmp_path / ".env.local"
        env_file.write_text("""
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=development
""")
        
        result = ConfigValidator.validate_frontend_environment(str(env_file))
        assert result.passed is True
        assert any("NEXT_PUBLIC_API_URL" in info for info in result.info)
    
    def test_validate_frontend_warns_non_public_vars(self, tmp_path):
        """Test frontend validation warns about non-NEXT_PUBLIC_ variables."""
        env_file = tmp_path / ".env.local"
        env_file.write_text("""
NEXT_PUBLIC_API_URL=http://localhost:8000
PRIVATE_API_KEY=secret
""")
        
        result = ConfigValidator.validate_frontend_environment(str(env_file))
        assert any("NEXT_PUBLIC_" in warning for warning in result.warnings)


class TestConfigTemplateGenerator:
    """Test ConfigTemplateGenerator class."""
    
    def test_generate_backend_template_development(self):
        """Test backend template generation for development environment."""
        template = ConfigTemplateGenerator.generate_backend_template(
            environment=Environment.DEVELOPMENT,
            include_postgres=True,
            include_mongo=False
        )
        
        assert "APP_ENV=development" in template
        assert "DEBUG=True" in template
        assert "POSTGRES_HOST" in template
        assert "MONGO_HOST" not in template
    
    def test_generate_backend_template_production(self):
        """Test backend template generation for production environment."""
        template = ConfigTemplateGenerator.generate_backend_template(
            environment=Environment.PRODUCTION,
            include_postgres=False,
            include_mongo=True
        )
        
        assert "APP_ENV=production" in template
        assert "DEBUG=False" in template
        assert "POSTGRES_HOST" not in template
        assert "MONGO_HOST" in template
    
    def test_generate_backend_template_to_file(self, tmp_path):
        """Test backend template generation to file."""
        output_file = tmp_path / ".env.backend"
        ConfigTemplateGenerator.generate_backend_template(
            environment=Environment.STAGING,
            include_postgres=True,
            include_mongo=True,
            output_path=str(output_file)
        )
        
        assert output_file.exists()
        content = output_file.read_text()
        assert "APP_ENV=staging" in content
        assert "POSTGRES_HOST" in content
        assert "MONGO_HOST" in content
    
    def test_generate_frontend_template_development(self):
        """Test frontend template generation for development environment."""
        template = ConfigTemplateGenerator.generate_frontend_template(
            environment=Environment.DEVELOPMENT,
            backend_url="http://localhost:8000"
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
    
    def test_generate_frontend_template_to_file(self, tmp_path):
        """Test frontend template generation to file."""
        output_file = tmp_path / ".env.frontend"
        ConfigTemplateGenerator.generate_frontend_template(
            environment=Environment.STAGING,
            output_path=str(output_file)
        )
        
        assert output_file.exists()
        content = output_file.read_text()
        assert "NEXT_PUBLIC_API_URL" in content
        assert "staging" in content.lower()
    
    def test_generate_docker_compose_template_development(self):
        """Test Docker Compose template generation for development."""
        template = ConfigTemplateGenerator.generate_docker_compose_template(
            environment=Environment.DEVELOPMENT,
            include_postgres=True,
            include_mongo=True
        )
        
        assert "version: '3.8'" in template
        assert "backend_development" in template
        assert "frontend_development" in template
        assert "postgres:" in template
        assert "mongo:" in template
    
    def test_generate_docker_compose_template_without_databases(self):
        """Test Docker Compose template without databases."""
        template = ConfigTemplateGenerator.generate_docker_compose_template(
            environment=Environment.PRODUCTION,
            include_postgres=False,
            include_mongo=False
        )
        
        assert "backend:" in template
        assert "frontend:" in template
        assert "postgres:" not in template
        assert "mongo:" not in template
        # Frontend should still depend on backend
        assert "depends_on:" in template
        # But backend should not have depends_on section
        backend_section = template.split("backend:")[1].split("frontend:")[0]
        assert "depends_on:" not in backend_section
    
    def test_generate_docker_compose_template_to_file(self, tmp_path):
        """Test Docker Compose template generation to file."""
        output_file = tmp_path / "docker-compose.yml"
        ConfigTemplateGenerator.generate_docker_compose_template(
            environment=Environment.STAGING,
            include_postgres=True,
            include_mongo=False,
            output_path=str(output_file)
        )
        
        assert output_file.exists()
        content = output_file.read_text()
        assert "version: '3.8'" in content
        assert "staging" in content


class TestConfigDocGenerator:
    """Test ConfigDocGenerator class."""
    
    def test_generate_configuration_guide(self):
        """Test configuration guide generation."""
        doc = ConfigDocGenerator.generate_configuration_guide()
        
        # Check that documentation contains key sections
        assert "Configuration Guide" in doc
        assert "OPENAI_API_KEY" in doc
        assert "Backend Configuration" in doc
        assert "Frontend Configuration" in doc
        assert "Security Best Practices" in doc
        assert "Docker Compose Configuration" in doc
        assert "Troubleshooting" in doc
    
    def test_generate_configuration_guide_to_file(self, tmp_path):
        """Test configuration guide generation to file."""
        output_file = tmp_path / "CONFIG_GUIDE.md"
        doc = ConfigDocGenerator.generate_configuration_guide(str(output_file))
        
        assert output_file.exists()
        content = output_file.read_text()
        assert content == doc
        assert len(content) > 1000  # Should be substantial documentation


class TestIntegration:
    """Integration tests for configuration validation system."""
    
    def test_full_backend_workflow(self, tmp_path):
        """Test complete backend configuration workflow."""
        # Generate template
        env_file = tmp_path / ".env.backend"
        ConfigTemplateGenerator.generate_backend_template(
            environment=Environment.DEVELOPMENT,
            include_postgres=True,
            output_path=str(env_file)
        )
        
        # Scan for secrets
        secret_result = ConfigValidator.scan_for_secrets(str(env_file))
        # Should skip .env files
        assert secret_result.passed is True
        
        # Validate environment
        validation_result = ConfigValidator.validate_backend_environment(str(env_file))
        assert validation_result.passed is True
    
    def test_full_frontend_workflow(self, tmp_path):
        """Test complete frontend configuration workflow."""
        # Generate template
        env_file = tmp_path / ".env.frontend"
        ConfigTemplateGenerator.generate_frontend_template(
            environment=Environment.DEVELOPMENT,
            output_path=str(env_file)
        )
        
        # Validate environment
        validation_result = ConfigValidator.validate_frontend_environment(str(env_file))
        assert validation_result.passed is True
    
    def test_secrets_detection_prevents_deployment(self, tmp_path):
        """Test that secrets detection would prevent deployment."""
        # Create backend code with hardcoded secret
        code_file = tmp_path / "app.py"
        code_file.write_text("""
from fastapi import FastAPI

app = FastAPI()

# BAD: Hardcoded credential
DATABASE_URL = "postgresql://user:password123@localhost:5432/db"
""")
        
        # Scan directory
        result = ConfigValidator.scan_directory_for_secrets(str(tmp_path))
        assert result.passed is False
        # This would prevent deployment
        assert len(result.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
