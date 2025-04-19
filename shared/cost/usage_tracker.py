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

# For type hints only
from typing import TYPE_CHECKING
if TYPE_CHECKING:
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
    
    def __init__(self, redis_client: Optional[Any] = None):
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
    
    def _get_next_reset_time(self) -> datetime:
        """Get the next time daily counters should reset (midnight UTC)."""
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
    
    async def _reset_daily_counters(self) -> None:
        """Reset daily usage counters."""
        self.daily_usage = 0
        self.usage_by_model = defaultdict(int)
        self.usage_by_agent = defaultdict(int)
        logger.info("Daily token usage counters reset")
    
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
                daily_key = f"usage:{current_time.strftime('%Y-%m-%d')}"
                await self.redis_client.hincrby(daily_key, "total", tokens)
                await self.redis_client.hincrby(daily_key, f"model:{model}", tokens)
                await self.redis_client.hincrby(daily_key, f"agent:{agent_id}", tokens)
                await self.redis_client.expire(daily_key, 60 * 60 * 24 * 30)  # Keep for 30 days
                
                # Add client tracking if provided
                if "client_id" in metadata:
                    client_id = metadata["client_id"]
                    client_key = f"usage:{current_time.strftime('%Y-%m-%d')}:client:{client_id}"
                    await self.redis_client.hincrby(client_key, "total", tokens)
                    await self.redis_client.expire(client_key, 60 * 60 * 24 * 30)  # Keep for 30 days
                
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
        operation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a planned LLM call is within budget.
        
        Args:
            agent_id: ID of the agent making the call
            estimated_tokens: Estimated token usage
            model: Model to be used
            operation_id: Optional operation identifier
            metadata: Additional context
            
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
        
        # Get most accurate usage data from Redis if available
        usage_total = self.daily_usage
        if self.redis_client:
            try:
                daily_key = f"usage:{current_time.strftime('%Y-%m-%d')}"
                redis_total = await self.redis_client.hget(daily_key, "total")
                if redis_total:
                    usage_total = int(redis_total)
            except Exception as e:
                logger.error(f"Error checking budget in Redis: {str(e)}")
        
        # Check client-specific budget if client_id provided
        client_limit = None
        client_usage = 0
        if metadata and "client_id" in metadata:
            client_id = metadata["client_id"]
            # TODO: Implement client-specific limits by retrieving from config
            # For now, we'll use the global limit
            client_limit = self.daily_limit
            
            if self.redis_client:
                try:
                    client_key = f"usage:{current_time.strftime('%Y-%m-%d')}:client:{client_id}"
                    redis_client_total = await self.redis_client.hget(client_key, "total")
                    if redis_client_total:
                        client_usage = int(redis_client_total)
                except Exception as e:
                    logger.error(f"Error checking client budget in Redis: {str(e)}")
        
        # Check agent-specific budget
        agent_limit = None  
        agent_usage = 0
        # TODO: Implement agent-specific limits by retrieving from config
        # For now, we'll use the global limit
        agent_limit = self.daily_limit
        
        if self.redis_client:
            try:
                daily_key = f"usage:{current_time.strftime('%Y-%m-%d')}"
                redis_agent_total = await self.redis_client.hget(daily_key, f"agent:{agent_id}")
                if redis_agent_total:
                    agent_usage = int(redis_agent_total)
            except Exception as e:
                logger.error(f"Error checking agent budget in Redis: {str(e)}")
        
        # Calculate remaining tokens at each level
        global_remaining = max(0, self.daily_limit - usage_total)
        client_remaining = None if client_limit is None else max(0, client_limit - client_usage)
        agent_remaining = None if agent_limit is None else max(0, agent_limit - agent_usage)
        
        # Find the most restrictive limit
        remaining = global_remaining
        if client_remaining is not None:
            remaining = min(remaining, client_remaining)
        if agent_remaining is not None:
            remaining = min(remaining, agent_remaining)
        
        # Check if the estimated tokens would exceed the budget
        allowed = estimated_tokens <= remaining
        
        # Prepare budget info
        budget_info = {
            "allowed": allowed,
            "estimated_tokens": estimated_tokens,
            "remaining": remaining,
            "global_usage": usage_total,
            "global_limit": self.daily_limit,
            "global_remaining": global_remaining,
            "global_percentage": (usage_total / self.daily_limit) * 100 if self.daily_limit > 0 else 0,
        }
        
        # Add client and agent info if available
        if client_limit is not None:
            budget_info.update({
                "client_usage": client_usage,
                "client_limit": client_limit,
                "client_remaining": client_remaining,
                "client_percentage": (client_usage / client_limit) * 100 if client_limit > 0 else 0
            })
        
        if agent_limit is not None:
            budget_info.update({
                "agent_usage": agent_usage,
                "agent_limit": agent_limit,
                "agent_remaining": agent_remaining,
                "agent_percentage": (agent_usage / agent_limit) * 100 if agent_limit > 0 else 0
            })
        
        # Log if budget exceeded
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
        # Default to today if not specified
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        # Default grouping
        group_by = group_by or ['model', 'agent_id']
        
        # Initialize report
        report = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_tokens": 0,
            "total_cost": 0.0,
            "groupings": {}
        }
        
        # Check if Redis is available
        if not self.redis_client:
            return {
                **report,
                "error": "Redis not available for historical reporting"
            }
        
        try:
            # Get all days in range
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                daily_key = f"usage:{date_str}"
                
                # Get total tokens for the day
                total_tokens = await self.redis_client.hget(daily_key, "total")
                if total_tokens:
                    day_tokens = int(total_tokens)
                    report["total_tokens"] += day_tokens
                
                # Get breakdowns by requested groupings
                for group in group_by:
                    if group not in report["groupings"]:
                        report["groupings"][group] = {}
                    
                    # Get all keys for this grouping
                    group_pattern = f"{group}:*"
                    keys = await self.redis_client.hkeys(daily_key)
                    group_keys = [k for k in keys if k.startswith(group_pattern)]
                    
                    for key in group_keys:
                        # Extract group value (e.g., model:gpt-4 -> gpt-4)
                        group_value = key.split(":", 1)[1] if ":" in key else key
                        
                        # Get tokens for this group
                        group_tokens = await self.redis_client.hget(daily_key, key)
                        if group_tokens:
                            tokens = int(group_tokens)
                            if group_value not in report["groupings"][group]:
                                report["groupings"][group][group_value] = 0
                            report["groupings"][group][group_value] += tokens
                
                # Move to next day
                current_date += timedelta(days=1)
            
            # Calculate costs if 'model' was one of the groupings
            if 'model' in report["groupings"]:
                for model, tokens in report["groupings"]["model"].items():
                    cost = self._estimate_cost(model, tokens)
                    report["total_cost"] += cost
            
            return report
        except Exception as e:
            logger.error(f"Error generating usage report: {str(e)}")
            return {
                **report,
                "error": f"Error generating report: {str(e)}"
            }


# Singleton instance for global use
tracker = UsageTracker()
