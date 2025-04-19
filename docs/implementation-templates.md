# 📋 Implementation Templates for Missing Components

This document provides skeleton templates for implementing the missing components identified in the health check report. These templates can be used as a starting point for development, ensuring a consistent approach and adherence to project standards.

## 1. LangSmith Tracer Template (`shared/observability/langsmith_tracer.py`)

```python
"""
LangSmith tracer for monitoring and debugging LLM operations.

This module provides integration with LangSmith for tracing LLM calls,
enabling detailed monitoring, debugging, and cost tracking for AI operations.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Union

# Conditional import for LangSmith
try:
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

from shared.config import observability_settings

# Initialize logger
logger = logging.getLogger(__name__)


class LangSmithTracer:
    """Middleware for tracing LLM operations to LangSmith."""
    
    def __init__(self, client_id: Optional[str] = None):
        """
        Initialize the LangSmith tracer.
        
        Args:
            client_id: Optional client identifier for tenant tracking
        """
        self.enabled = observability_settings.LANGSMITH_ENABLED
        self.project = observability_settings.LANGSMITH_PROJECT
        self.client_id = client_id or str(uuid.uuid4())
        
        # Initialize LangSmith client if available and enabled
        self.client = None
        if self.enabled and LANGSMITH_AVAILABLE:
            try:
                self.client = Client(
                    api_key=observability_settings.LANGSMITH_API_KEY
                )
                logger.info(f"LangSmith tracing enabled for project: {self.project}")
            except Exception as e:
                logger.error(f"Error initializing LangSmith client: {str(e)}")
                self.enabled = False
    
    async def trace_llm_call(
        self, 
        prompt: str,
        response: str,
        model: str,
        tokens_used: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trace an LLM call to LangSmith.
        
        Args:
            prompt: The prompt sent to the model
            response: The response received from the model
            model: Model identifier (e.g., "gpt-4")
            tokens_used: Total tokens consumed
            metadata: Additional context about the call
            
        Returns:
            Dictionary with trace information
        """
        if not self.enabled:
            return {"enabled": False, "run_id": None}
        
        metadata = metadata or {}
        run_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Enrich metadata with standard fields
        enriched_metadata = {
            "client_id": self.client_id,
            "model": model,
            "tokens": tokens_used,
            "timestamp": start_time,
            "cost_estimate": self._estimate_cost(model, tokens_used),
            **metadata
        }
        
        try:
            if self.client:
                # Create run in LangSmith
                run = self.client.run_create(
                    name=metadata.get("operation_name", "llm_call"),
                    run_type="llm",
                    inputs={"prompt": prompt},
                    outputs={"response": response},
                    runtime={
                        "total_tokens": tokens_used,
                        "model": model
                    },
                    extra=enriched_metadata,
                    project_name=self.project,
                    run_id=run_id
                )
                
                logger.debug(f"LangSmith trace recorded: {run_id}")
                return {
                    "enabled": True,
                    "run_id": run_id,
                    "success": True
                }
            
        except Exception as e:
            logger.error(f"Error recording LangSmith trace: {str(e)}")
            
        return {
            "enabled": True,
            "run_id": run_id,
            "success": False,
            "error": "Failed to record trace"
        }
    
    async def start_trace(
        self,
        operation_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start a new trace for a complex operation (e.g., agent execution).
        
        Args:
            operation_name: Name of the operation being traced
            metadata: Additional context about the operation
            
        Returns:
            Dictionary with trace context for child spans
        """
        # Implementation needed
        pass
    
    async def end_trace(
        self,
        trace_context: Dict[str, Any],
        result: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        End a previously started trace.
        
        Args:
            trace_context: Context from start_trace
            result: Final result of the operation
            metadata: Additional context to add
        """
        # Implementation needed
        pass
    
    def _estimate_cost(self, model: str, tokens: int) -> float:
        """
        Estimate the cost of an LLM call based on model and tokens.
        
        Args:
            model: Model identifier
            tokens: Number of tokens used
            
        Returns:
            Estimated cost in USD
        """
        # Basic cost model - should be expanded with actual pricing
        cost_per_1k_tokens = {
            "gpt-3.5-turbo": 0.002,
            "gpt-4": 0.06,
            "gpt-4o": 0.01,
            "claude-3-opus": 0.15,
            "claude-3.5-sonnet": 0.03
        }
        
        base_cost = cost_per_1k_tokens.get(model, 0.01)  # Default if unknown
        return (tokens / 1000) * base_cost


# Singleton instance for global use
tracer = LangSmithTracer()


# Decorator for tracing function calls
def trace_llm(operation_name: str = None):
    """
    Decorator to trace LLM operations.
    
    Args:
        operation_name: Optional name for the operation
        
    Returns:
        Decorated function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not tracer.enabled:
                return await func(*args, **kwargs)
            
            # Extract prompt and context from args/kwargs
            # This would need to be adapted based on the function signature
            
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Extract necessary information from result
            # Construct metadata
            
            # Record trace
            await tracer.trace_llm_call(
                prompt="<extracted prompt>",
                response=str(result),
                model="<extracted model>",
                tokens_used=0,  # Would need to be extracted
                metadata={
                    "operation_name": operation_name or func.__name__,
                    "duration": duration,
                    # Additional metadata
                }
            )
            
            return result
        return wrapper
    return decorator
```

## 2. Agent Implementation Template (`agents/sales/lead_research.py`)

```python
"""
LeadResearchAgent implementation for researching sales leads.

This agent is responsible for gathering information about potential leads,
analyzing their profile, and providing insights to the sales team.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from agents.base.sales_agent_base import BaseSalesAgent
from shared.memory.memory_manager import MemoryManager
from shared.config import llm_settings

# Initialize logger
logger = logging.getLogger(__name__)


class LeadResearchAgent(BaseSalesAgent):
    """
    Agent that researches potential leads for sales opportunities.
    
    This agent gathers information from various sources, analyzes the data,
    and provides insights to help sales teams prioritize and approach leads
    effectively.
    """
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        agent_id: str = "lead_research",
        model: Optional[str] = None
    ):
        """
        Initialize the lead research agent.
        
        Args:
            memory_manager: Manager for agent memory
            agent_id: Unique identifier for this agent
            model: Optional override for the LLM model to use
        """
        super().__init__(
            memory_manager=memory_manager,
            agent_id=agent_id,
            agent_type="LeadResearchAgent",
            model=model or llm_settings.DEFAULT_MODEL
        )
    
    async def plan(self, context: Dict[str, Any]) -> str:
        """
        Create a research plan based on lead information.
        
        Args:
            context: Dictionary containing lead information and objectives
                - lead_name: Name of the lead person or company
                - industry: Industry of the lead
                - objectives: Research objectives (e.g., "find decision makers")
                
        Returns:
            A structured plan for researching the lead
        """
        # Validate required context
        lead_name = context.get("lead_name")
        if not lead_name:
            raise ValueError("Lead name is required in context")
        
        industry = context.get("industry", "unknown")
        objectives = context.get("objectives", ["general profile"])
        
        # System message for planning
        system_message = f"""
        You are a lead research specialist tasked with creating a detailed research plan for {lead_name} in the {industry} industry.
        Your objectives are: {', '.join(objectives)}.
        
        Create a step-by-step research plan that includes:
        1. Sources to check (LinkedIn, company website, news articles, etc.)
        2. Specific information to look for
        3. Analysis approach to distill insights
        
        Your plan should be structured, comprehensive, and feasible with public information.
        """
        
        # Generate plan using LLM
        plan_response = await self._generate_llm_response(
            system_message=system_message,
            user_message=f"Create a research plan for {lead_name}.",
            max_tokens=1000
        )
        
        # Store plan in memory for later use
        await self.memory_manager.store(
            collection=f"{self.agent_id}_plans",
            data={
                "lead_name": lead_name,
                "plan": plan_response,
                "timestamp": self._current_timestamp(),
                "objectives": objectives
            }
        )
        
        return plan_response
    
    async def act(self, plan: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a research plan and gather information about a lead.
        
        Args:
            plan: The research plan to execute
            context: Dictionary containing lead information and objectives
                - lead_name: Name of the lead person or company
                - industry: Industry of the lead
                - tools: Optional list of available research tools
                
        Returns:
            Dictionary with research findings and insights
        """
        lead_name = context.get("lead_name")
        if not lead_name:
            raise ValueError("Lead name is required in context")
        
        # Extract available tools from context
        tools = context.get("tools", ["web_search", "company_database"])
        
        # Initialize results structure
        results = {
            "lead_name": lead_name,
            "profile": {},
            "decision_makers": [],
            "insights": [],
            "recommendations": [],
            "sources": []
        }
        
        # Execute research tasks based on plan
        # This would integrate with actual research tools in a real implementation
        # The pseudocode below would be replaced with actual API calls or tool usage
        
        if "web_search" in tools:
            # Simulate web search
            web_results = await self._simulate_tool_use(
                "web_search", 
                {"query": f"{lead_name} company information"}
            )
            results["sources"].append({"type": "web_search", "results": web_results})
        
        if "company_database" in tools:
            # Simulate company database lookup
            company_info = await self._simulate_tool_use(
                "company_database", 
                {"company_name": lead_name}
            )
            results["sources"].append({"type": "company_database", "results": company_info})
        
        # Synthesize results using LLM
        system_message = f"""
        You are a lead research analyst tasked with synthesizing information about {lead_name}.
        Based on the collected data, provide:
        1. A company profile summary
        2. List of key decision makers
        3. Strategic insights relevant to sales
        4. Concrete recommendations for the sales team
        
        Be specific, factual, and concise.
        """
        
        synthesis_prompt = f"""
        Here is the information collected on {lead_name}:
        
        {results['sources']}
        
        Analyze this information and provide a structured synthesis.
        """
        
        synthesis = await self._generate_llm_response(
            system_message=system_message,
            user_message=synthesis_prompt,
            max_tokens=1500
        )
        
        # Parse synthesis to update results
        # This would use more structured parsing in a real implementation
        results["synthesis"] = synthesis
        
        # Store research results in memory
        await self.memory_manager.store(
            collection=f"{self.agent_id}_results",
            data=results
        )
        
        return results
    
    async def _simulate_tool_use(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate the use of external research tools (for testing/development).
        
        In a real implementation, this would be replaced by actual API calls
        or integrations with external data sources.
        
        Args:
            tool_name: Name of the tool to simulate
            params: Parameters for the tool
            
        Returns:
            Simulated results from the tool
        """
        # This is a placeholder that would be replaced by actual implementations
        if tool_name == "web_search":
            return {
                "title": f"Results for {params.get('query')}",
                "snippets": [
                    "Company was founded in 2010.",
                    "Expanded to international markets in 2018.",
                    "Current CEO is Jane Smith."
                ]
            }
        elif tool_name == "company_database":
            return {
                "company_name": params.get("company_name"),
                "industry": "Technology",
                "size": "500-1000 employees",
                "revenue": "$50M-$100M",
                "founded": 2010,
                "executives": [
                    {"name": "Jane Smith", "title": "CEO"},
                    {"name": "John Johnson", "title": "CTO"}
                ]
            }
        else:
            return {"error": "Unknown tool"}
```

## 3. Token Usage Tracker Template (`shared/cost/usage_tracker.py`)

```python
"""
Token usage tracker for managing LLM costs.

This module provides tools for tracking, limiting, and reporting on token usage
across the application, helping to control costs and ensure budget compliance.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import aioredis

from shared.config import llm_settings

# Initialize logger
logger = logging.getLogger(__name__)


class UsageTracker:
    """
    Tracks and limits token usage across LLM interactions.
    
    This class provides mechanisms for:
    - Recording token usage by model, agent, and operation
    - Enforcing budget limits at various levels
    - Generating usage reports
    - Implementing tiered throttling strategies
    """
    
    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        """
        Initialize the usage tracker.
        
        Args:
            redis_client: Optional Redis client for persistent tracking
        """
        self.redis_client = redis_client
        self.daily_limit = llm_settings.MAX_DAILY_TOKENS
        self.track_usage = llm_settings.TRACK_TOKEN_USAGE
        
        # In-memory tracking as backup/cache
        self.daily_usage = 0
        self.usage_by_model = defaultdict(int)
        self.usage_by_agent = defaultdict(int)
        self.daily_reset_time = self._get_next_reset_time()
    
    async def track_usage(
        self, 
        tokens: int, 
        model: str, 
        agent_id: str,
        operation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track token usage for an LLM call.
        
        Args:
            tokens: Number of tokens used
            model: Model identifier
            agent_id: ID of the agent making the call
            operation_id: Optional operation identifier for grouping
            metadata: Additional context about the usage
            
        Returns:
            Status information including remaining budget
        """
        if not self.track_usage:
            return {"tracked": False, "reason": "Tracking disabled"}
        
        metadata = metadata or {}
        timestamp = time.time()
        
        # Check if we need to reset daily counters
        current_time = datetime.now()
        if current_time >= self.daily_reset_time:
            await self._reset_daily_counters()
            self.daily_reset_time = self._get_next_reset_time()
        
        # Update in-memory counters
        self.daily_usage += tokens
        self.usage_by_model[model] += tokens
        self.usage_by_agent[agent_id] += tokens
        
        # Prepare usage record
        usage_record = {
            "tokens": tokens,
            "model": model,
            "agent_id": agent_id,
            "operation_id": operation_id,
            "timestamp": timestamp,
            "cost_estimate": self._estimate_cost(model, tokens),
            **metadata
        }
        
        # Store in Redis if available
        if self.redis_client:
            try:
                # Store the individual usage record
                record_key = f"token_usage:{current_time.strftime('%Y-%m-%d')}:{time.time()}"
                await self.redis_client.hmset(record_key, usage_record)
                await self.redis_client.expire(record_key, 60 * 60 * 24 * 7)  # Keep for 7 days
                
                # Update counters
                daily_key = f"daily_usage:{current_time.strftime('%Y-%m-%d')}"
                await self.redis_client.hincrby(daily_key, "total", tokens)
                await self.redis_client.hincrby(daily_key, f"model:{model}", tokens)
                await self.redis_client.hincrby(daily_key, f"agent:{agent_id}", tokens)
                await self.redis_client.expire(daily_key, 60 * 60 * 24 * 30)  # Keep for 30 days
                
                # Note: in a real implementation, we would use pipeline for efficiency
                
            except Exception as e:
                logger.error(f"Error storing token usage in Redis: {str(e)}")
        
        # Log the usage
        logger.info(
            f"Token usage: {tokens} tokens for model={model}, agent={agent_id}, "
            f"daily_total={self.daily_usage}/{self.daily_limit}"
        )
        
        # Return status
        remaining = max(0, self.daily_limit - self.daily_usage)
        usage_status = {
            "tracked": True,
            "tokens": tokens,
            "daily_usage": self.daily_usage,
            "daily_limit": self.daily_limit,
            "remaining": remaining,
            "percentage_used": (self.daily_usage / self.daily_limit) * 100 if self.daily_limit > 0 else 0
        }
        
        return usage_status
    
    async def check_budget(
        self, 
        agent_id: str, 
        estimated_tokens: int,
        model: str,
        operation_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a planned LLM call is within budget.
        
        Args:
            agent_id: ID of the agent making the call
            estimated_tokens: Estimated token usage
            model: Model to be used
            operation_id: Optional operation identifier
            
        Returns:
            Tuple of (allowed, budget_info)
        """
        if not self.track_usage:
            return True, {"budget_check": "disabled"}
        
        # Check if we need to reset daily counters
        current_time = datetime.now()
        if current_time >= self.daily_reset_time:
            await self._reset_daily_counters()
            self.daily_reset_time = self._get_next_reset_time()
        
        # Check budget
        remaining = max(0, self.daily_limit - self.daily_usage)
        allowed = estimated_tokens <= remaining
        
        # Get more accurate numbers from Redis if available
        if self.redis_client:
            try:
                daily_key = f"daily_usage:{current_time.strftime('%Y-%m-%d')}"
                redis_total = await self.redis_client.hget(daily_key, "total")
                if redis_total:
                    redis_total = int(redis_total)
                    remaining = max(0, self.daily_limit - redis_total)
                    allowed = estimated_tokens <= remaining
            except Exception as e:
                logger.error(f"Error checking budget in Redis: {str(e)}")
        
        # Prepare budget info
        budget_info = {
            "allowed": allowed,
            "estimated_tokens": estimated_tokens,
            "daily_usage": self.daily_usage,
            "daily_limit": self.daily_limit,
            "remaining": remaining,
            "percentage_used": (self.daily_usage / self.daily_limit) * 100 if self.daily_limit > 0 else 0
        }
        
        if not allowed:
            logger.warning(
                f"Budget exceeded for agent={agent_id}, estimated_tokens={estimated_tokens}, "
                f"remaining={remaining}"
            )
        
        return allowed, budget_info
    
    async def get_usage_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a usage report for a specific time period.
        
        Args:
            start_date: Optional start date (defaults to today)
            end_date: Optional end date (defaults to today)
            group_by: Optional grouping fields (e.g., ['model', 'agent_id'])
            
        Returns:
            Dictionary with usage statistics
        """
        # Implementation needed
        pass
    
    async def _reset_daily_counters(self) -> None:
        """Reset daily usage counters."""
        self.daily_usage = 0
        self.usage_by_model = defaultdict(int)
        self.usage_by_agent = defaultdict(int)
        logger.info("Daily token usage counters reset")
    
    def _get_next_reset_time(self) -> datetime:
        """Get the next time daily counters should reset."""
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
    
    def _estimate_cost(self, model: str, tokens: int) -> float:
        """
        Estimate the cost of an LLM call based on model and tokens.
        
        Args:
            model: Model identifier
            tokens: Number of tokens used
            
        Returns:
            Estimated cost in USD
        """
        # Basic cost model - should be expanded with actual pricing
        cost_per_1k_tokens = {
            "gpt-3.5-turbo": 0.002,
            "gpt-4": 0.06,
            "gpt-4o": 0.01,
            "claude-3-opus": 0.15,
            "claude-3.5-sonnet": 0.03
        }
        
        base_cost = cost_per_1k_tokens.get(model, 0.01)  # Default if unknown
        return (tokens / 1000) * base_cost


# Singleton instance
tracker = UsageTracker()
```

## How to Use These Templates

1. Create the necessary directories if they don't exist:
   ```bash
   mkdir -p shared/observability
   mkdir -p shared/cost
   ```

2. Copy the templates to their respective locations:
   ```bash
   cp <template-content> shared/observability/langsmith_tracer.py
   cp <template-content> shared/cost/usage_tracker.py
   ```

3. Update the implementations with actual business logic and integration points.

4. Add unit tests for each component in their respective test directories.

5. Update import statements in existing files to use the new components.

## Integration Points

### Integrating LangSmith Tracer

Add to LLM service implementations:

```python
from shared.observability.langsmith_tracer import tracer

# In your LLM wrapper class
async def generate_text(self, prompt, model, max_tokens):
    # Existing LLM call code
    response = await self.client.chat.completions.create(...)
    
    # Add tracing
    await tracer.trace_llm_call(
        prompt=prompt,
        response=response.choices[0].message.content,
        model=model,
        tokens_used=response.usage.total_tokens,
        metadata={"operation": "generate_text"}
    )
    
    return response
```

### Integrating Usage Tracker

Add to LLM service implementations:

```python
from shared.cost.usage_tracker import tracker

# In your LLM wrapper class
async def generate_text(self, prompt, model, max_tokens, agent_id):
    # Check budget before making call
    allowed, budget_info = await tracker.check_budget(
        agent_id=agent_id,
        estimated_tokens=max_tokens,  # Conservative estimate
        model=model
    )
    
    if not allowed:
        # Handle budget exceeded case
        return {"error": "Budget exceeded", "details": budget_info}
    
    # Existing LLM call code
    response = await self.client.chat.completions.create(...)
    
    # Track actual usage
    await tracker.track_usage(
        tokens=response.usage.total_tokens,
        model=model,
        agent_id=agent_id,
        operation_id=None,
        metadata={"prompt_tokens": response.usage.prompt_tokens}
    )
    
    return response
```

### Integrating with Agents

Update BaseSalesAgent to use the new components:

```python
from shared.observability.langsmith_tracer import tracer
from shared.cost.usage_tracker import tracker

# In BaseSalesAgent._generate_llm_response method
async def _generate_llm_response(self, system_message, user_message, max_tokens):
    # Check budget
    allowed, budget_info = await tracker.check_budget(
        agent_id=self.agent_id,
        estimated_tokens=max_tokens,
        model=self.model
    )
    
    if not allowed:
        raise ValueError(f"Budget exceeded: {budget_info}")
    
    # Start tracing
    trace_context = await tracer.start_trace(
        operation_name=f"{self.agent_type}_generate_response",
        metadata={
            "agent_id": self.agent_id,
            "model": self.model
        }
    )
    
    # Make LLM call
    # ... existing code
    
    # Track usage
    await tracker.track_usage(
        tokens=total_tokens,
        model=self.model,
        agent_id=self.agent_id
    )
    
    # End trace
    await tracer.end_trace(
        trace_context=trace_context,
        result=response,
        metadata={"tokens": total_tokens}
    )
    
    return response
