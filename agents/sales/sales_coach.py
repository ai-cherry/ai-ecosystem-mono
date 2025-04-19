"""
SalesCoachAgent implementation for AI sales pipeline.

This module defines the SalesCoachAgent class which provides real-time
coaching, training, and feedback to sales representatives.
It extends the BaseSalesAgent abstract class.
"""

from typing import Any, Dict, List, Optional
import asyncio

from agents.base.sales_agent_base import BaseSalesAgent, AgentTask, AgentPlan, AgentResult, MemoryItem
from shared.memory.memory_manager import MemoryManager

class SalesCoachAgent(BaseSalesAgent):
    """
    Agent for providing sales coaching, training, and feedback.
    
    Capabilities:
    - Analyzes sales call transcripts
    - Provides specific feedback on sales techniques
    - Suggests improvements for future calls
    - Creates personalized training plans
    """
    
    def __init__(
        self,
        memory: MemoryManager,
        transcription_api_key: str = None,
        performance_db_connection: str = None,
        training_resources_path: str = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the SalesCoachAgent with required API credentials."""
        # Initialize tools
        tools = {}
        
        # Transcript analysis tool
        if transcription_api_key:
            async def analyze_transcript(transcript_text: str) -> Dict[str, Any]:
                """Analyze a sales call transcript for coaching insights."""
                # In a real implementation, this would call an NLP API
                # Mocked for demonstration
                await asyncio.sleep(1)  # Simulate API call
                return {
                    "talk_ratio": {"rep": 0.6, "customer": 0.4},
                    "key_topics": ["pricing", "features", "competition"],
                    "sentiment": {"positive": 0.7, "negative": 0.1, "neutral": 0.2},
                    "questions_asked": 5,
                    "filler_words": {"um": 12, "like": 8, "you know": 3},
                    "improvement_areas": ["listening", "value proposition", "objection handling"]
                }
            
            tools["AnalyzeTranscript"] = analyze_transcript
        
        # Sales performance data retrieval
        if performance_db_connection:
            async def get_performance_metrics(rep_id: str, date_range: str = "30d") -> Dict[str, Any]:
                """Get performance metrics for a sales rep over time."""
                # In a real implementation, this would query a database
                # Mocked for demonstration
                await asyncio.sleep(1)  # Simulate database query
                return {
                    "calls_made": 45,
                    "meetings_booked": 8,
                    "deals_closed": 3,
                    "revenue": 45000,
                    "avg_deal_size": 15000,
                    "conversion_rate": 0.067,
                    "trends": {
                        "calls_trend": "+5%",
                        "meetings_trend": "-2%",
                        "deals_trend": "+10%"
                    }
                }
            
            tools["GetPerformanceMetrics"] = get_performance_metrics
        
        # Training resource recommendation
        if training_resources_path:
            async def recommend_training(areas: List[str], skill_level: str = "intermediate") -> Dict[str, Any]:
                """Recommend training resources for specific improvement areas."""
                # In a real implementation, this would search a training database
                # Mocked for demonstration
                await asyncio.sleep(1)  # Simulate search
                return {
                    "resources": [
                        {"title": "Mastering Objection Handling", "type": "video", "duration": "32min"},
                        {"title": "Active Listening in Sales", "type": "article", "duration": "15min"},
                        {"title": "Value Proposition Workshop", "type": "interactive", "duration": "60min"}
                    ],
                    "priority": areas[0] if areas else "general",
                    "estimated_completion_time": "2 hours"
                }
            
            tools["RecommendTraining"] = recommend_training
        
        # Configure default storage policy for this agent
        merged_config = {
            "store_outputs_for_tools": ["AnalyzeTranscript", "RecommendTraining"],
            **(config or {})
        }
        
        super().__init__(
            name="sales_coach_agent",
            role="Sales Coach and Trainer",
            description="Provides coaching, feedback, and training to sales representatives",
            memory=memory,
            tools=tools,
            config=merged_config
        )
    
    async def plan(self, task: AgentTask, context: List[MemoryItem]) -> AgentPlan:
        """Create a coaching plan based on transcripts and performance data."""
        self.logger.info(f"Planning sales coaching for task {task['id']}")
        
        # Format context for the agent
        context_text = "\n".join([
            f"--- Context Item {i+1} ---\n{item['text']}\n"
            for i, item in enumerate(context)
        ])
        
        # Extract coaching details from task parameters
        coaching_params = task["parameters"]
        rep_id = coaching_params.get("rep_id", "unknown")
        transcript_text = coaching_params.get("transcript_text", "")
        coaching_focus = coaching_params.get("focus_areas", [])
        
        # Construct prompt for planning
        prompt = f"""
        You are a Sales Coach tasked with the following:
        
        Task: {task['description']}
        
        Sales Rep ID: {rep_id}
        Coaching Focus Areas: {', '.join(coaching_focus) if coaching_focus else 'General coaching'}
        
        Here is relevant context from our system:
        {context_text}
        
        Available tools:
        1. AnalyzeTranscript - Analyzes a sales call transcript for coaching insights
        2. GetPerformanceMetrics - Retrieves performance data for a sales rep
        3. RecommendTraining - Recommends training resources for specific improvement areas
        
        Create a detailed step-by-step plan for coaching this sales rep. For each step:
        1. Explain your thought process
        2. Identify which tool to use
        3. Specify the exact input for the tool
        4. Describe what you expect to learn or accomplish with this step
        
        Structure your plan as a sequence of well-reasoned steps.
        """
        
        # Use Agno for chain-of-thought reasoning
        plan_response = await self.agno_agent.run(prompt)
        
        # Parse the response to extract steps
        steps = []
        thought_process = plan_response
        
        # Structured step extraction based on coaching parameters
        step_id = 1
        
        # First analyze the transcript if available
        if "AnalyzeTranscript" in self.tools and transcript_text:
            steps.append({
                "step_id": step_id,
                "tool_name": "AnalyzeTranscript",
                "input_args": {"transcript_text": transcript_text},
                "expected_output": "Analysis of call transcript with coaching insights",
                "status": "pending",
                "output": None,
                "error": None
            })
            step_id += 1
        
        # Get performance metrics if rep_id is available
        if "GetPerformanceMetrics" in self.tools and rep_id:
            steps.append({
                "step_id": step_id,
                "tool_name": "GetPerformanceMetrics",
                "input_args": {"rep_id": rep_id, "date_range": "30d"},
                "expected_output": "Sales performance metrics for the rep",
                "status": "pending",
                "output": None,
                "error": None
            })
            step_id += 1
        
        # Recommend training based on focus areas
        if "RecommendTraining" in self.tools and coaching_focus:
            steps.append({
                "step_id": step_id,
                "tool_name": "RecommendTraining",
                "input_args": {"areas": coaching_focus, "skill_level": "intermediate"},
                "expected_output": "Recommended training resources",
                "status": "pending",
                "output": None,
                "error": None
            })
            step_id += 1
        
        return {
            "task_id": task["id"],
            "thought_process": thought_process,
            "steps": steps,
            "estimated_duration_seconds": 60 * len(steps)  # Rough estimate
        }
    
    async def act(self, plan: AgentPlan) -> AgentResult:
        """Execute the coaching plan by analyzing data and generating recommendations."""
        self.logger.info(f"Executing sales coaching plan for task {plan['task_id']}")
        
        steps_executed = []
        tool_outputs = {}
        transcript_analysis = None
        performance_data = None
        
        # Execute each step in the plan
        for step in plan["steps"]:
            step_copy = dict(step)  # Copy to avoid modifying the original
            step_copy["status"] = "in_progress"
            steps_executed.append(step_copy)
            
            tool_name = step["tool_name"]
            tool_fn = self.tools.get(tool_name)
            
            if not tool_fn:
                step_copy["status"] = "failed"
                step_copy["error"] = f"Tool {tool_name} not available"
                continue
                
            try:
                # Execute the tool
                self.logger.info(f"Executing tool {tool_name} with args {step['input_args']}")
                result = await tool_fn(**step["input_args"])
                
                # Store result and capture specific results for later use
                if tool_name == "AnalyzeTranscript":
                    transcript_analysis = result
                elif tool_name == "GetPerformanceMetrics":
                    performance_data = result
                
                # Store result
                step_copy["status"] = "completed"
                step_copy["output"] = result
                tool_outputs[f"{tool_name}_{step['step_id']}"] = result
                
            except Exception as e:
                self.logger.error(f"Error executing {tool_name}: {str(e)}")
                step_copy["status"] = "failed"
                step_copy["error"] = str(e)
        
        # Generate coaching feedback with Agno
        if any(s["status"] == "completed" for s in steps_executed):
            outputs_text = "\n\n".join([
                f"--- {s['tool_name']} Result ---\n{str(s['output'])}"
                for s in steps_executed if s["status"] == "completed"
            ])
            
            coaching_prompt = f"""
            You've analyzed data for a sales rep with the following results:
            
            {outputs_text}
            
            Create a comprehensive coaching plan, including:
            1. Specific strengths demonstrated by the rep
            2. Areas for improvement with concrete examples
            3. Actionable next steps for skill development
            4. Recommended training resources and timeline
            5. Metrics to track for measuring improvement
            
            Provide your coaching plan in a clear, constructive, and actionable format.
            """
            
            summary = await self.agno_agent.run(coaching_prompt)
            status = "success"
        else:
            summary = "Unable to complete sales coaching analysis due to tool failures."
            status = "failure"
        
        # Determine overall result status
        if all(s["status"] == "completed" for s in steps_executed):
            status = "success"
        elif any(s["status"] == "completed" for s in steps_executed):
            status = "partial_success"
        else:
            status = "failure"
        
        return {
            "task_id": plan["task_id"],
            "status": status,
            "summary": summary,
            "details": plan["thought_process"],
            "steps_executed": steps_executed,
            "tool_outputs": tool_outputs,
            "memory_items_created": [],  # Will be populated by run()
            "error": None if status != "failure" else "One or more coaching tools failed",
            "execution_time_seconds": 0  # Will be calculated by run()
        }
