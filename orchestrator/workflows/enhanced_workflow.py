"""
Enhanced Temporal workflows with memory and LLM integration.

This module extends the sample workflow with more realistic functionality,
including integration with memory systems and LLM services.
"""

from datetime import timedelta
from typing import Dict, Any, Optional
import uuid
import logging

from temporalio import workflow, activity
from temporalio.exceptions import ApplicationError

from shared.memory.redis import RedisMemory
from orchestrator.app.services.llm.base import LLMService

# Set up logging
logger = logging.getLogger(__name__)


@activity.defn
async def process_with_llm_and_memory(
    data: str,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Activity that processes input using LLM and stores results in memory.
    
    Args:
        data: Text input to process
        conversation_id: Optional existing conversation ID
        user_id: Optional user ID for the conversation
        
    Returns:
        Dictionary with processing results and metadata
    """
    # Generate a conversation ID if not provided
    if not conversation_id:
        conversation_id = f"conversation-{uuid.uuid4()}"
    
    # Initialize memory and LLM services
    memory = RedisMemory()
    llm_service = LLMService()
    
    try:
        # Save user input to memory
        memory.save_message(
            conversation_id=conversation_id,
            message={
                "role": "user",
                "content": data
            },
            user_id=user_id
        )
        
        # Process with LLM
        llm_result = llm_service.process(data)
        
        if isinstance(llm_result, dict) and "result" in llm_result:
            result_content = llm_result["result"]
            confidence = llm_result.get("confidence", 1.0)
        else:
            # Handle unexpected LLM output format
            result_content = str(llm_result)
            confidence = 0.5
        
        # Save LLM response to memory
        memory.save_message(
            conversation_id=conversation_id,
            message={
                "role": "assistant",
                "content": result_content
            },
            user_id=user_id
        )
        
        # Return success result
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "result": result_content,
            "confidence": confidence
        }
    
    except Exception as e:
        logger.error(f"Error in LLM processing: {str(e)}")
        
        # Save error message to memory
        memory.save_message(
            conversation_id=conversation_id,
            message={
                "role": "system",
                "content": f"Error processing: {str(e)}"
            },
            user_id=user_id
        )
        
        # Try to generate a fallback response
        try:
            fallback_response = "I'm sorry, I couldn't process your request properly."
            
            # Save fallback response to memory
            memory.save_message(
                conversation_id=conversation_id,
                message={
                    "role": "assistant",
                    "content": fallback_response
                },
                user_id=user_id
            )
            
            # Return fallback result
            return {
                "status": "fallback",
                "conversation_id": conversation_id,
                "result": fallback_response,
                "error": str(e)
            }
        
        except Exception as fallback_error:
            logger.error(f"Error in fallback handling: {str(fallback_error)}")
            
            # Return error result
            return {
                "status": "error",
                "conversation_id": conversation_id,
                "error": str(e),
                "fallback_error": str(fallback_error)
            }


@activity.defn
async def retrieve_conversation_history(
    conversation_id: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Activity that retrieves conversation history from memory.
    
    Args:
        conversation_id: The conversation ID to retrieve
        limit: Optional maximum number of messages to retrieve
        
    Returns:
        Dictionary with conversation history
    """
    try:
        memory = RedisMemory()
        conversation = memory.get_conversation(conversation_id, limit=limit)
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "messages": conversation,
            "message_count": len(conversation)
        }
    
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}")
        
        return {
            "status": "error",
            "conversation_id": conversation_id,
            "error": str(e)
        }


@workflow.defn
class EnhancedProcessingWorkflow:
    """
    Enhanced workflow for processing text with LLM and memory persistence.
    
    This workflow:
    1. Processes input using LLM
    2. Stores the input and result in memory
    3. Includes error handling and fallback logic
    4. Optionally retrieves conversation history
    """
    
    @workflow.run
    async def run(
        self, 
        input_data: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        retrieve_history: bool = False
    ) -> Dict[str, Any]:
        """
        Execute the workflow with the given input data.
        
        Args:
            input_data: Text to process
            conversation_id: Optional existing conversation ID
            user_id: Optional user ID for the conversation
            retrieve_history: Whether to retrieve conversation history after processing
            
        Returns:
            Dictionary with processing results and metadata
        """
        # Generate a conversation ID if not provided
        if not conversation_id:
            conversation_id = workflow.uuid4()
            conversation_id = f"conversation-{conversation_id}"
        
        try:
            # Execute the LLM processing activity with retry policy
            result = await workflow.execute_activity(
                process_with_llm_and_memory,
                input_data,
                conversation_id,
                user_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                    non_retryable_error_types=["ValueError", "KeyError"]
                )
            )
            
            # If requested, retrieve conversation history
            if retrieve_history:
                history = await workflow.execute_activity(
                    retrieve_conversation_history,
                    conversation_id,
                    start_to_close_timeout=timedelta(seconds=10)
                )
                
                # Add history to the result
                if history["status"] == "success":
                    result["history"] = history["messages"]
            
            return result
            
        except Exception as e:
            return {
                "status": "failed",
                "conversation_id": conversation_id,
                "error": str(e)
            }
