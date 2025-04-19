from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class Settings(BaseModel):
    # API settings
    PROJECT_NAME: str = "AI Orchestrator"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Memory settings
    # Firestore settings
    FIRESTORE_PROJECT_ID: Optional[str] = None
    FIRESTORE_EMULATOR_HOST: Optional[str] = None
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: Optional[str] = None
    
    # Vector store settings
    VECTOR_STORE_TYPE: str = "pinecone"  # or "weaviate", etc.
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: str = "us-west1-gcp"
    PINECONE_INDEX_NAME: str = "ai-orchestrator"
    
    # Embedding settings
    OPENAI_API_KEY: Optional[str] = None
    
    # LLM settings
    DEFAULT_LLM_MODEL: str = "gpt-4"
    
    # Temporal workflow settings
    TEMPORAL_HOST_URL: str = "localhost:7233"
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "ai-orchestrator-tq"
    
    # Additional environment variables
    DEV_MODE: bool = False
    LOG_LEVEL: str = "INFO"
    
    @classmethod
    @validator('REDIS_URL')
    def redis_url_must_have_password_if_exists(cls, v, values):
        """
        If REDIS_PASSWORD is set, ensure it's included in the REDIS_URL if not already present
        """
        if values.get('REDIS_PASSWORD') and '://:' not in v:
            # Split the URL into parts
            parts = v.split('://')
            if len(parts) == 2:
                # Insert password
                return f"{parts[0]}://:{values['REDIS_PASSWORD']}@{parts[1]}"
        return v
    
    class Config:
        case_sensitive = True
        env_file = ".env"  # load variables from .env in dev


settings = Settings()
