"""
Configuration management for the workflow system.

Loads configuration from environment variables and provides
settings for all workflow components.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkflowConfig(BaseSettings):
    """Workflow system configuration."""
    
    # LLM Configuration
    llm_provider: str = "openai"  # "openai" or "openrouter"
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    llm_model: str = "gpt-4-turbo-preview"
    llm_temperature: float = 0.0
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Workflow Configuration
    workflow_checkpoint_db: str = "sqlite:///workflow_checkpoints.db"
    max_retries_per_agent: int = 5
    max_total_retries: int = 20
    
    # Docker Configuration
    docker_host: str = "unix:///var/run/docker.sock"
    
    # Database Configuration
    postgres_image: str = "postgres:15"
    postgres_port: int = 5432
    mongo_image: str = "mongo:7"
    mongo_port: int = 27017
    
    # Generated Application Ports
    backend_port: int = 8000
    frontend_port: int = 3000
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "colored"
    
    # Output Directories
    output_dir: str = "./output"
    backend_output_dir: str = "./backend"
    frontend_output_dir: str = "./frontend"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global configuration instance
_config: Optional[WorkflowConfig] = None


def get_config() -> WorkflowConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = WorkflowConfig()
    return _config


def reload_config() -> WorkflowConfig:
    """Reload configuration from environment."""
    global _config
    _config = WorkflowConfig()
    return _config


def get_llm():
    """
    Get the configured LLM instance based on the provider setting.
    
    Returns:
        ChatOpenAI instance configured for either OpenAI or OpenRouter
    """
    from langchain_openai import ChatOpenAI
    
    config = get_config()
    
    if config.llm_provider.lower() == "openrouter":
        # Use OpenRouter with OpenAI-compatible API
        api_key = config.openrouter_api_key or config.openai_api_key
        if not api_key:
            raise ValueError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env"
            )
        
        return ChatOpenAI(
            model=config.llm_model,
            temperature=config.llm_temperature,
            openai_api_key=api_key,
            openai_api_base=config.openrouter_base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/supervised-agentic-workflow",
                "X-Title": "Supervised Agentic Workflow"
            }
        )
    else:
        # Use OpenAI directly
        if not config.openai_api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY in .env"
            )
        
        return ChatOpenAI(
            model=config.llm_model,
            temperature=config.llm_temperature,
            openai_api_key=config.openai_api_key
        )


# ==============================================================================
# Configuration Validation System
# ==============================================================================

import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from enum import Enum


class Environment(str, Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ValidationResult:
    """Result of a configuration validation operation."""
    
    def __init__(self):
        self.passed = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def add_error(self, message: str):
        """Add an error to the validation result."""
        self.passed = False
        self.errors.append(message)
    
    def add_warning(self, message: str):
        """Add a warning to the validation result."""
        self.warnings.append(message)
    
    def add_info(self, message: str):
        """Add an info message to the validation result."""
        self.info.append(message)
    
    def __str__(self) -> str:
        """Format validation result as string."""
        lines = []
        if self.passed:
            lines.append("✅ Configuration validation passed")
        else:
            lines.append("❌ Configuration validation failed")
        
        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors:
                lines.append(f"  ❌ {error}")
        
        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠️  {warning}")
        
        if self.info:
            lines.append("\nInfo:")
            for info in self.info:
                lines.append(f"  ℹ️  {info}")
        
        return "\n".join(lines)



class ConfigValidator:
    """
    Validates configuration for the workflow system.
    
    Implements:
    - Environment variable validation (required variables present)
    - Secrets detection (no hardcoded credentials in generated code)
    - Configuration file validation
    - Environment-specific configuration validation
    
    **Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5**
    """
    
    # Required environment variables for the workflow system
    REQUIRED_WORKFLOW_VARS = [
        # At least one API key required based on provider
    ]
    
    # Optional environment variables with defaults
    OPTIONAL_WORKFLOW_VARS = {
        "LLM_PROVIDER": "openai",
        "LLM_MODEL": "gpt-4-turbo-preview",
        "LLM_TEMPERATURE": "0.0",
        "WORKFLOW_CHECKPOINT_DB": "sqlite:///workflow_checkpoints.db",
        "MAX_RETRIES_PER_AGENT": "5",
        "MAX_TOTAL_RETRIES": "20",
        "DOCKER_HOST": "unix:///var/run/docker.sock",
        "POSTGRES_IMAGE": "postgres:15",
        "POSTGRES_PORT": "5432",
        "MONGO_IMAGE": "mongo:7",
        "MONGO_PORT": "27017",
        "BACKEND_PORT": "8000",
        "FRONTEND_PORT": "3000",
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "colored",
        "OUTPUT_DIR": "./output",
        "BACKEND_OUTPUT_DIR": "./backend",
        "FRONTEND_OUTPUT_DIR": "./frontend"
    }
    
    # Required variables for generated backend applications
    REQUIRED_BACKEND_VARS = [
        "APP_ENV"
    ]
    
    # Required variables for generated frontend applications
    REQUIRED_FRONTEND_VARS = [
        "NEXT_PUBLIC_API_URL"
    ]
    
    # Patterns that indicate hardcoded secrets
    SECRET_PATTERNS = [
        (r'password\s*=\s*["\'](?!{{|}})(.{8,})["\']', "hardcoded password"),
        (r'api[_-]?key\s*=\s*["\'](?!{{|}})(.{20,})["\']', "hardcoded API key"),
        (r'secret\s*=\s*["\'](?!{{|}})(.{16,})["\']', "hardcoded secret"),
        (r'token\s*=\s*["\'](?!{{|}})(.{20,})["\']', "hardcoded token"),
        (r'postgresql://[^:]+:[^@]+@', "hardcoded PostgreSQL credentials in connection string"),
        (r'mongodb://[^:]+:[^@]+@', "hardcoded MongoDB credentials in connection string"),
        (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key pattern"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub personal access token"),
        (r'AKIA[0-9A-Z]{16}', "AWS access key"),
    ]

    
    @staticmethod
    def validate_workflow_environment() -> ValidationResult:
        """
        Validate workflow system environment variables.
        
        Checks:
        - Required environment variables are present
        - Optional variables have valid values
        - No suspicious values that might be secrets
        
        Returns:
            ValidationResult with errors, warnings, and info messages
        
        **Validates: Requirement 14.1, 14.5**
        """
        result = ValidationResult()
        
        # Check LLM provider configuration
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        
        if provider == "openrouter":
            # Check for OpenRouter API key
            openrouter_key = os.environ.get("OPENROUTER_API_KEY")
            openai_key = os.environ.get("OPENAI_API_KEY")
            
            if not openrouter_key and not openai_key:
                result.add_error("OpenRouter provider selected but no API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY")
            elif openrouter_key:
                if openrouter_key == "your_openrouter_api_key_here":
                    result.add_error("OPENROUTER_API_KEY has placeholder value")
                else:
                    result.add_info("Using OpenRouter API key from OPENROUTER_API_KEY")
            elif openai_key:
                if openai_key == "your_openai_or_openrouter_api_key_here":
                    result.add_error("OPENAI_API_KEY has placeholder value")
                else:
                    result.add_info("Using OpenRouter with API key from OPENAI_API_KEY")
        else:
            # Check for OpenAI API key
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                result.add_error("Required environment variable missing: OPENAI_API_KEY")
            elif api_key in ["your_openai_api_key_here", "your_openai_or_openrouter_api_key_here", "REPLACE_"]:
                result.add_error(f"OPENAI_API_KEY has placeholder value: {api_key}")
            elif not api_key.startswith("sk-"):
                result.add_warning("OPENAI_API_KEY does not match expected format (should start with 'sk-')")
            else:
                result.add_info("OpenAI API key is set")
        
        # Check required variables
        for var in ConfigValidator.REQUIRED_WORKFLOW_VARS:
            value = os.environ.get(var)
            if not value:
                result.add_error(f"Required environment variable missing: {var}")
            elif value == f"your_{var.lower()}_here" or value.startswith("REPLACE_"):
                result.add_error(f"Environment variable {var} has placeholder value: {value}")
            else:
                result.add_info(f"Required variable {var} is set")
        
        # Check optional variables and apply defaults
        for var, default in ConfigValidator.OPTIONAL_WORKFLOW_VARS.items():
            value = os.environ.get(var)
            if not value:
                result.add_info(f"Using default for {var}: {default}")
            else:
                result.add_info(f"Using custom value for {var}")
        
        # Removed duplicate OpenAI API key check (now handled above with provider logic)
        
        # Check port values are valid integers
        for port_var in ["POSTGRES_PORT", "MONGO_PORT", "BACKEND_PORT", "FRONTEND_PORT"]:
            value = os.environ.get(port_var)
            if value:
                try:
                    port = int(value)
                    if port < 1 or port > 65535:
                        result.add_error(f"{port_var} must be between 1 and 65535, got: {port}")
                except ValueError:
                    result.add_error(f"{port_var} must be a valid integer, got: {value}")
        
        return result

    
    @staticmethod
    def validate_backend_environment(env_file: str = "./backend/.env") -> ValidationResult:
        """
        Validate generated backend application environment configuration.
        
        Checks:
        - Required backend environment variables are present
        - Database configuration is complete
        - No hardcoded credentials
        
        Args:
            env_file: Path to the backend .env file
        
        Returns:
            ValidationResult with errors, warnings, and info messages
        
        **Validates: Requirement 14.1, 14.3, 14.5**
        """
        result = ValidationResult()
        
        env_path = Path(env_file)
        if not env_path.exists():
            result.add_warning(f"Backend .env file not found: {env_file}")
            return result
        
        # Read environment file
        env_vars = {}
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
        except Exception as e:
            result.add_error(f"Failed to read backend .env file: {str(e)}")
            return result
        
        # Check required backend variables
        for var in ConfigValidator.REQUIRED_BACKEND_VARS:
            if var not in env_vars:
                result.add_error(f"Required backend variable missing: {var}")
            else:
                result.add_info(f"Backend variable {var} is set")
        
        # Validate database configuration completeness
        has_postgres = any(key.startswith("POSTGRES_") for key in env_vars)
        has_mongo = any(key.startswith("MONGO_") for key in env_vars)
        
        if has_postgres:
            postgres_vars = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", 
                           "POSTGRES_USER", "POSTGRES_PASSWORD", "DATABASE_URL"]
            for var in postgres_vars:
                if var not in env_vars:
                    result.add_error(f"PostgreSQL configuration incomplete: missing {var}")
                else:
                    result.add_info(f"PostgreSQL variable {var} is set")
        
        if has_mongo:
            mongo_vars = ["MONGO_HOST", "MONGO_PORT", "MONGO_DB", 
                         "MONGO_USER", "MONGO_PASSWORD", "MONGO_URL"]
            for var in mongo_vars:
                if var not in env_vars:
                    result.add_error(f"MongoDB configuration incomplete: missing {var}")
                else:
                    result.add_info(f"MongoDB variable {var} is set")
        
        if not has_postgres and not has_mongo:
            result.add_warning("No database configuration found in backend .env")
        
        return result

    
    @staticmethod
    def validate_frontend_environment(env_file: str = "./frontend/.env.local") -> ValidationResult:
        """
        Validate generated frontend application environment configuration.
        
        Checks:
        - Required frontend environment variables are present
        - API endpoint configuration is present
        - Public environment variables use NEXT_PUBLIC_ prefix
        
        Args:
            env_file: Path to the frontend .env file
        
        Returns:
            ValidationResult with errors, warnings, and info messages
        
        **Validates: Requirement 14.2, 14.5**
        """
        result = ValidationResult()
        
        env_path = Path(env_file)
        if not env_path.exists():
            result.add_warning(f"Frontend .env file not found: {env_file}")
            return result
        
        # Read environment file
        env_vars = {}
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
        except Exception as e:
            result.add_error(f"Failed to read frontend .env file: {str(e)}")
            return result
        
        # Check required frontend variables
        for var in ConfigValidator.REQUIRED_FRONTEND_VARS:
            if var not in env_vars:
                result.add_error(f"Required frontend variable missing: {var}")
            else:
                result.add_info(f"Frontend variable {var} is set")
        
        # Validate Next.js public variable naming convention
        for key in env_vars:
            if not key.startswith("NEXT_PUBLIC_") and not key.startswith("NEXT_"):
                result.add_warning(
                    f"Frontend variable '{key}' does not use NEXT_PUBLIC_ prefix. "
                    "It will not be available in browser code."
                )
        
        return result

    
    @staticmethod
    def scan_for_secrets(file_path: str) -> ValidationResult:
        """
        Scan a file for hardcoded secrets and credentials.
        
        Detects:
        - Hardcoded passwords, API keys, tokens
        - Database connection strings with embedded credentials
        - Common secret patterns (AWS keys, GitHub tokens, etc.)
        
        Args:
            file_path: Path to the file to scan
        
        Returns:
            ValidationResult with errors for found secrets
        
        **Validates: Requirement 14.5**
        """
        result = ValidationResult()
        
        file = Path(file_path)
        if not file.exists():
            result.add_warning(f"File not found: {file_path}")
            return result
        
        # Skip binary files and common non-code files
        skip_extensions = {'.db', '.sqlite', '.pyc', '.pyo', '.jpg', '.png', '.gif', 
                          '.pdf', '.zip', '.tar', '.gz', '.ico'}
        if file.suffix in skip_extensions:
            result.add_info(f"Skipping binary/non-code file: {file_path}")
            return result
        
        try:
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Skip .env files - they are supposed to contain credentials
                if (file.name.endswith('.env') or 
                    file.name.endswith('.env.example') or
                    file.name.startswith('.env.') or
                    '.env.' in file.name):
                    result.add_info(f"Skipping .env file (expected to contain config): {file.name}")
                    return result
                
                # Check each secret pattern
                for pattern, description in ConfigValidator.SECRET_PATTERNS:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        result.add_error(
                            f"Potential {description} found in {file.name} at line {line_num}"
                        )
        
        except Exception as e:
            result.add_warning(f"Failed to scan file {file_path}: {str(e)}")
        
        return result

    
    @staticmethod
    def scan_directory_for_secrets(directory: str, exclude_dirs: List[str] = None) -> ValidationResult:
        """
        Recursively scan a directory for hardcoded secrets.
        
        Args:
            directory: Root directory to scan
            exclude_dirs: List of directory names to exclude (e.g., ['node_modules', 'venv'])
        
        Returns:
            ValidationResult aggregating all secret scan results
        
        **Validates: Requirement 14.5**
        """
        if exclude_dirs is None:
            exclude_dirs = ['node_modules', 'venv', '__pycache__', '.git', 
                          '.mypy_cache', '.pytest_cache', 'dist', 'build']
        
        result = ValidationResult()
        dir_path = Path(directory)
        
        if not dir_path.exists():
            result.add_error(f"Directory not found: {directory}")
            return result
        
        scanned_files = 0
        for file_path in dir_path.rglob('*'):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue
            
            # Scan the file
            file_result = ConfigValidator.scan_for_secrets(str(file_path))
            scanned_files += 1
            
            # Aggregate results
            for error in file_result.errors:
                result.add_error(error)
            for warning in file_result.warnings:
                result.add_warning(warning)
        
        result.add_info(f"Scanned {scanned_files} files in {directory}")
        
        if result.passed:
            result.add_info("✅ No hardcoded secrets detected")
        
        return result



class ConfigTemplateGenerator:
    """
    Generates configuration file templates for different environments.
    
    Implements:
    - Environment-specific configuration templates (.env.dev, .env.staging, .env.prod)
    - Backend configuration templates
    - Frontend configuration templates
    - Docker Compose configuration templates
    
    **Validates: Requirements 14.1, 14.2, 14.3, 14.4**
    """
    
    @staticmethod
    def generate_backend_template(
        environment: Environment,
        include_postgres: bool = False,
        include_mongo: bool = False,
        output_path: str = None
    ) -> str:
        """
        Generate backend .env template for a specific environment.
        
        Args:
            environment: Target environment (development, staging, production)
            include_postgres: Include PostgreSQL configuration
            include_mongo: Include MongoDB configuration
            output_path: Optional path to write the template file
        
        Returns:
            Template content as string
        
        **Validates: Requirement 14.1, 14.3, 14.4**
        """
        lines = [
            f"# Backend Configuration Template - {environment.value.upper()}",
            "# Generated by Workflow Configuration System",
            "",
            "# Application Configuration",
            f"APP_ENV={environment.value}",
        ]
        
        # Environment-specific settings
        if environment == Environment.DEVELOPMENT:
            lines.extend([
                "DEBUG=True",
                "LOG_LEVEL=DEBUG",
                "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000",
            ])
        elif environment == Environment.STAGING:
            lines.extend([
                "DEBUG=False",
                "LOG_LEVEL=INFO",
                "CORS_ORIGINS=https://staging.example.com",
            ])
        elif environment == Environment.PRODUCTION:
            lines.extend([
                "DEBUG=False",
                "LOG_LEVEL=WARNING",
                "CORS_ORIGINS=https://example.com",
            ])
        
        lines.append("")
        
        # PostgreSQL configuration
        if include_postgres:
            lines.extend([
                "# PostgreSQL Configuration",
                "POSTGRES_HOST=localhost",
                "POSTGRES_PORT=5432",
                "POSTGRES_DB=your_database_name",
                "POSTGRES_USER=your_database_user",
                "POSTGRES_PASSWORD={{POSTGRES_PASSWORD}}  # Replace with actual password",
                "DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}",
                "",
            ])
        
        # MongoDB configuration
        if include_mongo:
            lines.extend([
                "# MongoDB Configuration",
                "MONGO_HOST=localhost",
                "MONGO_PORT=27017",
                "MONGO_DB=your_database_name",
                "MONGO_USER=your_database_user",
                "MONGO_PASSWORD={{MONGO_PASSWORD}}  # Replace with actual password",
                "MONGO_URL=mongodb://${MONGO_USER}:${MONGO_PASSWORD}@${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}?authSource=admin",
                "",
            ])
        
        # Security settings
        lines.extend([
            "# Security (use strong random values in production)",
            "SECRET_KEY={{SECRET_KEY}}  # Replace with actual secret",
            "JWT_SECRET={{JWT_SECRET}}  # Replace with actual JWT secret",
            "",
        ])
        
        # API keys placeholder
        lines.extend([
            "# External API Keys (add as needed)",
            "# OPENAI_API_KEY={{OPENAI_API_KEY}}",
            "# STRIPE_API_KEY={{STRIPE_API_KEY}}",
            "",
        ])
        
        template = "\n".join(lines)
        
        # Write to file if path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(template)
        
        return template

    
    @staticmethod
    def generate_frontend_template(
        environment: Environment,
        backend_url: str = None,
        output_path: str = None
    ) -> str:
        """
        Generate frontend .env template for a specific environment.
        
        Args:
            environment: Target environment (development, staging, production)
            backend_url: Backend API URL for this environment
            output_path: Optional path to write the template file
        
        Returns:
            Template content as string
        
        **Validates: Requirement 14.2, 14.4**
        """
        # Default backend URLs by environment
        if backend_url is None:
            if environment == Environment.DEVELOPMENT:
                backend_url = "http://localhost:8000"
            elif environment == Environment.STAGING:
                backend_url = "https://api-staging.example.com"
            elif environment == Environment.PRODUCTION:
                backend_url = "https://api.example.com"
        
        lines = [
            f"# Frontend Configuration Template - {environment.value.upper()}",
            "# Generated by Workflow Configuration System",
            "",
            "# Next.js Configuration",
            "# Note: Variables must be prefixed with NEXT_PUBLIC_ to be available in browser",
            "",
            "# API Configuration",
            f"NEXT_PUBLIC_API_URL={backend_url}",
            "",
        ]
        
        # Environment-specific settings
        if environment == Environment.DEVELOPMENT:
            lines.extend([
                "# Development Settings",
                "NEXT_PUBLIC_ENVIRONMENT=development",
                "NEXT_PUBLIC_ENABLE_DEBUG=true",
                "",
            ])
        elif environment == Environment.STAGING:
            lines.extend([
                "# Staging Settings",
                "NEXT_PUBLIC_ENVIRONMENT=staging",
                "NEXT_PUBLIC_ENABLE_DEBUG=false",
                "",
            ])
        elif environment == Environment.PRODUCTION:
            lines.extend([
                "# Production Settings",
                "NEXT_PUBLIC_ENVIRONMENT=production",
                "NEXT_PUBLIC_ENABLE_DEBUG=false",
                "",
            ])
        
        # Feature flags
        lines.extend([
            "# Feature Flags",
            "NEXT_PUBLIC_FEATURE_AUTH=true",
            "NEXT_PUBLIC_FEATURE_ANALYTICS=true",
            "",
        ])
        
        # Analytics and monitoring (optional)
        lines.extend([
            "# Analytics (add your keys)",
            "# NEXT_PUBLIC_GA_ID={{GA_ID}}",
            "# NEXT_PUBLIC_SENTRY_DSN={{SENTRY_DSN}}",
            "",
        ])
        
        template = "\n".join(lines)
        
        # Write to file if path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(template)
        
        return template

    
    @staticmethod
    def generate_docker_compose_template(
        environment: Environment,
        include_postgres: bool = False,
        include_mongo: bool = False,
        output_path: str = None
    ) -> str:
        """
        Generate Docker Compose template for a specific environment.
        
        Args:
            environment: Target environment (development, staging, production)
            include_postgres: Include PostgreSQL service
            include_mongo: Include MongoDB service
            output_path: Optional path to write the template file
        
        Returns:
            Template content as string
        
        **Validates: Requirement 14.4**
        """
        lines = [
            f"# Docker Compose Configuration - {environment.value.upper()}",
            "# Generated by Workflow Configuration System",
            "",
            "version: '3.8'",
            "",
            "services:",
        ]
        
        # Backend service
        lines.extend([
            "  backend:",
            "    build:",
            "      context: ./backend",
            "      dockerfile: Dockerfile",
            f"    container_name: backend_{environment.value}",
            "    ports:",
            "      - \"8000:8000\"",
            "    environment:",
            f"      - APP_ENV={environment.value}",
            "    env_file:",
            f"      - ./backend/.env.{environment.value}",
        ])
        
        if include_postgres or include_mongo:
            lines.append("    depends_on:")
            if include_postgres:
                lines.append("      - postgres")
            if include_mongo:
                lines.append("      - mongo")
        
        lines.extend([
            "    networks:",
            "      - app_network",
            "    restart: unless-stopped",
            "",
        ])
        
        # Frontend service
        lines.extend([
            "  frontend:",
            "    build:",
            "      context: ./frontend",
            "      dockerfile: Dockerfile",
            f"    container_name: frontend_{environment.value}",
            "    ports:",
            "      - \"3000:3000\"",
            "    environment:",
            f"      - NEXT_PUBLIC_ENVIRONMENT={environment.value}",
            "    env_file:",
            f"      - ./frontend/.env.{environment.value}",
            "    depends_on:",
            "      - backend",
            "    networks:",
            "      - app_network",
            "    restart: unless-stopped",
            "",
        ])
        
        # PostgreSQL service
        if include_postgres:
            lines.extend([
                "  postgres:",
                "    image: postgres:15",
                f"    container_name: postgres_{environment.value}",
                "    ports:",
                "      - \"5432:5432\"",
                "    environment:",
                "      - POSTGRES_DB=${POSTGRES_DB}",
                "      - POSTGRES_USER=${POSTGRES_USER}",
                "      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}",
                "    volumes:",
                f"      - postgres_data_{environment.value}:/var/lib/postgresql/data",
                "    networks:",
                "      - app_network",
                "    restart: unless-stopped",
                "",
            ])
        
        # MongoDB service
        if include_mongo:
            lines.extend([
                "  mongo:",
                "    image: mongo:7",
                f"    container_name: mongo_{environment.value}",
                "    ports:",
                "      - \"27017:27017\"",
                "    environment:",
                "      - MONGO_INITDB_ROOT_USERNAME=${MONGO_USER}",
                "      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}",
                "      - MONGO_INITDB_DATABASE=${MONGO_DB}",
                "    volumes:",
                f"      - mongo_data_{environment.value}:/data/db",
                "    networks:",
                "      - app_network",
                "    restart: unless-stopped",
                "",
            ])
        
        # Networks
        lines.extend([
            "networks:",
            "  app_network:",
            "    driver: bridge",
            "",
        ])
        
        # Volumes
        if include_postgres or include_mongo:
            lines.append("volumes:")
            if include_postgres:
                lines.append(f"  postgres_data_{environment.value}:")
            if include_mongo:
                lines.append(f"  mongo_data_{environment.value}:")
        
        template = "\n".join(lines)
        
        # Write to file if path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(template)
        
        return template



class ConfigDocGenerator:
    """
    Generates configuration documentation for the workflow system.
    
    Implements:
    - Comprehensive documentation of all configuration options
    - Environment-specific configuration guides
    - Security best practices documentation
    
    **Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5**
    """
    
    @staticmethod
    def generate_configuration_guide(output_path: str = None) -> str:
        """
        Generate comprehensive configuration documentation.
        
        Args:
            output_path: Optional path to write the documentation
        
        Returns:
            Documentation content as string
        """
        doc = """# Configuration Guide

## Overview

The Supervised Agentic Workflow System uses environment-based configuration to manage
settings for different deployment scenarios. This guide covers all configuration options
and best practices.

## Workflow System Configuration

### Required Environment Variables

- **OPENAI_API_KEY**: Your OpenAI API key for LLM operations
  - Format: `sk-...` (48+ characters)
  - Security: Never commit this to version control

### Optional Environment Variables

- **LLM_MODEL**: OpenAI model to use (default: `gpt-4-turbo-preview`)
- **LLM_TEMPERATURE**: Temperature for LLM responses (default: `0.0`)
- **WORKFLOW_CHECKPOINT_DB**: Database for workflow state (default: `sqlite:///workflow_checkpoints.db`)
- **MAX_RETRIES_PER_AGENT**: Maximum retry attempts per agent (default: `5`)
- **MAX_TOTAL_RETRIES**: Maximum total retries across workflow (default: `20`)
- **DOCKER_HOST**: Docker daemon socket (default: `unix:///var/run/docker.sock`)
- **POSTGRES_IMAGE**: PostgreSQL Docker image (default: `postgres:15`)
- **POSTGRES_PORT**: PostgreSQL port (default: `5432`)
- **MONGO_IMAGE**: MongoDB Docker image (default: `mongo:7`)
- **MONGO_PORT**: MongoDB port (default: `27017`)
- **BACKEND_PORT**: Generated backend application port (default: `8000`)
- **FRONTEND_PORT**: Generated frontend application port (default: `3000`)
- **LOG_LEVEL**: Logging level (default: `INFO`, options: `DEBUG`, `INFO`, `WARNING`, `ERROR`)
- **LOG_FORMAT**: Log format (default: `colored`)
- **OUTPUT_DIR**: Root output directory (default: `./output`)
- **BACKEND_OUTPUT_DIR**: Backend code output (default: `./backend`)
- **FRONTEND_OUTPUT_DIR**: Frontend code output (default: `./frontend`)

## Generated Application Configuration

### Backend Configuration

The Backend Agent generates `.env` files with the following structure:

```env
# Application Configuration
APP_ENV=development
DEBUG=True
LOG_LEVEL=INFO

# PostgreSQL Configuration (if PostgreSQL is used)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=generated_secure_password
DATABASE_URL=postgresql://user:password@host:port/database

# MongoDB Configuration (if MongoDB is used)
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=your_database
MONGO_USER=your_user
MONGO_PASSWORD=generated_secure_password
MONGO_URL=mongodb://user:password@host:port/database?authSource=admin
```

### Frontend Configuration

The Frontend Agent should generate `.env.local` files with:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Environment
NEXT_PUBLIC_ENVIRONMENT=development
NEXT_PUBLIC_ENABLE_DEBUG=true

# Feature Flags
NEXT_PUBLIC_FEATURE_AUTH=true
```

**Important**: Next.js requires the `NEXT_PUBLIC_` prefix for environment variables
that need to be available in browser code.

## Environment-Specific Configuration

### Development Environment

- Use `APP_ENV=development`
- Enable debug logging (`DEBUG=True`, `LOG_LEVEL=DEBUG`)
- Allow localhost CORS origins
- Use local Docker containers for databases

### Staging Environment

- Use `APP_ENV=staging`
- Moderate logging (`DEBUG=False`, `LOG_LEVEL=INFO`)
- Restrict CORS to staging domain
- Use staging database instances

### Production Environment

- Use `APP_ENV=production`
- Minimal logging (`DEBUG=False`, `LOG_LEVEL=WARNING`)
- Restrict CORS to production domain
- Use production database instances with backups
- Enable security features (HTTPS, rate limiting, etc.)

## Security Best Practices

### 1. Never Hardcode Credentials

❌ **Bad:**
```python
DATABASE_URL = "postgresql://user:password123@localhost:5432/db"
```

✅ **Good:**
```python
DATABASE_URL = os.environ.get("DATABASE_URL")
```

### 2. Use Strong Random Passwords

The Database Agent generates secure random passwords using Python's `secrets` module:
- Minimum 16 characters
- Alphanumeric with special characters
- Cryptographically secure random generation

### 3. Store Secrets in .env Files

- Add `.env` to `.gitignore`
- Use `.env.example` as a template (without actual secrets)
- Never commit `.env` files to version control

### 4. Use Environment-Specific Configuration

- Separate `.env.dev`, `.env.staging`, `.env.prod` files
- Load appropriate file based on deployment environment
- Use different credentials for each environment

### 5. Validate Configuration

Use the configuration validation system to check for security issues:

```python
from workflow.config import ConfigValidator

# Validate workflow environment
result = ConfigValidator.validate_workflow_environment()
print(result)

# Scan for hardcoded secrets
result = ConfigValidator.scan_directory_for_secrets("./backend")
print(result)
```

## Docker Compose Configuration

The Deployment Agent generates environment-specific Docker Compose files:

- `docker-compose.dev.yml` - Development environment
- `docker-compose.staging.yml` - Staging environment
- `docker-compose.prod.yml` - Production environment

Each file includes appropriate service configurations, networking, and volume management.

## Troubleshooting

### Missing Environment Variables

If you see errors about missing environment variables:

1. Check that `.env` file exists in the project root
2. Verify all required variables are set
3. Run validation: `ConfigValidator.validate_workflow_environment()`

### Hardcoded Secrets Detected

If secret scanning finds hardcoded credentials:

1. Move credentials to `.env` file
2. Update code to read from environment variables
3. Re-run secret scan to verify fix

### Database Connection Issues

If database connections fail:

1. Verify Docker containers are running: `docker ps`
2. Check database credentials in `.env` file
3. Validate configuration: `ConfigValidator.validate_backend_environment()`
4. Check container logs: `docker logs <container_name>`

## Additional Resources

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/usage/settings/)
- [Next.js Environment Variables](https://nextjs.org/docs/basic-features/environment-variables)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
"""
        
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(doc)
        
        return doc
