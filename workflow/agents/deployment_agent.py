"""
Deployment Agent: Generates Docker configurations and deploys containers.

The Deployment Agent:
1. Generates Dockerfiles for frontend (Node.js 18+)
2. Generates Dockerfiles for backend (Python 3.11+)
3. Generates Docker Compose configuration (version 3.8)
4. Handles environment-specific configurations (dev, staging, prod)
5. Manages Docker networking between containers
6. Validates service health after deployment

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 12.5, 13.5, 14.4**
"""

import os
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import docker
from docker.models.containers import Container
from docker.errors import DockerException, APIError, BuildError

from ..config import get_config


class DeploymentAgent:
    """
    Deployment Agent that generates Docker configurations and deploys containers.
    
    **Validates: Requirements 8.1, 8.2, 12.5, 13.5, 14.4**
    """
    
    # Service validation settings
    HEALTH_CHECK_TIMEOUT = 30  # seconds (reduced from 60)
    HEALTH_CHECK_INTERVAL = 2  # seconds (reduced from 3)
    MAX_HEALTH_CHECK_ATTEMPTS = 15  # attempts (reduced from 20)
    
    def __init__(self):
        """Initialize the Deployment Agent."""
        self.config = get_config()
        
        try:
            self.docker_client = docker.from_env()
            print("   ✅ Docker client initialized")
        except DockerException as e:
            print(f"   ❌ Failed to initialize Docker client: {str(e)}")
            raise
    
    def check_containers_status(self) -> Dict[str, Any]:
        """
        Check if containers are already running and healthy.
        
        Returns:
            Dictionary with container status information
        """
        status = {
            "frontend_running": False,
            "backend_running": False,
            "all_running": False,
            "containers": []
        }
        
        try:
            # Check for workflow containers
            containers = self.docker_client.containers.list(
                filters={"name": "workflow_"}
            )
            
            for container in containers:
                container_info = {
                    "name": container.name,
                    "status": container.status,
                    "id": container.short_id
                }
                status["containers"].append(container_info)
                
                if "frontend" in container.name and container.status == "running":
                    status["frontend_running"] = True
                elif "backend" in container.name and container.status == "running":
                    status["backend_running"] = True
            
            status["all_running"] = status["frontend_running"] and status["backend_running"]
            
        except Exception as e:
            print(f"      ⚠️  Error checking container status: {str(e)}")
        
        return status
    
    def generate_frontend_dockerfile(
        self,
        environment: str = "dev"
    ) -> str:
        """
        Generate Dockerfile for Next.js frontend application.
        
        Uses Node.js 18+ base image with multi-stage build for optimization.
        
        Args:
            environment: Target environment (dev, staging, prod)
            
        Returns:
            Dockerfile content as string
            
        **Validates: Requirements 8.1, 14.4**
        """
        print(f"   📝 Generating frontend Dockerfile (environment: {environment})...")
        
        if environment == "prod":
            # Production: Multi-stage build with optimization
            dockerfile = """# Multi-stage build for Next.js frontend
# Stage 1: Dependencies
FROM node:18-alpine AS deps
WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Stage 2: Builder
FROM node:18-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 3: Production
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
"""
        else:
            # Development/Staging: Simpler build with hot-reload support
            dockerfile = """# Development/Staging Dockerfile for Next.js frontend
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
"""
        
        print(f"      ✅ Frontend Dockerfile generated")
        return dockerfile
    
    def generate_backend_dockerfile(
        self,
        environment: str = "dev"
    ) -> str:
        """
        Generate Dockerfile for FastAPI backend application.
        
        Uses Python 3.11+ base image with proper dependency management.
        
        Args:
            environment: Target environment (dev, staging, prod)
            
        Returns:
            Dockerfile content as string
            
        **Validates: Requirements 8.2, 14.4**
        """
        print(f"   📝 Generating backend Dockerfile (environment: {environment})...")
        
        if environment == "prod":
            # Production: Multi-stage build with optimization
            dockerfile = """# Multi-stage build for FastAPI backend
# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        else:
            # Development/Staging: Simpler build with hot-reload
            dockerfile = """# Development/Staging Dockerfile for FastAPI backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start the application with hot-reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
"""
        
        print(f"      ✅ Backend Dockerfile generated")
        return dockerfile
    
    def generate_docker_compose(
        self,
        database_config: Optional[Dict[str, Any]] = None,
        environment: str = "dev"
    ) -> str:
        """
        Generate Docker Compose configuration file.
        
        Creates a complete docker-compose.yml with:
        - Frontend service (Next.js)
        - Backend service (FastAPI)
        - PostgreSQL database (if configured)
        - MongoDB database (if configured)
        - Proper networking and dependencies
        - Environment-specific settings
        
        Args:
            database_config: Database configuration from Database Agent
            environment: Target environment (dev, staging, prod)
            
        Returns:
            Docker Compose YAML content as string
            
        **Validates: Requirements 8.3, 8.4, 13.5, 14.4**
        """
        print(f"   📝 Generating Docker Compose configuration (environment: {environment})...")
        
        # Extract database configurations
        has_postgres = False
        has_mongo = False
        postgres_password = "changeme"
        postgres_user = "app_user"
        postgres_db = "app_db"
        mongo_password = "changeme"
        mongo_user = "app_user"
        mongo_db = "app_db"
        
        if database_config:
            # Check for PostgreSQL config
            if "postgres" in database_config and database_config["postgres"].get("success"):
                has_postgres = True
                pg_config = database_config["postgres"]
                postgres_password = pg_config.get("password", postgres_password)
                postgres_user = pg_config.get("username", postgres_user)
                postgres_db = pg_config.get("database", postgres_db)
            
            # Check for MongoDB config
            if "mongo" in database_config and database_config["mongo"].get("success"):
                has_mongo = True
                mongo_config = database_config["mongo"]
                mongo_password = mongo_config.get("password", mongo_password)
                mongo_user = mongo_config.get("username", mongo_user)
                mongo_db = mongo_config.get("database", mongo_db)
        
        # Start building Docker Compose file
        compose_lines = [
            "version: '3.8'",
            "",
            "services:",
            "  # Frontend Service (Next.js)",
            "  frontend:",
            "    build:",
            "      context: ./frontend",
            "      dockerfile: Dockerfile",
            "    container_name: workflow_frontend",
            "    ports:",
            f"      - \"{self.config.frontend_port}:3000\"",
            "    environment:",
            f"      - NEXT_PUBLIC_API_URL=http://localhost:{self.config.backend_port}",
            "      - NODE_ENV=" + environment,
            "    depends_on:",
            "      - backend",
            "    networks:",
            "      - workflow_network",
            "    restart: unless-stopped",
            "",
            "  # Backend Service (FastAPI)",
            "  backend:",
            "    build:",
            "      context: ./backend",
            "      dockerfile: Dockerfile",
            "    container_name: workflow_backend",
            "    ports:",
            f"      - \"{self.config.backend_port}:8000\"",
            "    environment:",
            f"      - APP_ENV={environment}",
        ]
        
        # Add database environment variables for backend
        if has_postgres:
            compose_lines.extend([
                f"      - POSTGRES_HOST=postgres",
                f"      - POSTGRES_PORT=5432",
                f"      - POSTGRES_DB={postgres_db}",
                f"      - POSTGRES_USER={postgres_user}",
                f"      - POSTGRES_PASSWORD={postgres_password}",
                f"      - DATABASE_URL=postgresql+asyncpg://{postgres_user}:{postgres_password}@postgres:5432/{postgres_db}",
            ])
        
        if has_mongo:
            compose_lines.extend([
                f"      - MONGO_HOST=mongo",
                f"      - MONGO_PORT=27017",
                f"      - MONGO_DB={mongo_db}",
                f"      - MONGO_USER={mongo_user}",
                f"      - MONGO_PASSWORD={mongo_password}",
                f"      - MONGO_URL=mongodb://{mongo_user}:{mongo_password}@mongo:27017/{mongo_db}?authSource=admin",
            ])
        
        # Add backend dependencies
        compose_lines.extend([
            "    depends_on:",
        ])
        
        if has_postgres:
            compose_lines.append("      - postgres")
        if has_mongo:
            compose_lines.append("      - mongo")
        
        compose_lines.extend([
            "    networks:",
            "      - workflow_network",
            "    restart: unless-stopped",
            "",
        ])
        
        # Add PostgreSQL service if configured
        if has_postgres:
            compose_lines.extend([
                "  # PostgreSQL Database",
                "  postgres:",
                f"    image: {self.config.postgres_image}",
                "    container_name: workflow_postgres",
                "    environment:",
                f"      - POSTGRES_DB={postgres_db}",
                f"      - POSTGRES_USER={postgres_user}",
                f"      - POSTGRES_PASSWORD={postgres_password}",
                "    ports:",
                f"      - \"{self.config.postgres_port}:5432\"",
                "    volumes:",
                "      - postgres_data:/var/lib/postgresql/data",
                "    networks:",
                "      - workflow_network",
                "    restart: unless-stopped",
                "    healthcheck:",
                "      test: [\"CMD-SHELL\", \"pg_isready -U " + postgres_user + "\"]",
                "      interval: 10s",
                "      timeout: 5s",
                "      retries: 5",
                "",
            ])
        
        # Add MongoDB service if configured
        if has_mongo:
            compose_lines.extend([
                "  # MongoDB Database",
                "  mongo:",
                f"    image: {self.config.mongo_image}",
                "    container_name: workflow_mongo",
                "    environment:",
                f"      - MONGO_INITDB_ROOT_USERNAME={mongo_user}",
                f"      - MONGO_INITDB_ROOT_PASSWORD={mongo_password}",
                f"      - MONGO_INITDB_DATABASE={mongo_db}",
                "    ports:",
                f"      - \"{self.config.mongo_port}:27017\"",
                "    volumes:",
                "      - mongo_data:/data/db",
                "    networks:",
                "      - workflow_network",
                "    restart: unless-stopped",
                "    healthcheck:",
                "      test: [\"CMD\", \"mongosh\", \"--eval\", \"db.adminCommand('ping')\"]",
                "      interval: 10s",
                "      timeout: 5s",
                "      retries: 5",
                "",
            ])
        
        # Add Docker networks
        compose_lines.extend([
            "# Docker Networks",
            "networks:",
            "  workflow_network:",
            "    driver: bridge",
            "    name: workflow_network",
            "",
        ])
        
        # Add volumes if databases are configured
        if has_postgres or has_mongo:
            compose_lines.append("# Persistent Volumes")
            compose_lines.append("volumes:")
            
            if has_postgres:
                compose_lines.append("  postgres_data:")
                compose_lines.append("    driver: local")
            
            if has_mongo:
                compose_lines.append("  mongo_data:")
                compose_lines.append("    driver: local")
        
        docker_compose_content = "\n".join(compose_lines)
        print(f"      ✅ Docker Compose configuration generated")
        return docker_compose_content
    
    def save_docker_configurations(
        self,
        frontend_path: str,
        backend_path: str,
        project_root: str,
        database_config: Optional[Dict[str, Any]] = None,
        environment: str = "dev"
    ) -> Dict[str, str]:
        """
        Save all Docker configuration files to disk.
        
        Args:
            frontend_path: Path to frontend directory
            backend_path: Path to backend directory
            project_root: Path to project root directory
            database_config: Database configuration from Database Agent
            environment: Target environment (dev, staging, prod)
            
        Returns:
            Dictionary with paths to created files
            
        **Validates: Requirements 8.1, 8.2, 13.5, 14.4**
        """
        print(f"\n   💾 Saving Docker configurations...")
        
        created_files = {}
        
        # Generate and save frontend Dockerfile
        frontend_dockerfile = self.generate_frontend_dockerfile(environment)
        frontend_dockerfile_path = os.path.join(frontend_path, "Dockerfile")
        os.makedirs(frontend_path, exist_ok=True)
        with open(frontend_dockerfile_path, 'w') as f:
            f.write(frontend_dockerfile)
        created_files['frontend_dockerfile'] = frontend_dockerfile_path
        print(f"      ✅ Frontend Dockerfile saved to {frontend_dockerfile_path}")
        
        # Generate and save backend Dockerfile
        backend_dockerfile = self.generate_backend_dockerfile(environment)
        backend_dockerfile_path = os.path.join(backend_path, "Dockerfile")
        os.makedirs(backend_path, exist_ok=True)
        with open(backend_dockerfile_path, 'w') as f:
            f.write(backend_dockerfile)
        created_files['backend_dockerfile'] = backend_dockerfile_path
        print(f"      ✅ Backend Dockerfile saved to {backend_dockerfile_path}")
        
        # Generate and save Docker Compose configuration
        docker_compose = self.generate_docker_compose(database_config, environment)
        docker_compose_path = os.path.join(project_root, f"docker-compose.{environment}.yml")
        with open(docker_compose_path, 'w') as f:
            f.write(docker_compose)
        created_files['docker_compose'] = docker_compose_path
        print(f"      ✅ Docker Compose configuration saved to {docker_compose_path}")
        
        # Also create a default docker-compose.yml that points to dev environment
        if environment == "dev":
            default_compose_path = os.path.join(project_root, "docker-compose.yml")
            with open(default_compose_path, 'w') as f:
                f.write(docker_compose)
            created_files['docker_compose_default'] = default_compose_path
            print(f"      ✅ Default docker-compose.yml created")
        
        print(f"\n   ✅ All Docker configurations saved successfully")
        return created_files

    def build_docker_images(
        self,
        frontend_path: str,
        backend_path: str,
        project_root: str
    ) -> Dict[str, Any]:
        """
        Build Docker images for frontend and backend using Docker SDK.
        
        Args:
            frontend_path: Path to frontend directory with Dockerfile
            backend_path: Path to backend directory with Dockerfile
            project_root: Path to project root directory
            
        Returns:
            Dictionary with build results and image information
            
        **Validates: Requirements 8.3, 14.4**
        """
        print(f"\n   🔨 Building Docker images...")
        
        build_results = {
            "frontend": {"success": False, "image_id": None, "errors": []},
            "backend": {"success": False, "image_id": None, "errors": []}
        }
        
        # Build frontend image
        try:
            print(f"      📦 Building frontend image...")
            frontend_image, frontend_logs = self.docker_client.images.build(
                path=frontend_path,
                tag="workflow_frontend:latest",
                rm=True,
                forcerm=True
            )
            build_results["frontend"]["success"] = True
            build_results["frontend"]["image_id"] = frontend_image.id
            print(f"      ✅ Frontend image built successfully: {frontend_image.short_id}")
        except BuildError as e:
            error_msg = f"Frontend build failed: {str(e)}"
            build_results["frontend"]["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        except APIError as e:
            error_msg = f"Docker API error building frontend: {str(e)}"
            build_results["frontend"]["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        except Exception as e:
            error_msg = f"Unexpected error building frontend: {str(e)}"
            build_results["frontend"]["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        
        # Build backend image
        try:
            print(f"      📦 Building backend image...")
            backend_image, backend_logs = self.docker_client.images.build(
                path=backend_path,
                tag="workflow_backend:latest",
                rm=True,
                forcerm=True
            )
            build_results["backend"]["success"] = True
            build_results["backend"]["image_id"] = backend_image.id
            print(f"      ✅ Backend image built successfully: {backend_image.short_id}")
        except BuildError as e:
            error_msg = f"Backend build failed: {str(e)}"
            build_results["backend"]["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        except APIError as e:
            error_msg = f"Docker API error building backend: {str(e)}"
            build_results["backend"]["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        except Exception as e:
            error_msg = f"Unexpected error building backend: {str(e)}"
            build_results["backend"]["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        
        # Check overall success
        all_success = build_results["frontend"]["success"] and build_results["backend"]["success"]
        
        if all_success:
            print(f"\n   ✅ All Docker images built successfully")
        else:
            print(f"\n   ❌ Some Docker images failed to build")
        
        return build_results

    def deploy_with_docker_compose(
        self,
        project_root: str,
        compose_file: str = "docker-compose.yml"
    ) -> Dict[str, Any]:
        """
        Deploy services using Docker Compose (docker-compose up -d).
        
        Args:
            project_root: Path to project root directory containing docker-compose.yml
            compose_file: Name of docker-compose file to use
            
        Returns:
            Dictionary with deployment results
            
        **Validates: Requirements 8.4, 14.4**
        """
        print(f"\n   🚀 Deploying services with Docker Compose...")
        
        deployment_result = {
            "success": False,
            "containers": [],
            "errors": [],
            "output": ""
        }
        
        compose_path = os.path.join(project_root, compose_file)
        
        if not os.path.exists(compose_path):
            error_msg = f"Docker Compose file not found: {compose_path}"
            deployment_result["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
            return deployment_result
        
        try:
            import subprocess
            
            # Run docker-compose up -d
            print(f"      📦 Starting services with docker-compose...")
            result = subprocess.run(
                ["docker-compose", "-f", compose_path, "up", "-d"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes timeout
            )
            
            deployment_result["output"] = result.stdout
            
            if result.returncode == 0:
                deployment_result["success"] = True
                print(f"      ✅ Services deployed successfully")
                
                # List running containers
                list_result = subprocess.run(
                    ["docker-compose", "-f", compose_path, "ps", "--format", "json"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if list_result.returncode == 0:
                    import json
                    try:
                        containers = json.loads(list_result.stdout)
                        if isinstance(containers, dict):
                            containers = [containers]
                        deployment_result["containers"] = [
                            {
                                "name": c.get("Name", "unknown"),
                                "service": c.get("Service", "unknown"),
                                "state": c.get("State", "unknown")
                            }
                            for c in containers
                        ]
                        print(f"      📋 Running containers: {len(deployment_result['containers'])}")
                    except json.JSONDecodeError:
                        # Fallback: parse text output
                        pass
            else:
                error_msg = f"docker-compose up failed with exit code {result.returncode}"
                deployment_result["errors"].append(error_msg)
                if result.stderr:
                    deployment_result["errors"].append(result.stderr)
                print(f"      ❌ {error_msg}")
                if result.stderr:
                    print(f"      ❌ Error output: {result.stderr[:500]}")
        
        except subprocess.TimeoutExpired:
            error_msg = "docker-compose up timed out after 3 minutes"
            deployment_result["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        except FileNotFoundError:
            error_msg = "docker-compose command not found. Is Docker Compose installed?"
            deployment_result["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        except Exception as e:
            error_msg = f"Unexpected error during deployment: {str(e)}"
            deployment_result["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        
        return deployment_result

    def quick_health_check(
        self,
        frontend_port: Optional[int] = None,
        backend_port: Optional[int] = None
    ) -> Dict[str, bool]:
        """
        Quick health check with minimal retries (5 seconds max per service).
        
        Args:
            frontend_port: Port where frontend is running
            backend_port: Port where backend is running
            
        Returns:
            Dictionary with quick health status
        """
        if frontend_port is None:
            frontend_port = self.config.frontend_port
        if backend_port is None:
            backend_port = self.config.backend_port
        
        health = {
            "frontend_healthy": False,
            "backend_healthy": False
        }
        
        try:
            import requests
            
            # Quick frontend check (3 attempts, 1 second apart)
            for attempt in range(3):
                try:
                    response = requests.get(f"http://localhost:{frontend_port}", timeout=2)
                    if response.status_code in [200, 304]:
                        health["frontend_healthy"] = True
                        break
                except:
                    if attempt < 2:
                        time.sleep(1)
            
            # Quick backend check (3 attempts, 1 second apart)
            for attempt in range(3):
                try:
                    response = requests.get(f"http://localhost:{backend_port}/health", timeout=2)
                    if response.status_code == 200:
                        health["backend_healthy"] = True
                        break
                except:
                    if attempt < 2:
                        time.sleep(1)
        
        except Exception:
            pass
        
        return health
    
    def validate_service_health(
        self,
        frontend_port: Optional[int] = None,
        backend_port: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate service health using HTTP health checks for frontend and backend.
        
        Args:
            frontend_port: Port where frontend is running (default from config)
            backend_port: Port where backend is running (default from config)
            
        Returns:
            Dictionary with health check results
            
        **Validates: Requirements 8.5, 14.4**
        """
        print(f"\n   🏥 Validating service health...")
        
        if frontend_port is None:
            frontend_port = self.config.frontend_port
        if backend_port is None:
            backend_port = self.config.backend_port
        
        health_results = {
            "frontend": {"healthy": False, "url": None, "status_code": None, "error": None},
            "backend": {"healthy": False, "url": None, "status_code": None, "error": None},
            "all_healthy": False
        }
        
        # Check frontend health
        frontend_url = f"http://localhost:{frontend_port}"
        health_results["frontend"]["url"] = frontend_url
        
        print(f"      🔍 Checking frontend at {frontend_url}...")
        try:
            import requests
            
            # Wait for service to be ready
            max_attempts = self.MAX_HEALTH_CHECK_ATTEMPTS
            for attempt in range(max_attempts):
                try:
                    response = requests.get(frontend_url, timeout=3)
                    health_results["frontend"]["status_code"] = response.status_code
                    
                    if response.status_code in [200, 304]:
                        health_results["frontend"]["healthy"] = True
                        print(f"      ✅ Frontend is healthy (status: {response.status_code})")
                        break
                    else:
                        print(f"      ⚠️  Frontend returned status {response.status_code}, retrying...")
                        time.sleep(self.HEALTH_CHECK_INTERVAL)
                except requests.exceptions.ConnectionError:
                    if attempt < max_attempts - 1:
                        print(f"      ⏳ Frontend not ready yet, waiting... (attempt {attempt + 1}/{max_attempts})")
                        time.sleep(self.HEALTH_CHECK_INTERVAL)
                    else:
                        raise
        except requests.exceptions.ConnectionError as e:
            health_results["frontend"]["error"] = f"Connection refused: {str(e)}"
            print(f"      ❌ Frontend health check failed: Connection refused")
        except requests.exceptions.Timeout as e:
            health_results["frontend"]["error"] = f"Timeout: {str(e)}"
            print(f"      ❌ Frontend health check timed out")
        except Exception as e:
            health_results["frontend"]["error"] = str(e)
            print(f"      ❌ Frontend health check error: {str(e)}")
        
        # Check backend health
        backend_health_url = f"http://localhost:{backend_port}/health"
        health_results["backend"]["url"] = backend_health_url
        
        print(f"      🔍 Checking backend at {backend_health_url}...")
        try:
            import requests
            
            # Wait for service to be ready
            max_attempts = self.MAX_HEALTH_CHECK_ATTEMPTS
            for attempt in range(max_attempts):
                try:
                    response = requests.get(backend_health_url, timeout=3)
                    health_results["backend"]["status_code"] = response.status_code
                    
                    if response.status_code == 200:
                        health_results["backend"]["healthy"] = True
                        print(f"      ✅ Backend is healthy (status: {response.status_code})")
                        break
                    else:
                        print(f"      ⚠️  Backend returned status {response.status_code}, retrying...")
                        time.sleep(self.HEALTH_CHECK_INTERVAL)
                except requests.exceptions.ConnectionError:
                    if attempt < max_attempts - 1:
                        print(f"      ⏳ Backend not ready yet, waiting... (attempt {attempt + 1}/{max_attempts})")
                        time.sleep(self.HEALTH_CHECK_INTERVAL)
                    else:
                        raise
        except requests.exceptions.ConnectionError as e:
            health_results["backend"]["error"] = f"Connection refused: {str(e)}"
            print(f"      ❌ Backend health check failed: Connection refused")
        except requests.exceptions.Timeout as e:
            health_results["backend"]["error"] = f"Timeout: {str(e)}"
            print(f"      ❌ Backend health check timed out")
        except Exception as e:
            health_results["backend"]["error"] = str(e)
            print(f"      ❌ Backend health check error: {str(e)}")
        
        # Overall health
        health_results["all_healthy"] = (
            health_results["frontend"]["healthy"] and 
            health_results["backend"]["healthy"]
        )
        
        if health_results["all_healthy"]:
            print(f"\n   ✅ All services are healthy")
        else:
            print(f"\n   ❌ Some services are unhealthy")
        
        return health_results

    def validate_database_connection_from_backend(
        self,
        backend_container_name: str = "workflow_backend",
        database_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate database connections from the backend container.
        
        Tests that the backend container can successfully connect to
        PostgreSQL and MongoDB databases.
        
        Args:
            backend_container_name: Name of backend container
            database_config: Database configuration with connection details
            
        Returns:
            Dictionary with validation results
            
        **Validates: Requirements 8.6, 14.4**
        """
        print(f"\n   🔌 Validating database connections from backend...")
        
        validation_results = {
            "postgres": {"connected": False, "error": None},
            "mongo": {"connected": False, "error": None},
            "all_connected": False
        }
        
        if not database_config:
            print(f"      ⚠️  No database configuration provided, skipping validation")
            return validation_results
        
        try:
            # Get the backend container
            container = self.docker_client.containers.get(backend_container_name)
            
            # Check PostgreSQL connection
            if "postgres" in database_config and database_config["postgres"].get("success"):
                print(f"      🔍 Testing PostgreSQL connection from backend container...")
                try:
                    pg_test_cmd = [
                        "python", "-c",
                        "import psycopg2; "
                        "import os; "
                        "conn = psycopg2.connect(os.environ.get('DATABASE_URL')); "
                        "conn.close(); "
                        "print('PostgreSQL connection successful')"
                    ]
                    
                    exec_result = container.exec_run(pg_test_cmd, environment={
                        "DATABASE_URL": database_config["postgres"].get("connection_string", "")
                    })
                    
                    if exec_result.exit_code == 0:
                        validation_results["postgres"]["connected"] = True
                        print(f"      ✅ PostgreSQL connection successful")
                    else:
                        error_msg = exec_result.output.decode('utf-8') if exec_result.output else "Unknown error"
                        validation_results["postgres"]["error"] = error_msg
                        print(f"      ❌ PostgreSQL connection failed: {error_msg[:200]}")
                except Exception as e:
                    validation_results["postgres"]["error"] = str(e)
                    print(f"      ❌ PostgreSQL validation error: {str(e)}")
            
            # Check MongoDB connection
            if "mongo" in database_config and database_config["mongo"].get("success"):
                print(f"      🔍 Testing MongoDB connection from backend container...")
                try:
                    mongo_test_cmd = [
                        "python", "-c",
                        "from pymongo import MongoClient; "
                        "import os; "
                        "client = MongoClient(os.environ.get('MONGO_URL')); "
                        "client.server_info(); "
                        "client.close(); "
                        "print('MongoDB connection successful')"
                    ]
                    
                    exec_result = container.exec_run(mongo_test_cmd, environment={
                        "MONGO_URL": database_config["mongo"].get("connection_string", "")
                    })
                    
                    if exec_result.exit_code == 0:
                        validation_results["mongo"]["connected"] = True
                        print(f"      ✅ MongoDB connection successful")
                    else:
                        error_msg = exec_result.output.decode('utf-8') if exec_result.output else "Unknown error"
                        validation_results["mongo"]["error"] = error_msg
                        print(f"      ❌ MongoDB connection failed: {error_msg[:200]}")
                except Exception as e:
                    validation_results["mongo"]["error"] = str(e)
                    print(f"      ❌ MongoDB validation error: {str(e)}")
        
        except docker.errors.NotFound:
            error_msg = f"Backend container '{backend_container_name}' not found"
            validation_results["postgres"]["error"] = error_msg
            validation_results["mongo"]["error"] = error_msg
            print(f"      ❌ {error_msg}")
        except Exception as e:
            error_msg = f"Container validation error: {str(e)}"
            validation_results["postgres"]["error"] = error_msg
            validation_results["mongo"]["error"] = error_msg
            print(f"      ❌ {error_msg}")
        
        # Check overall connection status
        has_postgres = "postgres" in database_config and database_config["postgres"].get("success")
        has_mongo = "mongo" in database_config and database_config["mongo"].get("success")
        
        if has_postgres and has_mongo:
            validation_results["all_connected"] = (
                validation_results["postgres"]["connected"] and 
                validation_results["mongo"]["connected"]
            )
        elif has_postgres:
            validation_results["all_connected"] = validation_results["postgres"]["connected"]
        elif has_mongo:
            validation_results["all_connected"] = validation_results["mongo"]["connected"]
        else:
            validation_results["all_connected"] = True  # No databases to validate
        
        if validation_results["all_connected"]:
            print(f"\n   ✅ All database connections validated")
        else:
            print(f"\n   ❌ Some database connections failed")
        
        return validation_results

    def output_service_endpoints(
        self,
        frontend_port: Optional[int] = None,
        backend_port: Optional[int] = None,
        database_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate and output service endpoint URLs.
        
        Args:
            frontend_port: Port where frontend is running
            backend_port: Port where backend is running
            database_config: Database configuration
            
        Returns:
            Dictionary with service endpoint URLs
            
        **Validates: Requirements 8.7, 14.4**
        """
        print(f"\n   📍 Service Endpoints:")
        print(f"   " + "=" * 60)
        
        if frontend_port is None:
            frontend_port = self.config.frontend_port
        if backend_port is None:
            backend_port = self.config.backend_port
        
        endpoints = {}
        
        # Frontend endpoint
        frontend_url = f"http://localhost:{frontend_port}"
        endpoints["frontend"] = frontend_url
        print(f"   🌐 Frontend:    {frontend_url}")
        
        # Backend endpoint
        backend_url = f"http://localhost:{backend_port}"
        endpoints["backend"] = backend_url
        print(f"   🔧 Backend:     {backend_url}")
        
        # Backend health check
        backend_health = f"{backend_url}/health"
        endpoints["backend_health"] = backend_health
        print(f"   💚 Health:      {backend_health}")
        
        # Database endpoints
        if database_config:
            if "postgres" in database_config and database_config["postgres"].get("success"):
                pg_config = database_config["postgres"]
                postgres_url = f"postgresql://localhost:{self.config.postgres_port}/{pg_config.get('database', 'app_db')}"
                endpoints["postgres"] = postgres_url
                print(f"   🗄️  PostgreSQL:  {postgres_url}")
            
            if "mongo" in database_config and database_config["mongo"].get("success"):
                mongo_config = database_config["mongo"]
                mongo_url = f"mongodb://localhost:{self.config.mongo_port}/{mongo_config.get('database', 'app_db')}"
                endpoints["mongo"] = mongo_url
                print(f"   🍃 MongoDB:     {mongo_url}")
        
        print(f"   " + "=" * 60)
        
        return endpoints

    def cleanup_containers_on_failure(
        self,
        project_root: str,
        compose_file: str = "docker-compose.yml"
    ) -> Dict[str, Any]:
        """
        Clean up containers when deployment fails.
        
        Stops and removes all containers defined in the docker-compose file.
        
        Args:
            project_root: Path to project root directory
            compose_file: Name of docker-compose file
            
        Returns:
            Dictionary with cleanup results
            
        **Validates: Requirements 8.7, 14.4**
        """
        print(f"\n   🧹 Cleaning up containers after failure...")
        
        cleanup_result = {
            "success": False,
            "stopped_containers": [],
            "removed_containers": [],
            "errors": []
        }
        
        compose_path = os.path.join(project_root, compose_file)
        
        if not os.path.exists(compose_path):
            error_msg = f"Docker Compose file not found: {compose_path}"
            cleanup_result["errors"].append(error_msg)
            print(f"      ⚠️  {error_msg}")
            return cleanup_result
        
        try:
            import subprocess
            
            # Stop containers
            print(f"      🛑 Stopping containers...")
            stop_result = subprocess.run(
                ["docker-compose", "-f", compose_path, "stop"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if stop_result.returncode == 0:
                print(f"      ✅ Containers stopped")
            else:
                cleanup_result["errors"].append(f"Stop failed: {stop_result.stderr}")
            
            # Remove containers
            print(f"      🗑️  Removing containers...")
            down_result = subprocess.run(
                ["docker-compose", "-f", compose_path, "down", "-v"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if down_result.returncode == 0:
                cleanup_result["success"] = True
                print(f"      ✅ Containers and volumes removed")
            else:
                cleanup_result["errors"].append(f"Remove failed: {down_result.stderr}")
                print(f"      ❌ Failed to remove containers: {down_result.stderr[:200]}")
        
        except subprocess.TimeoutExpired:
            error_msg = "Cleanup timed out"
            cleanup_result["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        except FileNotFoundError:
            error_msg = "docker-compose command not found"
            cleanup_result["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        except Exception as e:
            error_msg = f"Cleanup error: {str(e)}"
            cleanup_result["errors"].append(error_msg)
            print(f"      ❌ {error_msg}")
        
        if cleanup_result["success"]:
            print(f"\n   ✅ Cleanup completed successfully")
        else:
            print(f"\n   ⚠️  Cleanup completed with errors")
        
        return cleanup_result

    def generate_deployment_diagnostics(
        self,
        build_results: Optional[Dict[str, Any]] = None,
        deployment_result: Optional[Dict[str, Any]] = None,
        health_results: Optional[Dict[str, Any]] = None,
        db_validation_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate detailed error reporting with diagnostics on deployment failure.
        
        Args:
            build_results: Results from Docker image builds
            deployment_result: Results from docker-compose deployment
            health_results: Results from service health checks
            db_validation_results: Results from database connection validation
            
        Returns:
            Dictionary with comprehensive diagnostics
            
        **Validates: Requirements 8.7, 14.4**
        """
        diagnostics = {
            "status": "unknown",
            "phase": "unknown",
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Check build phase
        if build_results:
            if not build_results.get("frontend", {}).get("success"):
                diagnostics["status"] = "failed"
                diagnostics["phase"] = "build"
                diagnostics["errors"].append("Frontend image build failed")
                diagnostics["errors"].extend(build_results["frontend"].get("errors", []))
                diagnostics["recommendations"].append(
                    "Check frontend Dockerfile and ensure all dependencies are available"
                )
            
            if not build_results.get("backend", {}).get("success"):
                diagnostics["status"] = "failed"
                diagnostics["phase"] = "build"
                diagnostics["errors"].append("Backend image build failed")
                diagnostics["errors"].extend(build_results["backend"].get("errors", []))
                diagnostics["recommendations"].append(
                    "Check backend Dockerfile and ensure all Python dependencies can be installed"
                )
        
        # Check deployment phase
        if deployment_result:
            if not deployment_result.get("success"):
                diagnostics["status"] = "failed"
                diagnostics["phase"] = "deployment"
                diagnostics["errors"].append("Docker Compose deployment failed")
                diagnostics["errors"].extend(deployment_result.get("errors", []))
                diagnostics["recommendations"].append(
                    "Check docker-compose.yml configuration and Docker daemon status"
                )
        
        # Check health phase
        if health_results:
            if not health_results.get("frontend", {}).get("healthy"):
                diagnostics["status"] = "failed"
                diagnostics["phase"] = "health_check"
                error = health_results["frontend"].get("error")
                if error:
                    diagnostics["errors"].append(f"Frontend health check failed: {error}")
                else:
                    diagnostics["errors"].append("Frontend is not responding")
                diagnostics["recommendations"].append(
                    "Check frontend container logs: docker logs workflow_frontend"
                )
            
            if not health_results.get("backend", {}).get("healthy"):
                diagnostics["status"] = "failed"
                diagnostics["phase"] = "health_check"
                error = health_results["backend"].get("error")
                if error:
                    diagnostics["errors"].append(f"Backend health check failed: {error}")
                else:
                    diagnostics["errors"].append("Backend is not responding")
                diagnostics["recommendations"].append(
                    "Check backend container logs: docker logs workflow_backend"
                )
        
        # Check database validation phase
        if db_validation_results:
            if not db_validation_results.get("all_connected"):
                diagnostics["status"] = "failed"
                diagnostics["phase"] = "database_validation"
                
                if db_validation_results.get("postgres", {}).get("error"):
                    diagnostics["errors"].append(
                        f"PostgreSQL connection failed: {db_validation_results['postgres']['error']}"
                    )
                    diagnostics["recommendations"].append(
                        "Check PostgreSQL container status: docker logs workflow_postgres"
                    )
                
                if db_validation_results.get("mongo", {}).get("error"):
                    diagnostics["errors"].append(
                        f"MongoDB connection failed: {db_validation_results['mongo']['error']}"
                    )
                    diagnostics["recommendations"].append(
                        "Check MongoDB container status: docker logs workflow_mongo"
                    )
        
        # Set status to success if no failures detected
        if diagnostics["status"] == "unknown":
            diagnostics["status"] = "success"
            diagnostics["phase"] = "complete"
        
        return diagnostics
    
    def print_deployment_diagnostics(self, diagnostics: Dict[str, Any]) -> None:
        """
        Print deployment diagnostics in a formatted way.
        
        Args:
            diagnostics: Diagnostics dictionary from generate_deployment_diagnostics
        """
        print(f"\n   📊 Deployment Diagnostics")
        print(f"   " + "=" * 60)
        print(f"   Status: {diagnostics['status'].upper()}")
        print(f"   Phase:  {diagnostics['phase']}")
        
        if diagnostics.get("errors"):
            print(f"\n   ❌ Errors:")
            for error in diagnostics["errors"]:
                print(f"      • {error}")
        
        if diagnostics.get("warnings"):
            print(f"\n   ⚠️  Warnings:")
            for warning in diagnostics["warnings"]:
                print(f"      • {warning}")
        
        if diagnostics.get("recommendations"):
            print(f"\n   💡 Recommendations:")
            for recommendation in diagnostics["recommendations"]:
                print(f"      • {recommendation}")
        
        print(f"   " + "=" * 60)

    def execute_task(
        self,
        backend_path: str = "./backend",
        frontend_path: str = "./frontend",
        database_config: Optional[Dict[str, Any]] = None,
        environment: str = "dev"
    ) -> Dict[str, Any]:
        """
        Execute the complete deployment workflow.
        
        This orchestrates all deployment steps:
        1. Generate Docker configurations (Dockerfiles, docker-compose.yml)
        2. Build Docker images for frontend and backend
        3. Deploy services using Docker Compose
        4. Validate service health
        5. Validate database connections
        6. Output service endpoints
        
        Args:
            backend_path: Path to backend directory
            frontend_path: Path to frontend directory
            database_config: Database configuration from Database Agent
            environment: Target environment (dev, staging, prod)
            
        Returns:
            Dictionary with deployment results and status
            
        **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7**
        """
        print(f"\n{'='*70}")
        print(f"🚀 DEPLOYMENT AGENT - Starting Deployment")
        print(f"{'='*70}")
        print(f"   Environment: {environment}")
        print(f"   Backend:     {backend_path}")
        print(f"   Frontend:    {frontend_path}")
        print(f"{'='*70}\n")
        
        # Get project root (parent of backend/frontend directories)
        backend_path_obj = Path(backend_path)
        frontend_path_obj = Path(frontend_path)
        project_root = str(backend_path_obj.parent.absolute())
        
        result = {
            "success": False,
            "deployment_status": None,
            "error": None,
            "build_results": None,
            "deployment_result": None,
            "health_results": None,
            "db_validation_results": None,
            "diagnostics": None,
            "endpoints": None
        }
        
        try:
            # FAST PATH: Check if containers are already running and healthy
            print(f"\n🔍 PRE-CHECK: Checking existing containers")
            print(f"-" * 70)
            container_status = self.check_containers_status()
            
            if container_status["all_running"]:
                print(f"   ✅ Found running containers:")
                for container in container_status["containers"]:
                    print(f"      • {container['name']} ({container['status']})")
                
                # Quick health check on existing containers
                print(f"\n   ⚡ Quick health check...")
                quick_health = self.quick_health_check(
                    frontend_port=self.config.frontend_port,
                    backend_port=self.config.backend_port
                )
                
                if quick_health["frontend_healthy"] and quick_health["backend_healthy"]:
                    print(f"   ✅ All services are already running and healthy!")
                    print(f"\n   ⚡ FAST PATH: Skipping rebuild and redeployment\n")
                    
                    # Generate endpoints
                    endpoints = self.output_service_endpoints(
                        frontend_port=self.config.frontend_port,
                        backend_port=self.config.backend_port,
                        database_config=database_config
                    )
                    result["endpoints"] = endpoints
                    
                    # Create deployment status
                    from datetime import datetime
                    from ..models import DeploymentStatus
                    
                    result["deployment_status"] = DeploymentStatus(
                        containers_running=[
                            {"name": c["name"], "status": c["status"]}
                            for c in container_status["containers"]
                        ],
                        frontend_url=endpoints.get("frontend", ""),
                        backend_url=endpoints.get("backend", ""),
                        health_checks_passed=True,
                        deployment_timestamp=datetime.now()
                    )
                    
                    result["success"] = True
                    
                    print(f"\n{'='*70}")
                    print(f"✅ DEPLOYMENT VERIFIED (Fast Path)")
                    print(f"{'='*70}")
                    print(f"\n   Services were already running and healthy!")
                    print(f"\n   🌐 Access your application at:")
                    print(f"      Frontend: {endpoints.get('frontend')}")
                    print(f"      Backend:  {endpoints.get('backend')}")
                    print(f"\n{'='*70}\n")
                    
                    return result
                else:
                    print(f"   ⚠️  Containers running but health checks failed")
                    print(f"   🔄 Proceeding with full deployment...\n")
            else:
                print(f"   ℹ️  No running containers found, proceeding with deployment\n")
            
            # NORMAL PATH: Full deployment process
            # Step 1: Generate and save Docker configurations
            print(f"\n📋 STEP 1: Generating Docker Configurations")
            print(f"-" * 70)
            created_files = self.save_docker_configurations(
                frontend_path=str(frontend_path_obj.absolute()),
                backend_path=str(backend_path_obj.absolute()),
                project_root=project_root,
                database_config=database_config,
                environment=environment
            )
            print(f"\n   ✅ Docker configurations created:")
            for key, path in created_files.items():
                print(f"      • {key}: {path}")
            
            # Step 2: Build Docker images
            print(f"\n🔨 STEP 2: Building Docker Images")
            print(f"-" * 70)
            build_results = self.build_docker_images(
                frontend_path=str(frontend_path_obj.absolute()),
                backend_path=str(backend_path_obj.absolute()),
                project_root=project_root
            )
            result["build_results"] = build_results
            
            # Check if builds succeeded
            if not (build_results["frontend"]["success"] and build_results["backend"]["success"]):
                error_msg = "Docker image builds failed"
                result["error"] = error_msg
                result["diagnostics"] = self.generate_deployment_diagnostics(
                    build_results=build_results
                )
                self.print_deployment_diagnostics(result["diagnostics"])
                return result
            
            # Step 3: Deploy with Docker Compose
            print(f"\n🚀 STEP 3: Deploying Services")
            print(f"-" * 70)
            deployment_result = self.deploy_with_docker_compose(
                project_root=project_root,
                compose_file=created_files.get("docker_compose", "docker-compose.yml").split("/")[-1]
            )
            result["deployment_result"] = deployment_result
            
            # Check if deployment succeeded
            if not deployment_result["success"]:
                error_msg = "Docker Compose deployment failed"
                result["error"] = error_msg
                result["diagnostics"] = self.generate_deployment_diagnostics(
                    build_results=build_results,
                    deployment_result=deployment_result
                )
                self.print_deployment_diagnostics(result["diagnostics"])
                
                # Cleanup containers on failure
                self.cleanup_containers_on_failure(
                    project_root=project_root,
                    compose_file=created_files.get("docker_compose", "docker-compose.yml").split("/")[-1]
                )
                return result
            
            # Step 4: Validate service health
            print(f"\n🏥 STEP 4: Validating Service Health")
            print(f"-" * 70)
            health_results = self.validate_service_health(
                frontend_port=self.config.frontend_port,
                backend_port=self.config.backend_port
            )
            result["health_results"] = health_results
            
            # Check if health checks passed
            if not health_results["all_healthy"]:
                error_msg = "Service health checks failed"
                result["error"] = error_msg
                result["diagnostics"] = self.generate_deployment_diagnostics(
                    build_results=build_results,
                    deployment_result=deployment_result,
                    health_results=health_results
                )
                self.print_deployment_diagnostics(result["diagnostics"])
                
                # Cleanup containers on failure
                self.cleanup_containers_on_failure(
                    project_root=project_root,
                    compose_file=created_files.get("docker_compose", "docker-compose.yml").split("/")[-1]
                )
                return result
            
            # Step 5: Validate database connections (if databases configured)
            if database_config:
                print(f"\n🔌 STEP 5: Validating Database Connections")
                print(f"-" * 70)
                db_validation_results = self.validate_database_connection_from_backend(
                    backend_container_name="workflow_backend",
                    database_config=database_config
                )
                result["db_validation_results"] = db_validation_results
                
                # Check if database connections succeeded
                if not db_validation_results["all_connected"]:
                    error_msg = "Database connection validation failed"
                    result["error"] = error_msg
                    result["diagnostics"] = self.generate_deployment_diagnostics(
                        build_results=build_results,
                        deployment_result=deployment_result,
                        health_results=health_results,
                        db_validation_results=db_validation_results
                    )
                    self.print_deployment_diagnostics(result["diagnostics"])
                    
                    # Note: Don't cleanup here as services are healthy, just DB connection issue
                    # User may want to debug the running containers
                    return result
            
            # Step 6: Output service endpoints
            print(f"\n📍 STEP 6: Service Endpoints")
            print(f"-" * 70)
            endpoints = self.output_service_endpoints(
                frontend_port=self.config.frontend_port,
                backend_port=self.config.backend_port,
                database_config=database_config
            )
            result["endpoints"] = endpoints
            
            # Create deployment status object
            from datetime import datetime
            from ..models import DeploymentStatus
            
            result["deployment_status"] = DeploymentStatus(
                containers_running=deployment_result.get("containers", []),
                frontend_url=endpoints.get("frontend", ""),
                backend_url=endpoints.get("backend", ""),
                health_checks_passed=health_results.get("all_healthy", False),
                deployment_timestamp=datetime.now()
            )
            
            # Success!
            result["success"] = True
            result["diagnostics"] = self.generate_deployment_diagnostics(
                build_results=build_results,
                deployment_result=deployment_result,
                health_results=health_results,
                db_validation_results=result.get("db_validation_results")
            )
            
            print(f"\n{'='*70}")
            print(f"✅ DEPLOYMENT SUCCESSFUL")
            print(f"{'='*70}")
            print(f"\n   All services are deployed and healthy!")
            print(f"\n   🌐 Access your application at:")
            print(f"      Frontend: {endpoints.get('frontend')}")
            print(f"      Backend:  {endpoints.get('backend')}")
            print(f"\n{'='*70}\n")
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"Deployment failed with exception: {str(e)}"
            result["error"] = error_msg
            result["exception_traceback"] = traceback.format_exc()
            
            print(f"\n{'='*70}")
            print(f"❌ DEPLOYMENT FAILED")
            print(f"{'='*70}")
            print(f"\n   Error: {error_msg}")
            print(f"\n   Traceback:\n{result['exception_traceback']}")
            print(f"\n{'='*70}\n")
            
            # Generate diagnostics
            result["diagnostics"] = self.generate_deployment_diagnostics(
                build_results=result.get("build_results"),
                deployment_result=result.get("deployment_result"),
                health_results=result.get("health_results"),
                db_validation_results=result.get("db_validation_results")
            )
            self.print_deployment_diagnostics(result["diagnostics"])
            
            return result
