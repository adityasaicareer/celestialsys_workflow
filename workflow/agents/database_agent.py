"""
Database Agent: Manages PostgreSQL and MongoDB containers with Docker SDK.

The Database Agent:
1. Initializes PostgreSQL database in Docker container
2. Initializes MongoDB database in Docker container
3. Generates strong random passwords using secrets module
4. Creates database schemas and migration scripts
5. Validates database connections before completion
6. Generates .env files for database configuration
7. Ensures proper Docker networking between containers

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 12.4, 14.3**
"""

import os
import secrets
import string
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from urllib.parse import quote_plus
import docker
from docker.models.containers import Container
from docker.models.networks import Network
from docker.errors import DockerException, APIError, NotFound
import psycopg2
from pymongo import MongoClient

from ..config import get_config


class DatabaseAgent:
    """
    Database Agent that manages PostgreSQL and MongoDB containers.
    
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
    """
    
    # Container configuration
    POSTGRES_CONTAINER_NAME = "workflow_postgres"
    MONGO_CONTAINER_NAME = "workflow_mongo"
    NETWORK_NAME = "workflow_network"
    
    # Connection timeouts
    CONNECTION_TIMEOUT = 30  # seconds
    CONNECTION_RETRY_INTERVAL = 2  # seconds
    
    def __init__(self):
        """Initialize the Database Agent."""
        self.config = get_config()
        
        try:
            self.docker_client = docker.from_env()
            print("   ✅ Docker client initialized")
        except DockerException as e:
            print(f"   ❌ Failed to initialize Docker client: {str(e)}")
            raise
    
    def generate_strong_password(self, length: int = 32) -> str:
        """
        Generate a cryptographically strong random password.
        
        Uses Python's secrets module for secure random generation.
        
        Args:
            length: Password length (default: 32)
            
        Returns:
            Strong random password string
            
        **Validates: Requirement 6.5**
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    def ensure_network_exists(self) -> Network:
        """
        Ensure Docker network exists for container communication.
        
        Returns:
            Docker network object
            
        **Validates: Requirement 12.4, 14.3**
        """
        try:
            # Check if network exists
            network = self.docker_client.networks.get(self.NETWORK_NAME)
            print(f"   ✅ Network '{self.NETWORK_NAME}' already exists")
            return network
        except NotFound:
            # Create network
            print(f"   📡 Creating Docker network '{self.NETWORK_NAME}'...")
            network = self.docker_client.networks.create(
                self.NETWORK_NAME,
                driver="bridge"
            )
            print(f"   ✅ Network '{self.NETWORK_NAME}' created")
            return network
    
    def stop_and_remove_container(self, container_name: str) -> None:
        """
        Stop and remove a container if it exists.
        
        Args:
            container_name: Name of container to remove
        """
        try:
            container = self.docker_client.containers.get(container_name)
            print(f"   🛑 Stopping existing container '{container_name}'...")
            container.stop()
            container.remove()
            print(f"   ✅ Container '{container_name}' removed")
        except NotFound:
            # Container doesn't exist, nothing to remove
            pass
        except Exception as e:
            print(f"   ⚠️  Error removing container '{container_name}': {str(e)}")
    
    def initialize_postgres(
        self,
        database_name: str = "app_db",
        username: str = "app_user"
    ) -> Dict[str, Any]:
        """
        Initialize PostgreSQL database in Docker container.
        
        Steps:
        1. Generate strong random password
        2. Ensure Docker network exists
        3. Stop and remove existing container (if any)
        4. Start new PostgreSQL container
        5. Wait for database to be ready
        6. Validate connection
        
        Args:
            database_name: Name of database to create
            username: Username for database access
            
        Returns:
            Dictionary with connection configuration:
            {
                "success": bool,
                "container_name": str,
                "host": str,
                "port": int,
                "database": str,
                "username": str,
                "password": str,
                "connection_string": str
            }
            
        **Validates: Requirements 6.1, 6.5, 12.4**
        """
        print(f"\n🐘 Initializing PostgreSQL database...")
        
        # Generate strong password
        password = self.generate_strong_password()
        print(f"   🔒 Generated secure password")
        
        # Ensure network exists
        network = self.ensure_network_exists()
        
        # Stop and remove existing container
        self.stop_and_remove_container(self.POSTGRES_CONTAINER_NAME)
        
        try:
            # Start PostgreSQL container
            print(f"   🚀 Starting PostgreSQL container...")
            container = self.docker_client.containers.run(
                self.config.postgres_image,
                name=self.POSTGRES_CONTAINER_NAME,
                environment={
                    "POSTGRES_DB": database_name,
                    "POSTGRES_USER": username,
                    "POSTGRES_PASSWORD": password
                },
                ports={
                    f"{self.config.postgres_port}/tcp": self.config.postgres_port
                },
                network=self.NETWORK_NAME,
                detach=True,
                remove=False
            )
            
            print(f"   ✅ PostgreSQL container started: {container.short_id}")
            
            # Wait for database to be ready
            connection_string = (
                f"postgresql+asyncpg://{username}:{password}@localhost:"
                f"{self.config.postgres_port}/{database_name}"
            )
            
            if self._wait_for_postgres(
                host="localhost",
                port=self.config.postgres_port,
                database=database_name,
                username=username,
                password=password
            ):
                print(f"   ✅ PostgreSQL is ready and accepting connections")
                
                return {
                    "success": True,
                    "container_name": self.POSTGRES_CONTAINER_NAME,
                    "container_id": container.short_id,
                    "host": "localhost",
                    "internal_host": self.POSTGRES_CONTAINER_NAME,  # For container-to-container
                    "port": self.config.postgres_port,
                    "database": database_name,
                    "username": username,
                    "password": password,
                    "connection_string": connection_string,
                    "internal_connection_string": (
                        f"postgresql://{username}:{password}@{self.POSTGRES_CONTAINER_NAME}:"
                        f"{self.config.postgres_port}/{database_name}"
                    )
                }
            else:
                return {
                    "success": False,
                    "error": "PostgreSQL container started but connection validation failed",
                    "container_name": self.POSTGRES_CONTAINER_NAME
                }
                
        except APIError as e:
            error_msg = f"Docker API error: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def initialize_mongodb(
        self,
        database_name: str = "app_db",
        username: str = "app_user"
    ) -> Dict[str, Any]:
        """
        Initialize MongoDB database in Docker container.
        
        Steps:
        1. Generate strong random password
        2. Ensure Docker network exists
        3. Stop and remove existing container (if any)
        4. Start new MongoDB container
        5. Wait for database to be ready
        6. Validate connection
        
        Args:
            database_name: Name of database to create
            username: Username for database access
            
        Returns:
            Dictionary with connection configuration:
            {
                "success": bool,
                "container_name": str,
                "host": str,
                "port": int,
                "database": str,
                "username": str,
                "password": str,
                "connection_string": str
            }
            
        **Validates: Requirements 6.2, 6.5, 12.4**
        """
        print(f"\n🍃 Initializing MongoDB database...")
        
        # Generate strong password
        password = self.generate_strong_password()
        print(f"   🔒 Generated secure password")
        
        # Ensure network exists
        network = self.ensure_network_exists()
        
        # Stop and remove existing container
        self.stop_and_remove_container(self.MONGO_CONTAINER_NAME)
        
        try:
            # Start MongoDB container
            print(f"   🚀 Starting MongoDB container...")
            container = self.docker_client.containers.run(
                self.config.mongo_image,
                name=self.MONGO_CONTAINER_NAME,
                environment={
                    "MONGO_INITDB_ROOT_USERNAME": username,
                    "MONGO_INITDB_ROOT_PASSWORD": password,
                    "MONGO_INITDB_DATABASE": database_name
                },
                ports={
                    f"{self.config.mongo_port}/tcp": self.config.mongo_port
                },
                network=self.NETWORK_NAME,
                detach=True,
                remove=False
            )
            
            print(f"   ✅ MongoDB container started: {container.short_id}")
            
            # Wait for database to be ready
            # URL-encode username and password for MongoDB connection string
            encoded_username = quote_plus(username)
            encoded_password = quote_plus(password)
            
            connection_string = (
                f"mongodb://{encoded_username}:{encoded_password}@localhost:"
                f"{self.config.mongo_port}/{database_name}?authSource=admin"
            )
            
            if self._wait_for_mongodb(
                host="localhost",
                port=self.config.mongo_port,
                username=username,
                password=password
            ):
                print(f"   ✅ MongoDB is ready and accepting connections")
                
                return {
                    "success": True,
                    "container_name": self.MONGO_CONTAINER_NAME,
                    "container_id": container.short_id,
                    "host": "localhost",
                    "internal_host": self.MONGO_CONTAINER_NAME,  # For container-to-container
                    "port": self.config.mongo_port,
                    "database": database_name,
                    "username": username,
                    "password": password,
                    "connection_string": connection_string,
                    "internal_connection_string": (
                        f"mongodb://{encoded_username}:{encoded_password}@{self.MONGO_CONTAINER_NAME}:"
                        f"{self.config.mongo_port}/{database_name}?authSource=admin"
                    )
                }
            else:
                return {
                    "success": False,
                    "error": "MongoDB container started but connection validation failed",
                    "container_name": self.MONGO_CONTAINER_NAME
                }
                
        except APIError as e:
            error_msg = f"Docker API error: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def _wait_for_postgres(
        self,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str
    ) -> bool:
        """
        Wait for PostgreSQL to be ready and validate connection.
        
        Implements:
        - Simple SELECT 1 query for connection validation
        - Retry loop with configurable interval (default: 2 seconds)
        - Timeout handling (default: 30 seconds)
        - Detailed error reporting for connection failures
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: Database password
            
        Returns:
            True if connection successful, False otherwise
            
        **Validates: Requirements 6.4, 6.6**
        """
        print(f"   ⏳ Waiting for PostgreSQL to be ready...")
        print(f"      Connection: {username}@{host}:{port}/{database}")
        print(f"      Timeout: {self.CONNECTION_TIMEOUT}s, Retry interval: {self.CONNECTION_RETRY_INTERVAL}s")
        
        start_time = time.time()
        attempt_count = 0
        last_error = None
        error_type = None
        
        while time.time() - start_time < self.CONNECTION_TIMEOUT:
            attempt_count += 1
            elapsed = time.time() - start_time
            
            try:
                # Attempt connection with psycopg2
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=5
                )
                
                # Test connection with simple SELECT 1 query
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                
                # Verify query returned expected result
                if result and result[0] == 1:
                    print(f"   ✅ PostgreSQL connection validated (attempt {attempt_count}, elapsed {elapsed:.1f}s)")
                    return True
                else:
                    print(f"   ⚠️  Unexpected query result: {result}")
                    return False
                
            except psycopg2.OperationalError as e:
                # Transient connection errors - database may still be starting
                last_error = str(e)
                error_type = "OperationalError"
                
                # Check for specific error conditions
                if "password authentication failed" in last_error:
                    # Fatal error - wrong credentials, don't retry
                    print(f"\n   ❌ PostgreSQL Authentication Failed")
                    print(f"      Error: Password authentication failed for user '{username}'")
                    print(f"      Troubleshooting:")
                    print(f"        - Verify credentials are correct")
                    print(f"        - Check if user '{username}' exists in the database")
                    print(f"        - Ensure POSTGRES_USER and POSTGRES_PASSWORD match")
                    return False
                
                elif "database" in last_error and "does not exist" in last_error:
                    # Fatal error - database doesn't exist
                    print(f"\n   ❌ PostgreSQL Database Not Found")
                    print(f"      Error: Database '{database}' does not exist")
                    print(f"      Troubleshooting:")
                    print(f"        - Verify POSTGRES_DB environment variable is set correctly")
                    print(f"        - Check container logs: docker logs {self.POSTGRES_CONTAINER_NAME}")
                    return False
                
                # Transient error - retry
                if attempt_count % 5 == 0:  # Log every 5 attempts to avoid spam
                    print(f"      Attempt {attempt_count} failed (elapsed {elapsed:.1f}s), retrying...")
                
                time.sleep(self.CONNECTION_RETRY_INTERVAL)
                
            except psycopg2.Error as e:
                # Other psycopg2 errors (likely fatal)
                last_error = str(e)
                error_type = type(e).__name__
                print(f"\n   ❌ PostgreSQL Connection Error ({error_type})")
                print(f"      Error: {last_error}")
                print(f"      Connection string format: postgresql://{username}:***@{host}:{port}/{database}")
                return False
                
            except Exception as e:
                # Unexpected errors
                last_error = str(e)
                error_type = type(e).__name__
                print(f"\n   ❌ Unexpected Error ({error_type})")
                print(f"      Error: {last_error}")
                print(f"      Troubleshooting:")
                print(f"        - Check if PostgreSQL container is running: docker ps")
                print(f"        - Check container logs: docker logs {self.POSTGRES_CONTAINER_NAME}")
                print(f"        - Verify port {port} is not in use by another service")
                return False
        
        # Timeout reached
        elapsed = time.time() - start_time
        print(f"\n   ❌ PostgreSQL Connection Timeout")
        print(f"      Timeout: {self.CONNECTION_TIMEOUT}s (elapsed: {elapsed:.1f}s)")
        print(f"      Attempts: {attempt_count}")
        print(f"      Connection: postgresql://{username}:***@{host}:{port}/{database}")
        
        if last_error:
            print(f"      Last Error ({error_type}): {last_error}")
        
        print(f"      Troubleshooting:")
        print(f"        - Container may be taking longer to start than expected")
        print(f"        - Check container status: docker ps -a | grep {self.POSTGRES_CONTAINER_NAME}")
        print(f"        - Check container logs: docker logs {self.POSTGRES_CONTAINER_NAME}")
        print(f"        - Verify Docker has sufficient resources")
        print(f"        - Try increasing CONNECTION_TIMEOUT (current: {self.CONNECTION_TIMEOUT}s)")
        
        return False
    
    def _wait_for_mongodb(
        self,
        host: str,
        port: int,
        username: str,
        password: str
    ) -> bool:
        """
        Wait for MongoDB to be ready and validate connection.
        
        Implements:
        - server_info() command for connection validation
        - Retry loop with configurable interval (default: 2 seconds)
        - Timeout handling (default: 30 seconds)
        - Detailed error reporting for connection failures
        
        Args:
            host: Database host
            port: Database port
            username: Database username
            password: Database password
            
        Returns:
            True if connection successful, False otherwise
            
        **Validates: Requirements 6.4, 6.6**
        """
        print(f"   ⏳ Waiting for MongoDB to be ready...")
        print(f"      Connection: {username}@{host}:{port}")
        print(f"      Timeout: {self.CONNECTION_TIMEOUT}s, Retry interval: {self.CONNECTION_RETRY_INTERVAL}s")
        
        start_time = time.time()
        attempt_count = 0
        last_error = None
        error_type = None
        
        # URL-encode credentials
        encoded_username = quote_plus(username)
        encoded_password = quote_plus(password)
        
        while time.time() - start_time < self.CONNECTION_TIMEOUT:
            attempt_count += 1
            elapsed = time.time() - start_time
            
            try:
                connection_string = (
                    f"mongodb://{encoded_username}:{encoded_password}@{host}:{port}/"
                    f"?authSource=admin&serverSelectionTimeoutMS=5000"
                )
                
                client = MongoClient(connection_string)
                
                # Test connection with server_info() command
                # This retrieves server version and build information
                server_info = client.server_info()
                
                # Also test with admin ping command for additional validation
                admin_db = client.admin
                admin_db.command('ping')
                
                client.close()
                
                mongo_version = server_info.get('version', 'unknown')
                print(f"   ✅ MongoDB connection validated (attempt {attempt_count}, elapsed {elapsed:.1f}s)")
                print(f"      MongoDB version: {mongo_version}")
                return True
                
            except Exception as e:
                last_error = str(e)
                error_type = type(e).__name__
                
                # Check for specific error patterns
                if "Authentication failed" in last_error or "auth failed" in last_error:
                    # Fatal error - wrong credentials
                    print(f"\n   ❌ MongoDB Authentication Failed")
                    print(f"      Error: {last_error}")
                    print(f"      Troubleshooting:")
                    print(f"        - Verify username '{username}' and password are correct")
                    print(f"        - Check MONGO_INITDB_ROOT_USERNAME and MONGO_INITDB_ROOT_PASSWORD")
                    print(f"        - Ensure authSource=admin is correct for root user")
                    print(f"        - Check container logs: docker logs {self.MONGO_CONTAINER_NAME}")
                    return False
                
                elif "Timeout" in error_type or "timeout" in last_error.lower():
                    # Transient timeout - MongoDB may still be initializing
                    if attempt_count % 5 == 0:
                        print(f"      Attempt {attempt_count} timed out (elapsed {elapsed:.1f}s), retrying...")
                
                elif "Connection refused" in last_error or "No connection" in last_error:
                    # MongoDB service not yet accepting connections
                    if attempt_count % 5 == 0:
                        print(f"      Attempt {attempt_count} connection refused (elapsed {elapsed:.1f}s), retrying...")
                
                else:
                    # Other errors - log periodically
                    if attempt_count % 5 == 0:
                        print(f"      Attempt {attempt_count} failed: {error_type} (elapsed {elapsed:.1f}s)")
                
                time.sleep(self.CONNECTION_RETRY_INTERVAL)
        
        # Timeout reached
        elapsed = time.time() - start_time
        print(f"\n   ❌ MongoDB Connection Timeout")
        print(f"      Timeout: {self.CONNECTION_TIMEOUT}s (elapsed: {elapsed:.1f}s)")
        print(f"      Attempts: {attempt_count}")
        print(f"      Connection: mongodb://{username}:***@{host}:{port}/?authSource=admin")
        
        if last_error:
            print(f"      Last Error ({error_type}): {last_error}")
        
        print(f"      Troubleshooting:")
        print(f"        - Container may be taking longer to start than expected")
        print(f"        - Check container status: docker ps -a | grep {self.MONGO_CONTAINER_NAME}")
        print(f"        - Check container logs: docker logs {self.MONGO_CONTAINER_NAME}")
        print(f"        - Verify Docker has sufficient resources")
        print(f"        - Verify port {port} is not in use by another service")
        print(f"        - Try increasing CONNECTION_TIMEOUT (current: {self.CONNECTION_TIMEOUT}s)")
        
        return False
    
    def generate_migration_script(
        self,
        database_type: str,
        schema_definition: str,
        output_dir: str = "./backend"
    ) -> Dict[str, Any]:
        """
        Generate database schema migration script.
        
        Args:
            database_type: "postgresql" or "mongodb"
            schema_definition: Schema definition (SQL or MongoDB schema)
            output_dir: Directory to save migration scripts
            
        Returns:
            Dictionary with:
            {
                "success": bool,
                "script_path": str,
                "script_content": str
            }
            
        **Validates: Requirement 6.3**
        """
        print(f"\n📝 Generating {database_type} migration script...")
        
        output_path = Path(output_dir)
        migrations_dir = output_path / "migrations"
        migrations_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        
        if database_type == "postgresql":
            script_name = f"{timestamp}_init_schema.sql"
            script_path = migrations_dir / script_name
            
            # Add migration metadata
            script_content = f"""-- Migration: {timestamp}_init_schema
-- Created: {time.strftime('%Y-%m-%d %H:%M:%S')}
-- Description: Initial schema setup

{schema_definition}
"""
            
        elif database_type == "mongodb":
            script_name = f"{timestamp}_init_schema.py"
            script_path = migrations_dir / script_name
            
            # Create Python migration script
            script_content = f'''"""
Migration: {timestamp}_init_schema
Created: {time.strftime('%Y-%m-%d %H:%M:%S')}
Description: Initial MongoDB schema setup
"""

from pymongo import MongoClient
from typing import Dict, Any


def up(db_connection_string: str) -> None:
    """Apply migration."""
    client = MongoClient(db_connection_string)
    db = client.get_default_database()
    
    # Schema definition
{schema_definition}
    
    client.close()


def down(db_connection_string: str) -> None:
    """Rollback migration."""
    client = MongoClient(db_connection_string)
    db = client.get_default_database()
    
    # Rollback logic here
    pass
    
    client.close()
'''
        else:
            return {
                "success": False,
                "error": f"Unsupported database type: {database_type}"
            }
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            print(f"   ✅ Migration script created: {script_path}")
            
            return {
                "success": True,
                "script_path": str(script_path),
                "script_content": script_content
            }
            
        except Exception as e:
            error_msg = f"Failed to write migration script: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def generate_env_file(
        self,
        postgres_config: Optional[Dict[str, Any]] = None,
        mongo_config: Optional[Dict[str, Any]] = None,
        output_dir: str = "./backend"
    ) -> Dict[str, Any]:
        """
        Generate .env file with database configuration.
        
        NEVER hardcodes credentials - uses dynamically generated values.
        
        Args:
            postgres_config: PostgreSQL configuration dictionary
            mongo_config: MongoDB configuration dictionary
            output_dir: Directory to save .env file
            
        Returns:
            Dictionary with:
            {
                "success": bool,
                "env_path": str,
                "env_content": str
            }
            
        **Validates: Requirement 14.3**
        """
        print(f"\n📄 Generating .env configuration file...")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        env_path = output_path / ".env"
        
        env_lines = [
            "# Database Configuration",
            "# Generated by Database Agent",
            f"# Created: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        if postgres_config and postgres_config.get("success"):
            env_lines.extend([
                "# PostgreSQL Configuration",
                f"POSTGRES_HOST={postgres_config['host']}",
                f"POSTGRES_PORT={postgres_config['port']}",
                f"POSTGRES_DB={postgres_config['database']}",
                f"POSTGRES_USER={postgres_config['username']}",
                f"POSTGRES_PASSWORD={postgres_config['password']}",
                f"DATABASE_URL={postgres_config['connection_string']}",
                ""
            ])
        
        if mongo_config and mongo_config.get("success"):
            env_lines.extend([
                "# MongoDB Configuration",
                f"MONGO_HOST={mongo_config['host']}",
                f"MONGO_PORT={mongo_config['port']}",
                f"MONGO_DB={mongo_config['database']}",
                f"MONGO_USER={mongo_config['username']}",
                f"MONGO_PASSWORD={mongo_config['password']}",
                f"MONGO_URL={mongo_config['connection_string']}",
                ""
            ])
        
        # Add application configuration
        env_lines.extend([
            "# Application Configuration",
            "APP_ENV=development",
            "DEBUG=True",
            "LOG_LEVEL=INFO",
            ""
        ])
        
        env_content = "\n".join(env_lines)
        
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            print(f"   ✅ .env file created: {env_path}")
            print(f"   🔒 Credentials securely stored (never hardcoded)")
            
            return {
                "success": True,
                "env_path": str(env_path),
                "env_content": env_content
            }
            
        except Exception as e:
            error_msg = f"Failed to write .env file: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def execute_task(
        self,
        task_description: str,
        database_types: Optional[List[str]] = None,
        database_name: str = "app_db",
        username: str = "app_user"
    ) -> Dict[str, Any]:
        """
        Execute database initialization task.
        
        This is the main entry point that:
        1. Initializes requested databases (PostgreSQL, MongoDB, or both)
        2. Validates all connections
        3. Generates .env configuration file
        4. Returns complete database configuration
        
        Args:
            task_description: Task description
            database_types: List of databases to initialize ["postgresql", "mongodb"]
            database_name: Name of database to create
            username: Database username
            
        Returns:
            Dictionary with task results:
            {
                "success": bool,
                "postgres_config": dict (if PostgreSQL requested),
                "mongo_config": dict (if MongoDB requested),
                "env_file": str,
                "network": str,
                "error": str (if failed)
            }
            
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
        """
        print(f"\n🗄️  Database Agent: Starting task execution")
        print(f"   Task: {task_description[:100]}...")
        
        # Default to both databases if not specified
        if database_types is None:
            database_types = ["postgresql", "mongodb"]
        
        result = {
            "success": True,
            "network": self.NETWORK_NAME,
            "database_types": database_types
        }
        
        # Ensure Docker network exists
        try:
            self.ensure_network_exists()
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create Docker network: {str(e)}"
            }
        
        # Initialize PostgreSQL if requested
        if "postgresql" in database_types:
            postgres_config = self.initialize_postgres(
                database_name=database_name,
                username=username
            )
            result["postgres_config"] = postgres_config
            
            if not postgres_config.get("success"):
                result["success"] = False
                result["error"] = postgres_config.get("error", "PostgreSQL initialization failed")
                print(f"\n   ❌ PostgreSQL initialization failed")
                return result
        
        # Initialize MongoDB if requested
        if "mongodb" in database_types:
            mongo_config = self.initialize_mongodb(
                database_name=database_name,
                username=username
            )
            result["mongo_config"] = mongo_config
            
            if not mongo_config.get("success"):
                result["success"] = False
                result["error"] = mongo_config.get("error", "MongoDB initialization failed")
                print(f"\n   ❌ MongoDB initialization failed")
                return result
        
        # Generate .env file
        env_result = self.generate_env_file(
            postgres_config=result.get("postgres_config"),
            mongo_config=result.get("mongo_config"),
            output_dir=self.config.backend_output_dir
        )
        
        if env_result.get("success"):
            result["env_file"] = env_result["env_path"]
        else:
            # Not critical - continue even if .env generation fails
            result["env_file_error"] = env_result.get("error")
        
        if result["success"]:
            print(f"\n   ✅ Database initialization completed successfully!")
            print(f"   🌐 Network: {result['network']}")
            
            if "postgres_config" in result:
                pg = result["postgres_config"]
                print(f"   🐘 PostgreSQL: {pg['container_name']} (port {pg['port']})")
            
            if "mongo_config" in result:
                mg = result["mongo_config"]
                print(f"   🍃 MongoDB: {mg['container_name']} (port {mg['port']})")
            
            if "env_file" in result:
                print(f"   📄 Configuration: {result['env_file']}")
        
        return result
    
    def cleanup(self) -> None:
        """
        Cleanup resources and close Docker client.
        """
        if hasattr(self, 'docker_client'):
            self.docker_client.close()
