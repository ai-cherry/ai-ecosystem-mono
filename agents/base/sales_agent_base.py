"""
BaseSalesAgent & concrete Sales-Agent implementations.

This module defines the abstract BaseSalesAgent class and four concrete
implementations for different sales-related tasks:
1. LeadResearchAgent
2. MarketingOutreachAgent 
3. SalesCoachAgent
4. CollectionsScoringAgent

Design goals:
1. Built on Agno for core reasoning loops (fast + tiny mem footprint)
2. Uses LangChain only for external tool wrappers
3. Pulls context from MemoryManager
4. Exposes uniform async API: `await agent.run(task: AgentTask) -> AgentResult`
5. Pluggable into Temporal workflows
"""

import abc
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict, Union

# Agno imports for core reasoning (fast + tiny memory footprint)
from agno.agent import AgnoAgent, AgnoConfig
from agno.utils import AgnoTool

# LangChain tool imports (only used for external integrations)
from langchain.tools import BaseTool
from langchain.agents import Tool
from langchain.utilities import GoogleSearchAPIWrapper
from langchain.utilities.sql_database import SQLDatabase

# Local imports
from shared.memory.memory_manager import MemoryManager, MemoryItem


class AgentTask(TypedDict):
    """Task structure passed to agent for execution."""
    id: str
    task_type: str  # e.g., "lead_research", "outreach", "coaching", "collections"
    description: str
    parameters: Dict[str, Any]
    client_id: str
    priority: int
    deadline: Optional[str]  # ISO format datetime


class AgentStep(TypedDict):
    """Individual step in an agent's execution plan."""
    step_id: int
    tool_name: str
    input_args: Dict[str, Any]
    expected_output: str
    status: str  # "pending", "in_progress", "completed", "failed"
    output: Optional[Any]
    error: Optional[str]


class AgentPlan(TypedDict):
    """Plan structure returned from agent planning phase."""
    task_id: str
    thought_process: str
    steps: List[AgentStep]
    estimated_duration_seconds: int


class AgentResult(TypedDict):
    """Final result structure returned from agent execution."""
    task_id: str
    status: str  # "success", "partial_success", "failure"
    summary: str
    details: str
    steps_executed: List[AgentStep]
    tool_outputs: Dict[str, Any]
    memory_items_created: List[str]  # IDs of items stored in memory
    error: Optional[str]
    execution_time_seconds: float


class BaseSalesAgent(abc.ABC):
    """
    Abstract base class for all sales-oriented agents.
    
    Provides a uniform interface with methods for context gathering,
    planning, acting, and running complete tasks. Concrete subclasses
    must implement the plan and act abstract methods.
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        memory: MemoryManager,
        tools: Dict[str, Callable] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a sales agent.
        
        Args:
            name: Unique identifier for this agent
            role: Human-readable role description
            description: Detailed description of the agent's capabilities
            memory: MemoryManager instance for context retrieval/storage
            tools: Dict mapping tool names to callable functions
            config: Additional configuration parameters
        """
        self.name = name
        self.role = role
        self.description = description
        self.memory = memory
        self.tools = tools or {}
        self.config = config or {}
        
        # Initialize Agno agent for reasoning
        self.agno_config = AgnoConfig(
            model="gpt-4-turbo",
            temperature=0.2,
            **self.config.get("agno_config", {})
        )
        self.agno_agent = AgnoAgent(self.agno_config)
        
        # Wrap tools for Agno compatibility
        self.agno_tools = {}
        for tool_name, tool_fn in self.tools.items():
            # Handle both LangChain tools and regular callables
            if isinstance(tool_fn, BaseTool) or isinstance(tool_fn, Tool):
                # Convert LangChain tool to Agno tool
                self.agno_tools[tool_name] = AgnoTool(
                    name=tool_name,
                    description=tool_fn.description,
                    fn=tool_fn._run
                )
            else:
                # Regular callable
                self.agno_tools[tool_name] = AgnoTool(
                    name=tool_name,
                    description=f"Tool for {tool_name}",
                    fn=tool_fn
                )
        
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.info(f"Initialized {self.name} ({self.role})")
    
    async def gather_context(self, task: AgentTask) -> List[MemoryItem]:
        """
        Retrieve relevant context from memory based on the task.
        
        Args:
            task: The task to gather context for
            
        Returns:
            List of memory items providing context for the task
        """
        self.logger.info(f"Gathering context for task {task['id']}")
        
        # Extract key terms from task description
        query = f"{task['description']} {' '.join(str(v) for v in task['parameters'].values())}"
        
        # Retrieve from memory manager
        context_items = await self.memory.retrieve(
            query=query,
            client_id=task["client_id"],
            top_k=10  # Adjust based on task complexity
        )
        
        self.logger.info(f"Retrieved {len(context_items)} context items for task {task['id']}")
        return context_items
    
    @abc.abstractmethod
    async def plan(self, task: AgentTask, context: List[MemoryItem]) -> AgentPlan:
        """
        Create a multi-step plan based on the task and context.
        
        Args:
            task: The task to plan for
            context: Relevant memory items for context
            
        Returns:
            A structured plan with steps to execute
        """
        pass
    
    @abc.abstractmethod
    async def act(self, plan: AgentPlan) -> AgentResult:
        """
        Execute the plan by running tools in sequence.
        
        Args:
            plan: The plan to execute
            
        Returns:
            Results from plan execution
        """
        pass
    
    async def run(self, task: AgentTask) -> AgentResult:
        """
        Complete end-to-end task execution (gather → plan → act → store).
        
        This is the main entry point for agent execution. It:
        1. Gathers context from memory
        2. Creates a plan based on the task and context
        3. Executes the plan
        4. Stores results back to memory
        
        Args:
            task: The task to execute
            
        Returns:
            Results from task execution
        """
        start_time = asyncio.get_event_loop().time()
        self.logger.info(f"Starting task {task['id']}: {task['description']}")
        
        try:
            # 1. Gather context from memory
            context = await self.gather_context(task)
            
            # 2. Plan based on task and context
            plan = await self.plan(task, context)
            
            # 3. Execute plan
            result = await self.act(plan)
            
            # 4. Store key results in memory
            memory_items = []
            if result["status"] in ["success", "partial_success"]:
                # Store overall result summary
                summary_id = await self.memory.store(
                    text=result["summary"],
                    metadata={
                        "task_id": task["id"],
                        "agent": self.name,
                        "client_id": task["client_id"],
                        "type": "task_result",
                        "status": result["status"]
                    }
                )
                memory_items.append(summary_id)
                
                # Store important tool outputs as separate memories
                for step in result["steps_executed"]:
                    if step["status"] == "completed" and step["output"]:
                        # Determine if this output should be stored
                        tool_name = step["tool_name"]
                        if tool_name in self.config.get("store_outputs_for_tools", []):
                            output_str = str(step["output"])
                            output_id = await self.memory.store(
                                text=output_str,
                                metadata={
                                    "task_id": task["id"],
                                    "agent": self.name,
                                    "client_id": task["client_id"],
                                    "type": "tool_output",
                                    "tool": tool_name,
                                    "step_id": step["step_id"]
                                }
                            )
                            memory_items.append(output_id)
            
            # Update result with memory items
            result["memory_items_created"] = memory_items
            
            # Calculate execution time
            end_time = asyncio.get_event_loop().time()
            result["execution_time_seconds"] = end_time - start_time
            
            self.logger.info(
                f"Completed task {task['id']} with status {result['status']} "
                f"in {result['execution_time_seconds']:.2f}s"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing task {task['id']}: {str(e)}", exc_info=True)
            
            # Calculate execution time
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            # Return error result
            return {
                "task_id": task["id"],
                "status": "failure",
                "summary": f"Error executing task: {str(e)}",
                "details": f"Exception: {repr(e)}",
                "steps_executed": [],
                "tool_outputs": {},
                "memory_items_created": [],
                "error": str(e),
                "execution_time_seconds": execution_time
            }
