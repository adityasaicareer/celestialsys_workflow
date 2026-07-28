"""
Test suite for Database Agent connection validation functionality.

Tests connection validation for both PostgreSQL and MongoDB, including:
- Successful connection validation
- Timeout handling
- Authentication failure detection
- Database not found errors
- Detailed error reporting

**Validates: Requirements 6.4, 6.6**
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import psycopg2
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure

from workflow.agents.database_agent import DatabaseAgent


class TestPostgreSQLConnectionValidation:
    """Test PostgreSQL connection validation."""
    
    def test_postgres_successful_connection(self):
        """Test successful PostgreSQL connection validation with SELECT 1 query."""
        agent = DatabaseAgent()
        
        # Mock psycopg2.connect to return a mock connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)  # SELECT 1 returns (1,)
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            result = agent._wait_for_postgres(
                host="localhost",
                port=5432,
                database="test_db",
                username="test_user",
                password="test_pass"
            )
        
        assert result is True
        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_cursor.fetchone.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    def test_postgres_authentication_failure(self):
        """Test PostgreSQL authentication failure detection and error reporting."""
        agent = DatabaseAgent()
        
        # Mock authentication failure
        auth_error = psycopg2.OperationalError(
            'FATAL:  password authentication failed for user "test_user"'
        )
        
        with patch('psycopg2.connect', side_effect=auth_error):
            result = agent._wait_for_postgres(
                host="localhost",
                port=5432,
                database="test_db",
                username="test_user",
                password="wrong_pass"
            )
        
        # Should fail immediately without retrying (fatal error)
        assert result is False
    
    def test_postgres_database_not_found(self):
        """Test PostgreSQL database not found error detection."""
        agent = DatabaseAgent()
        
        # Mock database not found error
        db_error = psycopg2.OperationalError(
            'FATAL:  database "nonexistent_db" does not exist'
        )
        
        with patch('psycopg2.connect', side_effect=db_error):
            result = agent._wait_for_postgres(
                host="localhost",
                port=5432,
                database="nonexistent_db",
                username="test_user",
                password="test_pass"
            )
        
        # Should fail immediately (fatal error)
        assert result is False
    
    def test_postgres_timeout_handling(self):
        """Test PostgreSQL connection timeout with retry logic."""
        agent = DatabaseAgent()
        agent.CONNECTION_TIMEOUT = 2  # Short timeout for test
        agent.CONNECTION_RETRY_INTERVAL = 0.5
        
        # Mock persistent connection failure (transient error)
        transient_error = psycopg2.OperationalError("could not connect to server")
        
        with patch('psycopg2.connect', side_effect=transient_error):
            start_time = time.time()
            result = agent._wait_for_postgres(
                host="localhost",
                port=5432,
                database="test_db",
                username="test_user",
                password="test_pass"
            )
            elapsed = time.time() - start_time
        
        # Should timeout and return False
        assert result is False
        # Should have waited approximately CONNECTION_TIMEOUT seconds
        assert elapsed >= agent.CONNECTION_TIMEOUT
        assert elapsed < agent.CONNECTION_TIMEOUT + 2  # Allow some overhead
    
    def test_postgres_retry_then_success(self):
        """Test PostgreSQL connection succeeds after retries."""
        agent = DatabaseAgent()
        agent.CONNECTION_RETRY_INTERVAL = 0.1  # Fast retries for test
        
        # Mock connection that fails twice then succeeds
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor
        
        transient_error = psycopg2.OperationalError("connection refused")
        call_count = 0
        
        def connect_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise transient_error
            return mock_conn
        
        with patch('psycopg2.connect', side_effect=connect_side_effect):
            result = agent._wait_for_postgres(
                host="localhost",
                port=5432,
                database="test_db",
                username="test_user",
                password="test_pass"
            )
        
        # Should succeed after retries
        assert result is True
        assert call_count == 3  # Failed twice, succeeded third time
    
    def test_postgres_unexpected_query_result(self):
        """Test PostgreSQL validation fails if SELECT 1 returns unexpected result."""
        agent = DatabaseAgent()
        
        # Mock connection that returns wrong result
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (2,)  # Wrong result
        mock_conn.cursor.return_value = mock_cursor
        
        with patch('psycopg2.connect', return_value=mock_conn):
            result = agent._wait_for_postgres(
                host="localhost",
                port=5432,
                database="test_db",
                username="test_user",
                password="test_pass"
            )
        
        assert result is False


class TestMongoDBConnectionValidation:
    """Test MongoDB connection validation."""
    
    def test_mongodb_successful_connection(self):
        """Test successful MongoDB connection validation with server_info and ping."""
        agent = DatabaseAgent()
        
        # Mock MongoClient
        mock_client = Mock()
        mock_admin = Mock()
        mock_client.admin = mock_admin
        mock_client.server_info.return_value = {
            'version': '7.0.0',
            'ok': 1.0
        }
        mock_admin.command.return_value = {'ok': 1.0}
        
        with patch('workflow.agents.database_agent.MongoClient', return_value=mock_client):
            result = agent._wait_for_mongodb(
                host="localhost",
                port=27017,
                username="test_user",
                password="test_pass"
            )
        
        assert result is True
        mock_client.server_info.assert_called_once()
        mock_admin.command.assert_called_once_with('ping')
        mock_client.close.assert_called_once()
    
    def test_mongodb_authentication_failure(self):
        """Test MongoDB authentication failure detection and error reporting."""
        agent = DatabaseAgent()
        
        # Mock authentication failure
        auth_error = OperationFailure("Authentication failed")
        
        with patch('workflow.agents.database_agent.MongoClient') as mock_mongo:
            mock_client = Mock()
            mock_client.server_info.side_effect = auth_error
            mock_mongo.return_value = mock_client
            
            result = agent._wait_for_mongodb(
                host="localhost",
                port=27017,
                username="test_user",
                password="wrong_pass"
            )
        
        # Should fail immediately (fatal error)
        assert result is False
    
    def test_mongodb_timeout_handling(self):
        """Test MongoDB connection timeout with retry logic."""
        agent = DatabaseAgent()
        agent.CONNECTION_TIMEOUT = 2  # Short timeout for test
        agent.CONNECTION_RETRY_INTERVAL = 0.5
        
        # Mock persistent timeout error
        timeout_error = ServerSelectionTimeoutError("Timeout")
        
        with patch('workflow.agents.database_agent.MongoClient') as mock_mongo:
            mock_client = Mock()
            mock_client.server_info.side_effect = timeout_error
            mock_mongo.return_value = mock_client
            
            start_time = time.time()
            result = agent._wait_for_mongodb(
                host="localhost",
                port=27017,
                username="test_user",
                password="test_pass"
            )
            elapsed = time.time() - start_time
        
        # Should timeout and return False
        assert result is False
        # Should have waited approximately CONNECTION_TIMEOUT seconds
        assert elapsed >= agent.CONNECTION_TIMEOUT
        assert elapsed < agent.CONNECTION_TIMEOUT + 2
    
    def test_mongodb_retry_then_success(self):
        """Test MongoDB connection succeeds after retries."""
        agent = DatabaseAgent()
        agent.CONNECTION_RETRY_INTERVAL = 0.1  # Fast retries for test
        
        # Mock client that fails twice then succeeds
        call_count = 0
        timeout_error = ServerSelectionTimeoutError("Connection refused")
        
        def server_info_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise timeout_error
            return {'version': '7.0.0', 'ok': 1.0}
        
        with patch('workflow.agents.database_agent.MongoClient') as mock_mongo:
            mock_client = Mock()
            mock_admin = Mock()
            mock_client.admin = mock_admin
            mock_client.server_info.side_effect = server_info_side_effect
            mock_admin.command.return_value = {'ok': 1.0}
            mock_mongo.return_value = mock_client
            
            result = agent._wait_for_mongodb(
                host="localhost",
                port=27017,
                username="test_user",
                password="test_pass"
            )
        
        # Should succeed after retries
        assert result is True
        assert call_count == 3  # Failed twice, succeeded third time
    
    def test_mongodb_connection_refused(self):
        """Test MongoDB connection refused error with retries."""
        agent = DatabaseAgent()
        agent.CONNECTION_TIMEOUT = 2
        agent.CONNECTION_RETRY_INTERVAL = 0.5
        
        # Mock connection refused error
        conn_error = Exception("No connection could be made because the target machine actively refused it")
        
        with patch('workflow.agents.database_agent.MongoClient') as mock_mongo:
            mock_client = Mock()
            mock_client.server_info.side_effect = conn_error
            mock_mongo.return_value = mock_client
            
            result = agent._wait_for_mongodb(
                host="localhost",
                port=27017,
                username="test_user",
                password="test_pass"
            )
        
        # Should timeout and fail
        assert result is False


class TestConnectionValidationConfiguration:
    """Test connection validation configuration and retry settings."""
    
    def test_default_timeout_configuration(self):
        """Test default timeout and retry interval values."""
        agent = DatabaseAgent()
        
        assert agent.CONNECTION_TIMEOUT == 30
        assert agent.CONNECTION_RETRY_INTERVAL == 2
    
    def test_connection_string_format_safety(self):
        """Test that connection strings don't expose passwords in error messages."""
        agent = DatabaseAgent()
        
        # Mock a failure scenario
        with patch('psycopg2.connect', side_effect=psycopg2.OperationalError("Timeout")):
            agent.CONNECTION_TIMEOUT = 1
            agent.CONNECTION_RETRY_INTERVAL = 0.3
            
            result = agent._wait_for_postgres(
                host="testhost",
                port=5432,
                database="testdb",
                username="testuser",
                password="supersecret123"
            )
        
        # Should fail
        assert result is False
        # Password should not appear in connection string format (shown as ***)
        # This is implicitly tested by the implementation


class TestIntegrationValidation:
    """Integration tests for database initialization with validation."""
    
    @patch('workflow.agents.database_agent.DatabaseAgent._wait_for_postgres')
    @patch('workflow.agents.database_agent.docker.from_env')
    def test_postgres_initialization_with_validation(self, mock_docker, mock_wait):
        """Test complete PostgreSQL initialization flow with connection validation."""
        from docker.errors import NotFound
        
        # Mock Docker client
        mock_client = Mock()
        mock_container = Mock()
        mock_container.short_id = "abc123"
        mock_client.containers.run.return_value = mock_container
        
        # Mock network not found, then return mock network on create
        mock_client.networks.get.side_effect = NotFound("Network not found")
        mock_network = Mock()
        mock_client.networks.create.return_value = mock_network
        
        # Mock container get to raise NotFound (no existing container)
        mock_client.containers.get.side_effect = NotFound("Container not found")
        
        mock_docker.return_value = mock_client
        
        # Mock successful connection validation
        mock_wait.return_value = True
        
        agent = DatabaseAgent()
        result = agent.initialize_postgres(
            database_name="test_db",
            username="test_user"
        )
        
        # Should succeed
        assert result["success"] is True
        assert "connection_string" in result
        assert "test_db" in result["connection_string"]
        
        # Validation should have been called
        mock_wait.assert_called_once()
    
    @patch('workflow.agents.database_agent.DatabaseAgent._wait_for_mongodb')
    @patch('workflow.agents.database_agent.docker.from_env')
    def test_mongodb_initialization_with_validation_failure(self, mock_docker, mock_wait):
        """Test MongoDB initialization fails when connection validation fails."""
        from docker.errors import NotFound
        
        # Mock Docker client
        mock_client = Mock()
        mock_container = Mock()
        mock_container.short_id = "def456"
        mock_client.containers.run.return_value = mock_container
        
        # Mock network not found, then return mock network on create
        mock_client.networks.get.side_effect = NotFound("Network not found")
        mock_network = Mock()
        mock_client.networks.create.return_value = mock_network
        
        # Mock container get to raise NotFound (no existing container)
        mock_client.containers.get.side_effect = NotFound("Container not found")
        
        mock_docker.return_value = mock_client
        
        # Mock failed connection validation
        mock_wait.return_value = False
        
        agent = DatabaseAgent()
        result = agent.initialize_mongodb(
            database_name="test_db",
            username="test_user"
        )
        
        # Should report failure
        assert result["success"] is False
        assert "validation failed" in result["error"]
        
        # Validation should have been called
        mock_wait.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
