"""
PolicyGate: Content moderation and guardrails for AI-generated outputs.

This module provides policy enforcement for all outbound communications from
AI agents, ensuring content safety, data privacy, and compliance with business rules.
It acts as a gatekeeper that all agent-generated content must pass through before
being sent to users or external systems.
"""

import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp
import numpy as np

from shared.config import guardrail_settings

# Initialize logger
logger = logging.getLogger(__name__)


class ContentRisk(str, Enum):
    """Enumeration of content risk levels."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyResult:
    """Result of a policy check."""
    
    def __init__(
        self,
        allowed: bool,
        risk_level: ContentRisk,
        reason: Optional[str] = None,
        risk_score: float = 0.0,
        flagged_content: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a policy result.
        
        Args:
            allowed: Whether the content is allowed or should be blocked
            risk_level: The assessed risk level of the content
            reason: Optional reason why content was blocked
            risk_score: Numerical risk score (0.0-1.0)
            flagged_content: Specific portions of content that triggered flags
            metadata: Additional metadata about the check
        """
        self.allowed = allowed
        self.risk_level = risk_level
        self.reason = reason
        self.risk_score = risk_score
        self.flagged_content = flagged_content or []
        self.metadata = metadata or {}
    
    def __str__(self) -> str:
        """String representation of policy result."""
        return f"PolicyResult(allowed={self.allowed}, risk_level={self.risk_level}, reason={self.reason})"
    
    def __bool__(self) -> bool:
        """Boolean representation of policy result (True if allowed)."""
        return self.allowed
    
    @property
    def needs_human_review(self) -> bool:
        """Whether this content needs human review."""
        return (self.risk_level in [ContentRisk.MEDIUM, ContentRisk.HIGH] and 
                guardrail_settings.REQUIRE_HUMAN_REVIEW_FOR_MEDIUM_RISK)


class BasePolicy:
    """Base class for all policy checks."""
    
    def __init__(self, name: str, description: str):
        """
        Initialize the policy.
        
        Args:
            name: Name of the policy
            description: Description of what the policy checks
        """
        self.name = name
        self.description = description
    
    async def check(self, content: str, metadata: Dict[str, Any] = None) -> PolicyResult:
        """
        Check if content adheres to this policy.
        
        Args:
            content: Content to check
            metadata: Additional context about the content
            
        Returns:
            PolicyResult indicating whether content passed policy check
        """
        raise NotImplementedError("Subclasses must implement check()")


class ContentModerationPolicy(BasePolicy):
    """Policy for content moderation using external API."""
    
    def __init__(self):
        """Initialize the content moderation policy."""
        super().__init__(
            name="content_moderation",
            description="Checks content for harmful, inappropriate, or offensive material"
        )
        self.api_key = guardrail_settings.MODERATION_API_KEY
        self.api_url = guardrail_settings.MODERATION_API_URL
        self.categories = {
            "sexual": 0.7,
            "hate": 0.7,
            "harassment": 0.7,
            "violence": 0.8,
            "self-harm": 0.8,
            "sexual/minors": 0.3,  # Very low tolerance
            "hate/threatening": 0.6,
            "violence/graphic": 0.7,
        }
    
    async def check(self, content: str, metadata: Dict[str, Any] = None) -> PolicyResult:
        """
        Check content using moderation API.
        
        Args:
            content: Content to check
            metadata: Additional context about the content
            
        Returns:
            PolicyResult with moderation results
        """
        metadata = metadata or {}
        client_id = metadata.get("client_id", "unknown")
        
        try:
            # Call moderation API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json={"input": content},
                    headers={"Authorization": f"Bearer {self.api_key}"}
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error from moderation API: {response.status}")
                        # Default to safe if API fails, but log the error
                        return PolicyResult(
                            allowed=True,
                            risk_level=ContentRisk.SAFE,
                            reason="Error checking content moderation API",
                            metadata={"error": f"API error: {response.status}"}
                        )
                    
                    result = await response.json()
            
            # Process API results
            flagged = False
            highest_score = 0.0
            flagged_categories = []
            
            # Check each category against our thresholds
            scores = result.get("results", [{}])[0].get("category_scores", {})
            for category, threshold in self.categories.items():
                score = scores.get(category, 0.0)
                if score >= threshold:
                    flagged = True
                    flagged_categories.append(category)
                    highest_score = max(highest_score, score)
            
            # Determine risk level based on highest score
            if highest_score >= 0.9:
                risk_level = ContentRisk.CRITICAL
                allowed = False
            elif highest_score >= 0.8:
                risk_level = ContentRisk.HIGH
                allowed = False
            elif highest_score >= 0.7:
                risk_level = ContentRisk.MEDIUM
                allowed = guardrail_settings.ALLOW_MEDIUM_RISK
            elif highest_score >= 0.5:
                risk_level = ContentRisk.LOW
                allowed = True
            else:
                risk_level = ContentRisk.SAFE
                allowed = True
            
            # Log violation if not allowed
            if not allowed:
                logger.warning(
                    f"Content moderation violation for client {client_id}: "
                    f"flagged categories: {flagged_categories}, risk score: {highest_score}"
                )
            
            # Return result
            return PolicyResult(
                allowed=allowed,
                risk_level=risk_level,
                reason="Content violates moderation policy" if not allowed else None,
                risk_score=highest_score,
                flagged_content=[f"Category: {cat}" for cat in flagged_categories],
                metadata={
                    "categories": flagged_categories,
                    "scores": {k: v for k, v in scores.items() if k in self.categories}
                }
            )
            
        except Exception as e:
            logger.exception(f"Error in content moderation check: {str(e)}")
            # Default to safe in case of errors, but log the exception
            return PolicyResult(
                allowed=True,
                risk_level=ContentRisk.SAFE,
                reason="Error checking content",
                metadata={"error": str(e)}
            )


class PiiDetectionPolicy(BasePolicy):
    """Policy for detecting personally identifiable information (PII)."""
    
    def __init__(self):
        """Initialize the PII detection policy."""
        super().__init__(
            name="pii_detection",
            description="Detects and redacts personally identifiable information"
        )
        
        # Regex patterns for common PII
        self.patterns = {
            "credit_card": r"(\d{4}[-\s]?){3}\d{4}",
            "ssn": r"\d{3}[-\s]?\d{2}[-\s]?\d{4}",
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"(?:\+\d{1,2}\s)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
        }
    
    async def check(self, content: str, metadata: Dict[str, Any] = None) -> PolicyResult:
        """
        Check content for PII.
        
        Args:
            content: Content to check
            metadata: Additional context about the content
            
        Returns:
            PolicyResult with PII detection results
        """
        metadata = metadata or {}
        client_id = metadata.get("client_id", "unknown")
        is_outbound = metadata.get("direction", "outbound") == "outbound"
        allowlist = metadata.get("pii_allowlist", [])
        
        try:
            # Check for PII patterns
            found_pii = {}
            redacted_content = content
            
            for pii_type, pattern in self.patterns.items():
                if pii_type in allowlist:
                    continue
                    
                matches = re.finditer(pattern, content)
                for match in matches:
                    match_text = match.group(0)
                    if pii_type not in found_pii:
                        found_pii[pii_type] = []
                    found_pii[pii_type].append(match_text)
                    
                    # Redact PII in output
                    if is_outbound:
                        redaction = f"[REDACTED {pii_type}]"
                        redacted_content = redacted_content.replace(match_text, redaction)
            
            # Determine result based on found PII
            has_pii = len(found_pii) > 0
            
            # For outbound messages, we redact PII but still send the message
            if is_outbound and has_pii:
                logger.info(f"Redacted PII for client {client_id}: {list(found_pii.keys())}")
                return PolicyResult(
                    allowed=True,
                    risk_level=ContentRisk.LOW,
                    reason=None,
                    risk_score=0.3,
                    flagged_content=[f"{k}: {len(v)} instances" for k, v in found_pii.items()],
                    metadata={
                        "pii_found": found_pii,
                        "redacted_content": redacted_content,
                        "action": "redacted"
                    }
                )
            elif not is_outbound and has_pii:
                # For inbound messages with PII, we need to handle it according to the config
                if guardrail_settings.BLOCK_INBOUND_PII:
                    logger.warning(f"Blocked inbound message with PII for client {client_id}")
                    return PolicyResult(
                        allowed=False,
                        risk_level=ContentRisk.MEDIUM,
                        reason="Message contains PII that is not permitted",
                        risk_score=0.6,
                        flagged_content=[f"{k}: {len(v)} instances" for k, v in found_pii.items()],
                        metadata={"pii_found": found_pii}
                    )
                else:
                    logger.info(f"Allowed inbound message with PII for client {client_id}")
                    return PolicyResult(
                        allowed=True,
                        risk_level=ContentRisk.LOW,
                        reason=None,
                        risk_score=0.3,
                        flagged_content=[f"{k}: {len(v)} instances" for k, v in found_pii.items()],
                        metadata={"pii_found": found_pii}
                    )
            else:
                # No PII found
                return PolicyResult(
                    allowed=True,
                    risk_level=ContentRisk.SAFE,
                    reason=None,
                    risk_score=0.0,
                    metadata={"pii_check": "passed"}
                )
            
        except Exception as e:
            logger.exception(f"Error in PII detection check: {str(e)}")
            # Default to allowing the content but log the error
            return PolicyResult(
                allowed=True,
                risk_level=ContentRisk.SAFE,
                reason="Error checking PII",
                metadata={"error": str(e)}
            )


class RateLimitPolicy(BasePolicy):
    """Policy for enforcing rate limits on communications."""
    
    def __init__(self):
        """Initialize rate limit policy."""
        super().__init__(
            name="rate_limit",
            description="Enforces rate limits on communications"
        )
        self.client_counts = {}  # Tracks counts by client_id
        self.max_per_hour = guardrail_settings.MAX_MESSAGES_PER_HOUR
        self.max_per_day = guardrail_settings.MAX_MESSAGES_PER_DAY
    
    async def check(self, content: str, metadata: Dict[str, Any] = None) -> PolicyResult:
        """
        Check if client has exceeded rate limits.
        
        Args:
            content: Content is not used for this check
            metadata: Must contain client_id
            
        Returns:
            PolicyResult indicating if rate limit is exceeded
        """
        metadata = metadata or {}
        client_id = metadata.get("client_id")
        
        if not client_id:
            logger.warning("Rate limit check called without client_id")
            # We can't enforce limits without a client ID
            return PolicyResult(
                allowed=True,
                risk_level=ContentRisk.SAFE,
                reason="No client ID provided for rate limiting",
                metadata={"error": "missing_client_id"}
            )
        
        import time
        current_time = int(time.time())
        hour_ago = current_time - 3600
        day_ago = current_time - 86400
        
        # Initialize client count if not exists
        if client_id not in self.client_counts:
            self.client_counts[client_id] = []
        
        # Remove old timestamps
        self.client_counts[client_id] = [
            ts for ts in self.client_counts[client_id] if ts > day_ago
        ]
        
        # Count messages in last hour and day
        hour_count = sum(1 for ts in self.client_counts[client_id] if ts > hour_ago)
        day_count = len(self.client_counts[client_id])
        
        # Add current message timestamp
        self.client_counts[client_id].append(current_time)
        
        # Check against limits
        if hour_count >= self.max_per_hour:
            logger.warning(f"Rate limit exceeded for client {client_id}: {hour_count} messages in last hour")
            return PolicyResult(
                allowed=False,
                risk_level=ContentRisk.MEDIUM,
                reason=f"Rate limit exceeded: {hour_count}/{self.max_per_hour} messages in last hour",
                risk_score=0.6,
                metadata={
                    "hour_count": hour_count,
                    "day_count": day_count,
                    "hour_limit": self.max_per_hour,
                    "day_limit": self.max_per_day
                }
            )
        
        if day_count >= self.max_per_day:
            logger.warning(f"Rate limit exceeded for client {client_id}: {day_count} messages in last day")
            return PolicyResult(
                allowed=False,
                risk_level=ContentRisk.MEDIUM,
                reason=f"Rate limit exceeded: {day_count}/{self.max_per_day} messages in last day",
                risk_score=0.6,
                metadata={
                    "hour_count": hour_count,
                    "day_count": day_count,
                    "hour_limit": self.max_per_hour,
                    "day_limit": self.max_per_day
                }
            )
        
        # Within limits
        return PolicyResult(
            allowed=True,
            risk_level=ContentRisk.SAFE,
            reason=None,
            risk_score=0.0,
            metadata={
                "hour_count": hour_count,
                "day_count": day_count,
                "hour_limit": self.max_per_hour,
                "day_limit": self.max_per_day
            }
        )


class PolicyGate:
    """
    Main policy gate that applies all policy checks to content.
    
    This is the primary interface for agent-generated content validation.
    It applies multiple policy checks and aggregates results.
    """
    
    def __init__(self):
        """Initialize the policy gate with all policies."""
        self.policies = [
            ContentModerationPolicy(),
            PiiDetectionPolicy(),
            RateLimitPolicy()
        ]
        
        # Add any custom client-specific policies from config
        for policy_config in guardrail_settings.CUSTOM_POLICIES:
            try:
                policy_class = globals()[policy_config.get("class")]
                policy = policy_class(**policy_config.get("args", {}))
                self.policies.append(policy)
            except (KeyError, TypeError) as e:
                logger.error(f"Error initializing custom policy: {str(e)}")
        
        logger.info(f"PolicyGate initialized with {len(self.policies)} policies")
    
    async def check_content(
        self, 
        content: str, 
        metadata: Dict[str, Any] = None
    ) -> Tuple[bool, Dict[str, PolicyResult]]:
        """
        Check content against all policies.
        
        Args:
            content: Content to check
            metadata: Additional context about the content
            
        Returns:
            Tuple of (allowed, {policy_name: PolicyResult})
        """
        metadata = metadata or {}
        results = {}
        allowed = True
        
        # Apply each policy
        for policy in self.policies:
            try:
                result = await policy.check(content, metadata)
                results[policy.name] = result
                
                # If any policy blocks, the overall result is blocked
                if not result.allowed:
                    allowed = False
                    logger.info(
                        f"Content blocked by policy '{policy.name}': "
                        f"{result.reason or 'No reason provided'}"
                    )
            except Exception as e:
                logger.exception(f"Error applying policy {policy.name}: {str(e)}")
                # Don't block content due to policy errors, but log them
        
        return allowed, results
    
    async def filter_content(
        self, 
        content: str, 
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Check and potentially modify content based on policies.
        
        Args:
            content: Content to check and filter
            metadata: Additional context about the content
            
        Returns:
            Dict with filtered content and policy results
        """
        metadata = metadata or {}
        allowed, results = await self.check_content(content, metadata)
        
        # Check if PII was redacted
        pii_result = results.get("pii_detection")
        if pii_result and pii_result.allowed and pii_result.metadata.get("redacted_content"):
            filtered_content = pii_result.metadata["redacted_content"]
        else:
            filtered_content = content
        
        # Determine overall risk level (highest of all policies)
        risk_levels = [result.risk_level for result in results.values()]
        overall_risk = max(risk_levels, key=lambda x: ContentRisk[x.upper()].value)
        
        # Check if human review is needed (any policy requires it)
        needs_review = any(result.needs_human_review for result in results.values())
        
        # Collect reasons if content is blocked
        reasons = []
        if not allowed:
            reasons = [
                f"{policy_name}: {result.reason}" 
                for policy_name, result in results.items() 
                if not result.allowed and result.reason
            ]
        
        return {
            "allowed": allowed,
            "original_content": content,
            "filtered_content": filtered_content,
            "results": results,
            "risk_level": overall_risk,
            "needs_human_review": needs_review,
            "reasons": reasons
        }
