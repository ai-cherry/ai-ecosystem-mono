"""
Planner → Tool → Responder workflow using LangChain and VectorStore.

This workflow demonstrates a real agentic chain:
- Planner: Decides which tool to use (here, always LLM for demo)
- Tool: Uses LangChain LLM to process input
- Responder: Formats the output
- Stores results in vector memory (Pinecone via VectorStore)
"""

from typing import Dict, Any
from temporalio import workflow

from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from shared.memory.vectorstore import VectorStore

@workflow.defn
class PlannerToolResponderWorkflow:
    """
    Planner → Tool → Responder workflow using LangChain and VectorStore.
    """

    @workflow.run
    async def run(self, input_data: str) -> Dict[str, Any]:
        """
        Execute the workflow:
        1. Plan (decide tool)
        2. Run tool (LLM)
        3. Store result in vector memory
        4. Respond

        Args:
            input_data: User input string

        Returns:
            Dict with status, result, and vector memory doc_id
        """
        try:
            # 1. Planner: (for demo, always use LLM tool)
            tool = "llm"

            # 2. Tool: Run LLMChain with a simple prompt
            prompt = PromptTemplate(
                input_variables=["input"],
                template="You are an expert assistant. Answer the following:\n{input}"
            )
            llm = OpenAI(temperature=0.2)
            chain = LLMChain(llm=llm, prompt=prompt)
            result = await chain.arun(input=input_data)

            # 3. Store in vector memory
            vectorstore = VectorStore()
            doc_id = vectorstore.upsert_text(
                text=result,
                metadata={"input": input_data, "tool": tool}
            )

            # 4. Responder: Format output
            return {
                "status": "completed",
                "result": result,
                "vector_doc_id": doc_id
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }