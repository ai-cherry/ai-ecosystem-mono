"""
Planner → Tool → Responder workflow using LangChain and VectorStore.

This workflow demonstrates a real agentic chain:
- Planner: Decides which tool to use (here, always LLM for demo)
- Tool: Uses LangChain LLM to process input
- Responder: Formats the output
- Stores results in vector memory (Pinecone via VectorStore)
"""

from typing import Dict, Any, Union
from temporalio import workflow

from shared.memory.factory import create_vector_memory
from orchestrator.app.services.llm.factory import create_llm_service


@workflow.defn
class PlannerToolResponderWorkflow:
    """
    Planner → Tool → Responder workflow using LangChain and VectorStore.
    """

    @workflow.run
    async def run(self, input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute the workflow:
        1. Plan (decide tool)
        2. Run tool (LLM)
        3. Store result in vector memory
        4. Respond

        Args:
            input_data: User input string or object with configuration

        Returns:
            Dict with status, result, and vector memory doc_id
        """
        try:
            # Convert string input to dict if needed
            if isinstance(input_data, str):
                input_data = {"user": input_data}
            
            # 1. Planner: In a real implementation, this would decide which tool to use
            # based on user input, capabilities, and context
            tool = "llm"
            
            # 2. Tool: Run the LLM with input data
            llm_result = await workflow.execute_activity(
                process_with_llm,
                input_data,
                start_to_close_timeout="5 minutes"
            )
            
            # 3. Store in vector memory
            doc_id = await workflow.execute_activity(
                store_in_vector_memory,
                text=llm_result.get("content", ""),
                metadata={
                    "input": input_data, 
                    "tool": tool,
                    "model": llm_result.get("model", "unknown")
                },
                start_to_close_timeout="2 minutes"
            )
            
            # 4. Responder: Format output
            return {
                "status": "completed",
                "result": llm_result.get("content", ""),
                "model": llm_result.get("model", "unknown"),
                "vector_doc_id": doc_id,
                "metadata": llm_result.get("metadata", {})
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }


# Activity implementations

@workflow.activity
async def process_with_llm(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input with LLM.
    
    Args:
        input_data: Input data for the LLM
        
    Returns:
        LLM processing result
    """
    # Get the LLM service
    llm_service = create_llm_service(
        provider=input_data.get("provider", "openai"),
        model_name=input_data.get("model", None)
    )
    
    # Process the input
    return llm_service.process(input_data)


@workflow.activity
async def store_in_vector_memory(text: str, metadata: Dict[str, Any]) -> str:
    """
    Store text in vector memory.
    
    Args:
        text: The text to store
        metadata: Metadata to associate with the text
        
    Returns:
        Document ID in vector store
    """
    # Get the vector memory service
    vector_memory = create_vector_memory()
    
    # Store the text
    return vector_memory.upsert_text(text=text, metadata=metadata)
