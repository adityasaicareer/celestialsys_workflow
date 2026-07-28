"""
Planning Agent: Decomposes requirements into executable tasks.

The Planning Agent reads user requirements (text or markdown files),
analyzes them, and creates a structured execution plan with task
dependencies and agent assignments.
"""

import os
import json
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from ..models import ExecutionPlan, TaskDefinition
from ..config import get_config, get_llm


class PlanningAgent:
    """
    Planning Agent that decomposes requirements into executable tasks.
    
    This agent:
    1. Accepts requirements as text or markdown file paths
    2. Reads and parses markdown files when needed
    3. Analyzes requirements to identify features and components
    4. Creates a task dependency graph
    5. Assigns tasks to appropriate specialist agents
    6. Validates that all requirements are covered
    """
    
    AGENT_TYPES = [
        "planning",
        "supervisor",
        "backend",
        "frontend",
        "database",
        "testing",
        "deployment"
    ]
    
    def __init__(self):
        """Initialize the Planning Agent."""
        self.config = get_config()
        self.llm = get_llm()
        
        self.parser = PydanticOutputParser(pydantic_object=ExecutionPlan)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("human", "{requirements}")
        ])
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the Planning Agent."""
        return """You are a Planning Agent in a supervised workflow system that builds full-stack applications.

Your responsibilities:
1. Analyze user requirements thoroughly
2. Break down requirements into executable tasks
3. Create a task dependency graph (ensure no cycles - must be a DAG)
4. Assign each task to the appropriate specialist agent
5. Estimate task durations
6. Ensure all requirements are covered by at least one task

Available Specialist Agents:
- **backend**: Generates FastAPI Python code, database models, API endpoints
- **frontend**: Generates Next.js React code, UI components, responsive designs
- **database**: Initializes PostgreSQL and MongoDB in Docker, creates schemas
- **testing**: Generates and executes tests for backend and frontend
- **deployment**: Creates Docker configurations and deploys services

Task Assignment Guidelines:
- Database setup tasks should come first (many tasks depend on database)
- Backend tasks can start after database is ready
- Frontend tasks can run in parallel with backend (if APIs are defined)
- Testing tasks should come after code generation
- Deployment is the final step after all tests pass

Output Format:
Return a valid JSON object matching the ExecutionPlan schema:
{{
    "tasks": [
        {{
            "id": "task_1",
            "description": "Initialize PostgreSQL database in Docker",
            "agent": "database",
            "dependencies": [],
            "estimated_duration": "2 minutes",
            "status": "pending"
        }},
        {{
            "id": "task_2",
            "description": "Generate User model and authentication endpoints",
            "agent": "backend",
            "dependencies": ["task_1"],
            "estimated_duration": "5 minutes",
            "status": "pending"
        }}
    ],
    "dependency_graph": {{
        "task_1": [],
        "task_2": ["task_1"]
    }},
    "estimated_total_duration": "30 minutes",
    "required_agents": ["database", "backend", "frontend", "testing", "deployment"]
}}

CRITICAL RULES:
1. dependency_graph must be acyclic (no circular dependencies)
2. All task IDs must be unique
3. All dependencies must reference existing task IDs
4. Agent names must be one of: backend, frontend, database, testing, deployment
5. Return ONLY valid JSON, no additional text
"""
    
    def detect_input_type(self, user_input: str) -> tuple[str, str]:
        """
        Detect whether input is text or a file path.
        
        Args:
            user_input: User requirements (text or file path)
            
        Returns:
            Tuple of (input_type, content) where input_type is 'text' or 'file'
        """
        # Check if input looks like a file path
        if user_input.strip().endswith('.md') and os.path.isfile(user_input):
            return ('file', user_input)
        return ('text', user_input)
    
    def read_markdown_file(self, file_path: str) -> str:
        """
        Read and parse markdown file content.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            File content as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except FileNotFoundError:
            raise FileNotFoundError(f"Requirements file not found: {file_path}")
        except Exception as e:
            raise IOError(f"Error reading requirements file: {str(e)}")
    
    def create_execution_plan(self, user_requirements: str) -> ExecutionPlan:
        """
        Create execution plan from user requirements.
        
        Args:
            user_requirements: Requirements as text or file path
            
        Returns:
            Structured execution plan with tasks and dependencies
            
        Raises:
            ValueError: If requirements are invalid or plan cannot be created
        """
        # Detect input type and get content
        input_type, input_value = self.detect_input_type(user_requirements)
        
        if input_type == 'file':
            requirements_text = self.read_markdown_file(input_value)
            print(f"📄 Loaded requirements from file: {input_value}")
        else:
            requirements_text = input_value
        
        # Generate execution plan using LLM
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({"requirements": requirements_text})
            
            # Parse the response
            # The LLM should return JSON, but we'll handle potential markdown wrapping
            # Handle case where response.content might be a list or string
            if isinstance(response.content, list):
                # If it's a list, join the items
                content = ''.join(str(item) for item in response.content)
            else:
                content = str(response.content)
            
            content = content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                lines = content.split('\n')
                lines = [l for l in lines if not l.strip().startswith('```')]
                content = '\n'.join(lines)
            
            # Parse JSON
            plan_dict = json.loads(content)
            
            # Create ExecutionPlan object
            execution_plan = ExecutionPlan(**plan_dict)
            
            # Validate the plan
            self.validate_plan(execution_plan)
            
            return execution_plan
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse execution plan JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to create execution plan: {str(e)}")
    
    def validate_plan(self, plan: ExecutionPlan) -> None:
        """
        Validate the execution plan.
        
        Args:
            plan: Execution plan to validate
            
        Raises:
            ValueError: If plan is invalid
        """
        # Check that we have tasks
        if not plan.tasks:
            raise ValueError("Execution plan must contain at least one task")
        
        # Check for unique task IDs
        task_ids = [task.id for task in plan.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task IDs must be unique")
        
        # Check that all dependencies reference valid tasks
        for task in plan.tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    raise ValueError(
                        f"Task {task.id} has invalid dependency: {dep_id}"
                    )
        
        # Check for cycles in dependency graph (DAG validation)
        if self._has_cycle(plan):
            raise ValueError("Dependency graph contains cycles (must be a DAG)")
        
        # Check that all agents are valid
        for task in plan.tasks:
            if task.agent not in self.AGENT_TYPES:
                raise ValueError(
                    f"Task {task.id} has invalid agent: {task.agent}. "
                    f"Must be one of {self.AGENT_TYPES}"
                )
    
    def _has_cycle(self, plan: ExecutionPlan) -> bool:
        """
        Check if dependency graph has cycles using DFS.
        
        Args:
            plan: Execution plan with dependency graph
            
        Returns:
            True if cycle detected, False otherwise
        """
        # Build adjacency list
        graph = {task.id: task.dependencies for task in plan.tasks}
        
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            """DFS helper to detect cycles."""
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        # Check each node
        for node in graph:
            if node not in visited:
                if dfs(node):
                    return True
        
        return False
