"""
Configuration settings for the AI Ecosystem.

This module provides centralized configuration for all components of the system,
using Pydantic for validation and environment variable loading.
"""

import os
import json
from typing import Any, Dict, List, Optional, Union
from functools import lru_cache

# Import from correct location based on pydantic version
try:
    # Pydantic v2+
    from pydantic.v1 import BaseSettings, Field, validator
except ImportError:
    # Pydantic v1
    from pydantic import BaseSettings, Field, validator


class MemorySettings(BaseSettings):
    """Settings for memory services."""
    
    # Firestore settings
    FIRESTORE_PROJECT_ID: Optional[str] = Field(None, env="FIRESTORE_PROJECT_ID")
    
    # Redis settings
    REDIS_URL: str = Field("redis://localhost:6379", env="REDIS_URL")
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD")
    REDIS_TTL: int = Field(3600, env="REDIS_TTL")  # Default TTL in seconds
    
    # Vector store settings
    VECTOR_STORE_TYPE: str = Field("pinecone", env="VECTOR_STORE_TYPE")
    PINECONE_API_KEY: Optional[str] = Field(None, env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = Field("us-west1-gcp", env="PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: str = Field("ai-orchestrator", env="PINECONE_INDEX_NAME")
    
    # Weaviate settings
    WEAVIATE_URL: Optional[str] = Field(None, env="WEAVIATE_URL")
    WEAVIATE_API_KEY: Optional[str] = Field(None, env="WEAVIATE_API_KEY")
    
    # OpenAI settings for embeddings
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    EMBEDDING_MODEL: str = Field("text-embedding-ada-002", env="EMBEDDING_MODEL")
    
    @classmethod
    @validator('VECTOR_STORE_TYPE')
    def validate_vector_store_type(cls, v):
        allowed = ["pinecone", "weaviate", "firestore"]
        if v not in allowed:
            raise ValueError(f"VECTOR_STORE_TYPE must be one of {allowed}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class LLMSettings(BaseSettings):
    """Settings for LLM services."""
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    DEFAULT_MODEL: str = Field("gpt-4", env="DEFAULT_MODEL")
    TEMPERATURE: float = Field(0.7, env="TEMPERATURE")
    MAX_TOKENS: int = Field(1000, env="MAX_TOKENS")
    
    # Timeout settings
    REQUEST_TIMEOUT: int = Field(60, env="REQUEST_TIMEOUT")  # seconds
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(60, env="RATE_LIMIT_REQUESTS")  # requests per minute
    
    # Cost tracking
    TRACK_TOKEN_USAGE: bool = Field(True, env="TRACK_TOKEN_USAGE")
    MAX_DAILY_TOKENS: int = Field(100000, env="MAX_DAILY_TOKENS")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class APISettings(BaseSettings):
    """Settings for the API."""
    
    # Server settings
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")
    DEBUG: bool = Field(False, env="DEBUG")
    
    # CORS settings
    CORS_ORIGINS: List[str] = Field(["*"], env="CORS_ORIGINS")
    
    # Authentication
    AUTH_ENABLED: bool = Field(True, env="AUTH_ENABLED")
    AUTH_TOKEN: Optional[str] = Field(None, env="AUTH_TOKEN")
    
    @classmethod
    @validator('CORS_ORIGINS', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class GuardrailSettings(BaseSettings):
    """Settings for content moderation and guardrails."""
    
    # Content moderation
    MODERATION_API_URL: str = Field(
        "https://api.openai.com/v1/moderations", 
        env="MODERATION_API_URL"
    )
    MODERATION_API_KEY: Optional[str] = Field(None, env="MODERATION_API_KEY")
    ALLOW_MEDIUM_RISK: bool = Field(False, env="ALLOW_MEDIUM_RISK")
    REQUIRE_HUMAN_REVIEW_FOR_MEDIUM_RISK: bool = Field(
        True, 
        env="REQUIRE_HUMAN_REVIEW_FOR_MEDIUM_RISK"
    )
    
    # PII detection settings
    BLOCK_INBOUND_PII: bool = Field(False, env="BLOCK_INBOUND_PII")
    
    # Rate limiting
    MAX_MESSAGES_PER_HOUR: int = Field(100, env="MAX_MESSAGES_PER_HOUR")
    MAX_MESSAGES_PER_DAY: int = Field(1000, env="MAX_MESSAGES_PER_DAY")
    
    # Custom policies
    CUSTOM_POLICIES: List[Dict[str, Any]] = Field([], env="CUSTOM_POLICIES")
    
    @classmethod
    @validator('CUSTOM_POLICIES', pre=True)
    def parse_custom_policies(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class BuilderAgentSettings(BaseSettings):
    """Settings for Builder Agent security and capabilities."""
    
    # Security settings
    CODE_GENERATION_ENABLED: bool = Field(True, env="CODE_GENERATION_ENABLED")
    REQUIRE_PR_APPROVAL: bool = Field(True, env="REQUIRE_PR_APPROVAL")
    ALLOWED_IMPORT_PATTERNS: List[str] = Field(
        ["^os$", "^sys$", "^re$", "^json$", "^time$", "^datetime$", "^math$"],
        env="ALLOWED_IMPORT_PATTERNS"
    )
    BLOCKED_IMPORT_PATTERNS: List[str] = Field(
        ["^subprocess", "^shutil", "^requests", "^urllib", "^socket"],
        env="BLOCKED_IMPORT_PATTERNS"
    )
    
    # File access
    ALLOWED_WRITE_PATHS: List[str] = Field(
        ["./generated", "./output", "./temp"],
        env="ALLOWED_WRITE_PATHS"
    )
    
    # Execution limits
    MAX_EXECUTION_TIME_SECONDS: int = Field(30, env="MAX_EXECUTION_TIME_SECONDS")
    
    @classmethod
    @validator('ALLOWED_IMPORT_PATTERNS', 'BLOCKED_IMPORT_PATTERNS', 'ALLOWED_WRITE_PATHS', pre=True)
    def parse_list(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class ObservabilitySettings(BaseSettings):
    """Settings for observability and monitoring."""
    
    # LangSmith tracing
    LANGSMITH_ENABLED: bool = Field(False, env="LANGSMITH_ENABLED")
    LANGSMITH_API_KEY: Optional[str] = Field(None, env="LANGSMITH_API_KEY")
    LANGSMITH_PROJECT: str = Field("ai-ecosystem", env="LANGSMITH_PROJECT")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    
    # Metrics
    PROMETHEUS_ENABLED: bool = Field(False, env="PROMETHEUS_ENABLED")
    PROMETHEUS_PORT: int = Field(9090, env="PROMETHEUS_PORT")
    
    # Grafana dashboard ID
    GRAFANA_DASHBOARD_ID: Optional[str] = Field(None, env="GRAFANA_DASHBOARD_ID")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_memory_settings() -> MemorySettings:
    """Get memory settings as a cached singleton."""
    return MemorySettings()


@lru_cache()
def get_llm_settings() -> LLMSettings:
    """Get LLM settings as a cached singleton."""
    return LLMSettings()


@lru_cache()
def get_api_settings() -> APISettings:
    """Get API settings as a cached singleton."""
    return APISettings()


@lru_cache()
def get_guardrail_settings() -> GuardrailSettings:
    """Get guardrail settings as a cached singleton."""
    return GuardrailSettings()


@lru_cache()
def get_builder_agent_settings() -> BuilderAgentSettings:
    """Get builder agent settings as a cached singleton."""
    return BuilderAgentSettings()


@lru_cache()
def get_observability_settings() -> ObservabilitySettings:
    """Get observability settings as a cached singleton."""
    return ObservabilitySettings()


# Create instances for direct import
memory_settings = get_memory_settings()
llm_settings = get_llm_settings()  
api_settings = get_api_settings()
guardrail_settings = get_guardrail_settings()
builder_agent_settings = get_builder_agent_settings()
observability_settings = get_observability_settings()
