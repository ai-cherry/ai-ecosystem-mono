"""
BuilderTeamAgentManager

A team of AI agents working together to handle complex building tasks.
The manager coordinates multiple agents with different roles to complete tasks.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional

# Import shared memory components
from shared.memory.factory import create_conversation_memory, create_vector_memory
# Import LLM service
from orchestrator.app.services.llm.factory import create_llm_service

# Set up logging
logger = logging.getLogger(__name__)


class BuilderTeamAgentManager:
    """
    Manager for a team of specialized AI agents working together.
    
    This class coordinates multiple agents with different specializations
    (architect, developer, designer, tester) to accomplish complex building tasks.
    """
    
    def __init__(self, 
                 team_id: Optional[str] = None,
                 memory_provider: str = "redis",
                 llm_provider: str = "openai",
                 llm_model: str = "gpt-4o"):
        """
        Initialize the agent manager and team members.
        
        Args:
            team_id: Optional identifier for this team
            memory_provider: Memory backend provider (redis, firestore)
            llm_provider: LLM service provider (openai, etc.)
            llm_model: The model to use for agents
        """
        # Generate team ID if not provided
        self.team_id = team_id or f"team-{uuid.uuid4()}"
        
        # Initialize memory systems
        self.conversation_memory = create_conversation_memory(provider=memory_provider)
        self.vector_memory = create_vector_memory()
        
        # Initialize LLM service for all agents
        self.llm_service = create_llm_service(
            provider=llm_provider,
            model_name=llm_model
        )
        
        # Set up team members/roles
        self.roles = {
            "architect": {
                "name": "Architect",
                "description": "Designs the overall structure and architecture of solutions",
                "instructions": "Focus on creating robust, scalable architectures that follow best practices.",
            },
            "developer": {
                "name": "Developer",
                "description": "Implements the solutions designed by the architect",
                "instructions": "Write clean, efficient code with appropriate error handling and tests.",
            },
            "designer": {
                "name": "Designer",
                "description": "Focuses on UI/UX and visual aspects of solutions",
                "instructions": "Create intuitive, accessible user interfaces that follow modern design patterns.",
            },
            "tester": {
                "name": "Tester",
                "description": "Tests the implemented solutions for bugs and issues",
                "instructions": "Thoroughly test implementations for correctness, reliability, and edge cases.",
            }
        }
        
        # Track conversation state
        self.conversation_id = f"team-convo-{self.team_id}"
        
        logger.info(f"BuilderTeamAgentManager initialized with team_id {self.team_id}")

    def run(self, task: str) -> str:
        """
        Run the builder team agent on the given task.
        
        This method coordinates the team members to analyze, plan, and execute
        the task through a structured workflow.
        
        Args:
            task: The task description to process
            
        Returns:
            Result of the team's work
        """
        try:
            logger.info(f"Team {self.team_id} received task: {task}")
            
            # 1. Save the task to conversation memory
            self.conversation_memory.save_message(
                conversation_id=self.conversation_id,
                message={
                    "role": "user",
                    "content": task
                }
            )
            
            # 2. Let the architect analyze the task first
            architect_response = self._consult_role("architect", task)
            self._store_role_response("architect", architect_response)
            
            # 3. Get input from other team members
            developer_response = self._consult_role("developer", task, context=architect_response)
            self._store_role_response("developer", developer_response)
            
            designer_response = self._consult_role("designer", task, context=architect_response)
            self._store_role_response("designer", designer_response)
            
            # 4. Create a combined response that integrates all team members' input
            final_response = self._create_final_response(
                task, 
                [architect_response, developer_response, designer_response]
            )
            
            # 5. Store the final response in conversation memory
            self.conversation_memory.save_message(
                conversation_id=self.conversation_id,
                message={
                    "role": "assistant",
                    "content": final_response
                }
            )
            
            # 6. Also store in vector memory for later retrieval
            self.vector_memory.upsert_text(
                text=final_response,
                metadata={
                    "task": task,
                    "team_id": self.team_id,
                    "type": "team_response"
                }
            )
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error in BuilderTeamAgentManager.run: {str(e)}")
            error_response = f"The builder team encountered an error: {str(e)}"
            
            # Store error in conversation memory
            self.conversation_memory.save_message(
                conversation_id=self.conversation_id,
                message={
                    "role": "system",
                    "content": error_response
                }
            )
            
            return error_response
    
    def _consult_role(self, role: str, task: str, context: str = "") -> str:
        """
        Consult a specific team role for their input on the task.
        
        Args:
            role: The role to consult
            task: The original task
            context: Optional context from previous role consultations
            
        Returns:
            The role's response
        """
        if role not in self.roles:
            raise ValueError(f"Unknown role: {role}")
        
        role_info = self.roles[role]
        
        # Construct prompt for this role
        prompt = {
            "system": f"You are the {role_info['name']} on a builder team. {role_info['description']}. {role_info['instructions']}",
            "user": f"Task: {task}" + (f"\n\nContext from team:\n{context}" if context else "")
        }
        
        # Process with LLM
        result = self.llm_service.process(prompt)
        
        return result.get("content", "No response generated")
    
    def _store_role_response(self, role: str, response: str) -> None:
        """
        Store a role's response in conversation memory.
        
        Args:
            role: The role that generated the response
            response: The response content
        """
        self.conversation_memory.save_message(
            conversation_id=self.conversation_id,
            message={
                "role": "system",
                "content": f"[{self.roles[role]['name']}] {response}"
            }
        )
    
    def _create_final_response(self, task: str, role_responses: List[str]) -> str:
        """
        Create a final integrated response from all team members.
        
        Args:
            task: The original task
            role_responses: List of responses from different roles
            
        Returns:
            Integrated final response
        """
        # Construct prompt for generating the final response
        prompt = {
            "system": "You are the Team Coordinator. Your job is to create a comprehensive, cohesive response that integrates input from multiple team members.",
            "user": f"Task: {task}\n\nTeam Input:\n\n" + "\n\n".join([
                f"- {self.roles[role]['name']}: {resp}" 
                for role, resp in zip(["architect", "developer", "designer"], role_responses)
            ]) + "\n\nCreate a final response that integrates these perspectives and addresses the task comprehensively."
        }
        
        # Process with LLM
        result = self.llm_service.process(prompt)
        
        return result.get("content", "Error creating final response")
