"""
Test file to verify Task 13.1 completion: Testing Agent class creation.

This test verifies:
1. TestingAgent class can be imported
2. TestingAgent can be instantiated
3. TestingAgent has all required methods
4. TestGenerator and TestExecutor classes exist
"""

import pytest
from workflow.agents.testing_agent import TestingAgent, TestGenerator, TestExecutor


def test_testing_agent_import():
    """Test that TestingAgent can be imported."""
    assert TestingAgent is not None


def test_testing_agent_instantiation():
    """Test that TestingAgent can be instantiated."""
    agent = TestingAgent()
    assert agent is not None
    assert hasattr(agent, 'config')
    assert hasattr(agent, 'llm')
    assert hasattr(agent, 'generator')
    assert hasattr(agent, 'executor')


def test_testing_agent_has_required_methods():
    """Test that TestingAgent has all required methods."""
    agent = TestingAgent()
    
    # Backend test generation and execution
    assert hasattr(agent, 'generate_backend_tests')
    assert callable(agent.generate_backend_tests)
    
    assert hasattr(agent, 'execute_backend_tests')
    assert callable(agent.execute_backend_tests)
    
    # Frontend test generation and execution
    assert hasattr(agent, 'generate_frontend_tests')
    assert callable(agent.generate_frontend_tests)
    
    assert hasattr(agent, 'execute_frontend_tests')
    assert callable(agent.execute_frontend_tests)
    
    # Main task execution method
    assert hasattr(agent, 'execute_task')
    assert callable(agent.execute_task)


def test_test_generator_exists():
    """Test that TestGenerator class exists and has required methods."""
    agent = TestingAgent()
    generator = agent.generator
    
    assert generator is not None
    assert isinstance(generator, TestGenerator)
    
    # Backend test generation methods
    assert hasattr(generator, 'generate_backend_unit_tests')
    assert callable(generator.generate_backend_unit_tests)
    
    assert hasattr(generator, 'generate_backend_integration_tests')
    assert callable(generator.generate_backend_integration_tests)
    
    # Frontend test generation methods
    assert hasattr(generator, 'generate_frontend_component_tests')
    assert callable(generator.generate_frontend_component_tests)
    
    assert hasattr(generator, 'generate_frontend_integration_tests')
    assert callable(generator.generate_frontend_integration_tests)


def test_test_executor_exists():
    """Test that TestExecutor class exists and has required methods."""
    agent = TestingAgent()
    executor = agent.executor
    
    assert executor is not None
    assert isinstance(executor, TestExecutor)
    
    # Test execution methods
    assert hasattr(executor, 'run_pytest')
    assert callable(executor.run_pytest)
    
    assert hasattr(executor, 'run_jest_or_vitest')
    assert callable(executor.run_jest_or_vitest)


def test_coverage_thresholds_defined():
    """Test that coverage thresholds are defined."""
    assert hasattr(TestingAgent, 'MIN_BACKEND_COVERAGE')
    assert hasattr(TestingAgent, 'MIN_FRONTEND_COVERAGE')
    
    # Verify they are reasonable values
    assert TestingAgent.MIN_BACKEND_COVERAGE >= 0
    assert TestingAgent.MIN_BACKEND_COVERAGE <= 100
    assert TestingAgent.MIN_FRONTEND_COVERAGE >= 0
    assert TestingAgent.MIN_FRONTEND_COVERAGE <= 100


def test_testing_agent_from_workflow_agents():
    """Test that TestingAgent can be imported from workflow.agents."""
    from workflow.agents import TestingAgent as ImportedTestingAgent
    
    assert ImportedTestingAgent is not None
    agent = ImportedTestingAgent()
    assert agent is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
