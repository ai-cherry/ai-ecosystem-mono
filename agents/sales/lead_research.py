"""
LeadResearchAgent implementation for researching sales leads.

This agent is responsible for gathering information about potential leads,
analyzing their profile, and providing insights to the sales team.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from agents.base.sales_agent_base import BaseSalesAgent, AgentTask, AgentPlan, AgentResult, AgentStep
from shared.memory.memory_manager import MemoryManager

# Initialize logger
logger = logging.getLogger(__name__)


class LeadProfile(BaseModel):
    """Structured data about a sales lead."""
    company_name: str
    industry: str = Field(default="")
    size: str = Field(default="")  # e.g., "50-200 employees"
    location: str = Field(default="")
    founded_year: Optional[int] = None
    funding: Optional[str] = None
    
    # Key people
    ceo: Optional[str] = None
    decision_makers: List[Dict[str, str]] = Field(default_factory=list)  # [{name, title, contact}]
    
    # Contact info
    website: str = Field(default="")
    phone: Optional[str] = None
    email: Optional[str] = None
    
    # Business intelligence
    recent_news: List[str] = Field(default_factory=list)
    technologies_used: List[str] = Field(default_factory=list)
    competitors: List[str] = Field(default_factory=list)
    pain_points: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    
    # Agent analysis
    summary: str = Field(default="")
    engagement_strategy: str = Field(default="")
    estimated_deal_size: str = Field(default="")
    probability: float = Field(default=0.0)  # 0.0 to 1.0


class LeadResearchAgent(BaseSalesAgent):
    """
    Agent that researches potential leads for sales opportunities.
    
    This agent gathers information from various sources, analyzes the data,
    and provides insights to help sales teams prioritize and approach leads
    effectively.
    """
    
    def __init__(
        self,
        memory: MemoryManager,
        tools: Dict[str, Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the lead research agent.
        
        Args:
            memory: MemoryManager for agent memory access
            tools: Dictionary of tools available to the agent
            config: Configuration options
        """
        super().__init__(
            name="lead_research_agent",
            role="Lead Research Specialist",
            description="Researches leads and provides insights for sales opportunities",
            memory=memory,
            tools=tools or {},
            config=config or {}
        )
        
        # Register research-specific tools if not provided
        if not tools:
            self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register default tools for lead research."""
        # These would be implemented as actual integrations in production
        self.tools.update({
            "search_company": self._search_company,
            "find_decision_makers": self._find_decision_makers,
            "get_company_news": self._get_company_news,
            "analyze_company_website": self._analyze_company_website,
            "extract_apollo_data": self._extract_apollo_data,
            "extract_linkedin_data": self._extract_linkedin_data
        })
        
        # Register tools with Agno
        for tool_name, tool_fn in self.tools.items():
            self.agno_tools[tool_name] = self._create_agno_tool(tool_name, tool_fn)
    
    async def plan(self, task: AgentTask, context: List[Any]) -> AgentPlan:
        """
        Create a research plan based on lead information.
        
        Args:
            task: The task to plan for
            context: Relevant memory items for context
            
        Returns:
            A structured plan with steps to execute
        """
        # Extract lead information from task parameters
        lead_data = task["parameters"].get("lead", {})
        lead_name = lead_data.get("name", "")
        
        if not lead_name:
            raise ValueError("Lead name is required in task parameters")
        
        # Build the system prompt for the planning phase
        system_prompt = f"""
        You are a lead research specialist tasked with creating a detailed research plan for {lead_name}.
        Based on the initial information, create a step-by-step plan to gather comprehensive information about this lead.
        
        Your plan should include steps to:
        1. Gather basic company information (size, industry, location, funding)
        2. Identify key decision makers
        3. Find recent company news and developments
        4. Analyze the company's online presence
        5. Identify potential pain points and opportunities
        6. Synthesize findings into actionable insights for the sales team
        
        For each step, specify which tool to use and what information to look for.
        """
        
        # Extract any relevant information from memory context
        context_summary = self._summarize_context(context)
        
        # Create user prompt that includes the lead data and context
        user_prompt = f"""
        Create a research plan for: {lead_name}
        
        Initial information:
        {self._format_lead_data(lead_data)}
        
        Context from memory:
        {context_summary}
        
        Provide a detailed step-by-step plan using the available tools:
        - search_company: Search for basic company information
        - find_decision_makers: Find key people at the company
        - get_company_news: Get recent news about the company
        - analyze_company_website: Extract information from company website
        - extract_apollo_data: Extract data from Apollo.io
        - extract_linkedin_data: Extract data from LinkedIn
        """
        
        # Use the Agno agent to generate a plan
        plan_response = await self.agno_agent.generate(
            system=system_prompt,
            user=user_prompt
        )
        
        # Parse the response into structured steps
        steps = self._parse_plan_to_steps(plan_response, task["id"])
        
        # Create the structured plan
        plan = {
            "task_id": task["id"],
            "thought_process": plan_response,
            "steps": steps,
            "estimated_duration_seconds": len(steps) * 60  # Rough estimate: 1 minute per step
        }
        
        # Log the plan
        logger.info(f"Created research plan for {lead_name} with {len(steps)} steps")
        
        return plan
    
    async def act(self, plan: AgentPlan) -> AgentResult:
        """
        Execute a research plan and gather information about a lead.
        
        Args:
            plan: The plan to execute
            
        Returns:
            Research results and lead profile
        """
        task_id = plan["task_id"]
        start_time = self.agno_agent.get_current_time()
        steps_executed = []
        tool_outputs = {}
        memory_items_created = []
        
        try:
            # Execute each step in the plan
            for step in plan["steps"]:
                logger.info(f"Executing step {step['step_id']}: {step['tool_name']}")
                
                # Update step status
                step["status"] = "in_progress"
                
                try:
                    # Get the tool function
                    tool_fn = self.tools.get(step["tool_name"])
                    if not tool_fn:
                        raise ValueError(f"Tool not found: {step['tool_name']}")
                    
                    # Execute the tool
                    result = await tool_fn(**step["input_args"])
                    
                    # Update step with result
                    step["status"] = "completed"
                    step["output"] = result
                    tool_outputs[f"{step['tool_name']}_{step['step_id']}"] = result
                    
                except Exception as e:
                    # Handle step failure
                    logger.error(f"Error executing step {step['step_id']}: {str(e)}")
                    step["status"] = "failed"
                    step["error"] = str(e)
                
                # Add step to executed steps
                steps_executed.append(step)
            
            # Synthesize the results into a lead profile
            lead_profile = await self._synthesize_lead_profile(tool_outputs, task_id)
            
            # Store the lead profile in memory
            profile_id = await self.memory.store(
                text=f"Lead profile for {lead_profile.company_name}",
                metadata={
                    "type": "lead_profile",
                    "task_id": task_id,
                    "company_name": lead_profile.company_name,
                    "lead_profile": lead_profile.dict()
                }
            )
            memory_items_created.append(profile_id)
            
            # Calculate execution time
            execution_time = self.agno_agent.get_current_time() - start_time
            
            # Create success result
            result = {
                "task_id": task_id,
                "status": "success",
                "summary": f"Completed research on {lead_profile.company_name}",
                "details": lead_profile.dict(),
                "steps_executed": steps_executed,
                "tool_outputs": tool_outputs,
                "memory_items_created": memory_items_created,
                "error": None,
                "execution_time_seconds": execution_time
            }
            
            return result
            
        except Exception as e:
            # Handle overall execution failure
            logger.error(f"Error executing research plan: {str(e)}")
            
            # Calculate execution time
            execution_time = self.agno_agent.get_current_time() - start_time
            
            # Create failure result
            return {
                "task_id": task_id,
                "status": "failure",
                "summary": f"Failed to complete research: {str(e)}",
                "details": "",
                "steps_executed": steps_executed,
                "tool_outputs": tool_outputs,
                "memory_items_created": memory_items_created,
                "error": str(e),
                "execution_time_seconds": execution_time
            }
    
    async def _synthesize_lead_profile(self, tool_outputs: Dict[str, Any], task_id: str) -> LeadProfile:
        """
        Synthesize research results into a structured lead profile.
        
        Args:
            tool_outputs: Results from tool executions
            task_id: The task ID
            
        Returns:
            Structured lead profile
        """
        # Combine all tool outputs into a single context
        context = "\n\n".join([f"{key}:\n{value}" for key, value in tool_outputs.items()])
        
        # Create prompts for the LLM
        system_prompt = """
        You are a lead research analyst tasked with synthesizing information about a potential sales lead.
        Extract all relevant information and create a structured lead profile with the following information:
        - Company details (name, industry, size, location, founded year, funding)
        - Key people (CEO, decision makers with titles and contact info if available)
        - Contact information (website, phone, email)
        - Business intelligence (recent news, technologies used, competitors, pain points, opportunities)
        - Analysis (summary, suggested engagement strategy, estimated deal size, probability of success)
        
        Format your response as a structured JSON object matching the LeadProfile schema.
        """
        
        user_prompt = f"""
        Synthesize the following research information into a structured lead profile:
        
        {context}
        
        Return only the JSON object matching the LeadProfile schema.
        """
        
        # Generate profile using the Agno agent
        profile_json = await self.agno_agent.generate(
            system=system_prompt,
            user=user_prompt
        )
        
        # Parse the JSON response (handling potential formatting issues)
        profile_dict = self._extract_json(profile_json)
        
        # Create the lead profile object
        return LeadProfile(**profile_dict)
    
    def _parse_plan_to_steps(self, plan_text: str, task_id: str) -> List[AgentStep]:
        """
        Parse the plan text into structured steps.
        
        Args:
            plan_text: The plan text from the LLM
            task_id: The task ID
            
        Returns:
            List of structured steps
        """
        steps = []
        step_id = 1
        
        # Basic parsing logic - in production, this would be more robust
        # Split by numbered lines (1., 2., etc.) or "Step N:"
        import re
        step_matches = re.findall(r'(?:(?:\d+\.)|(?:Step \d+:))(.*?)(?=(?:\d+\.)|(?:Step \d+:)|$)', plan_text, re.DOTALL)
        
        for step_text in step_matches:
            step_text = step_text.strip()
            if not step_text:
                continue
                
            # Try to extract tool name and input args
            tool_match = re.search(r'(?:use|using|execute|run|call)\s+(?:the\s+)?tool\s+[\'"]?([a-zA-Z_]+)[\'"]?', step_text, re.IGNORECASE)
            tool_name = tool_match.group(1) if tool_match else "search_company"  # Default tool
            
            # Extract input args based on tool name
            input_args = {}
            if tool_name == "search_company":
                company_match = re.search(r'(?:company|organization|business)\s+[\'"]?([^\'"\n]+)[\'"]?', step_text, re.IGNORECASE)
                if company_match:
                    input_args["company_name"] = company_match.group(1).strip()
            elif tool_name == "find_decision_makers":
                company_match = re.search(r'(?:company|organization|business)\s+[\'"]?([^\'"\n]+)[\'"]?', step_text, re.IGNORECASE)
                if company_match:
                    input_args["company_name"] = company_match.group(1).strip()
                    input_args["roles"] = ["CEO", "CTO", "CFO", "VP"]  # Default roles
            elif tool_name == "extract_apollo_data" or tool_name == "extract_linkedin_data":
                company_match = re.search(r'(?:company|organization|business)\s+[\'"]?([^\'"\n]+)[\'"]?', step_text, re.IGNORECASE)
                if company_match:
                    input_args["company_name"] = company_match.group(1).strip()
            
            # Create the step
            step = {
                "step_id": step_id,
                "tool_name": tool_name,
                "input_args": input_args,
                "expected_output": f"Information about the lead from {tool_name}",
                "status": "pending",
                "output": None,
                "error": None
            }
            
            steps.append(step)
            step_id += 1
        
        # If no steps were parsed, create a default step
        if not steps:
            steps.append({
                "step_id": 1,
                "tool_name": "search_company",
                "input_args": {"company_name": "unknown"},
                "expected_output": "Basic company information",
                "status": "pending",
                "output": None,
                "error": None
            })
        
        return steps
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON object from text that might contain other content.
        
        Args:
            text: Text that may contain a JSON object
            
        Returns:
            Extracted JSON as dict, or empty dict if no valid JSON found
        """
        import json
        import re
        
        # Try to find a JSON object in the text
        json_match = re.search(r'({[\s\S]*})', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Fallback to creating a basic structure
        return {
            "company_name": "Unknown",
            "industry": "",
            "summary": "Could not extract profile from research data."
        }
    
    def _summarize_context(self, context: List[Any]) -> str:
        """
        Summarize memory context items into a string.
        
        Args:
            context: List of memory items
            
        Returns:
            Summary string
        """
        if not context:
            return "No prior context available."
        
        summary_parts = []
        for item in context:
            if hasattr(item, "text"):
                summary_parts.append(item.text)
            elif isinstance(item, dict) and "text" in item:
                summary_parts.append(item["text"])
        
        return "\n\n".join(summary_parts)
    
    def _format_lead_data(self, lead_data: Dict[str, Any]) -> str:
        """
        Format lead data as a string.
        
        Args:
            lead_data: Dictionary of lead data
            
        Returns:
            Formatted string
        """
        if not lead_data:
            return "No lead data provided."
        
        parts = []
        for key, value in lead_data.items():
            parts.append(f"{key}: {value}")
        
        return "\n".join(parts)
    
    # Tool implementations - these would be actual API integrations in production
    
    async def _search_company(self, company_name: str) -> str:
        """Search for basic company information."""
        # Mock implementation - would use actual search API
        return f"""
        Company: {company_name}
        Industry: Software
        Size: 50-200 employees
        Location: San Francisco, CA
        Founded: 2018
        Website: https://{company_name.lower().replace(' ', '')}.com
        """
    
    async def _find_decision_makers(self, company_name: str, roles: List[str] = None) -> str:
        """Find key decision makers at the company."""
        # Mock implementation - would use actual API
        roles = roles or ["CEO", "CTO"]
        
        decision_makers = [
            {"name": "Jane Smith", "title": "CEO", "contact": "jane@example.com"},
            {"name": "John Johnson", "title": "CTO", "contact": "john@example.com"}
        ]
        
        return "\n".join([f"{dm['name']} - {dm['title']} ({dm['contact']})" for dm in decision_makers])
    
    async def _get_company_news(self, company_name: str) -> str:
        """Get recent news about the company."""
        # Mock implementation - would use actual news API
        return f"""
        Recent news for {company_name}:
        1. Announced new product launch (2 weeks ago)
        2. Hired new VP of Sales (1 month ago)
        3. Opened new office in Austin (3 months ago)
        """
    
    async def _analyze_company_website(self, website: str) -> str:
        """Extract information from company website."""
        # Mock implementation - would use actual web scraping
        return f"""
        Website analysis for {website}:
        - Main products: Cloud software, data analytics
        - Technologies: React, Node.js, AWS
        - Key messaging: "Transforming businesses with AI"
        - Careers page shows 15 open positions
        """
    
    async def _extract_apollo_data(self, company_name: str) -> str:
        """Extract data from Apollo.io."""
        # Mock implementation - would integrate with Apollo API
        return f"""
        Apollo data for {company_name}:
        Industry: Enterprise Software
        Size: 120 employees
        Revenue: $10-50M
        Technologies: AWS, React, Python
        Key people:
        - Jane Smith (CEO) - jane@example.com
        - Mark Johnson (CTO) - mark@example.com
        - Sarah Williams (VP Sales) - sarah@example.com
        """
    
    async def _extract_linkedin_data(self, company_name: str) -> str:
        """Extract data from LinkedIn."""
        # Mock implementation - would integrate with LinkedIn
        return f"""
        LinkedIn data for {company_name}:
        About: {company_name} is a leading provider of enterprise software solutions.
        Founded: 2018
        Employees: 120
        Headquarters: San Francisco, CA
        Specialties: Cloud Computing, Enterprise Software, AI
        Recent posts:
        - Announced Series B funding of $30M
        - Launched new product feature
        - Highlighted customer success story
        """
    
    def _create_agno_tool(self, name: str, func: Any) -> Any:
        """
        Create an Agno tool from a function.
        
        Args:
            name: Name of the tool
            func: Function to wrap
            
        Returns:
            Agno tool object
        """
        from agno.utils import AgnoTool
        
        # Create a description based on docstring
        description = func.__doc__ or f"Tool for {name}"
        
        # Return Agno tool
        return AgnoTool(
            name=name,
            description=description,
            fn=func
        )
