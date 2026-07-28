# Configuration Guide

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
