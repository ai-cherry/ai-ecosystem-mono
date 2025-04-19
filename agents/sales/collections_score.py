"""
CollectionsScoringAgent implementation for AI sales pipeline.

This module defines the CollectionsScoringAgent class which analyzes accounts 
for collections risk and recommends payment collection strategies.
It extends the BaseSalesAgent abstract class.
"""

from typing import Any, Dict, List, Optional
import asyncio

from agents.base.sales_agent_base import BaseSalesAgent, AgentTask, AgentPlan, AgentResult, MemoryItem
from shared.memory.memory_manager import MemoryManager

class CollectionsScoringAgent(BaseSalesAgent):
    """
    Agent for analyzing accounts receivable and scoring collections risk.
    
    Capabilities:
    - Analyzes payment history and patterns
    - Calculates risk scores for accounts
    - Recommends collection strategies
    - Prioritizes accounts for follow-up
    """
    
    def __init__(
        self,
        memory: MemoryManager,
        accounting_db_connection: str = None,
        credit_api_key: str = None,
        payment_processor_api_key: str = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the CollectionsScoringAgent with required API credentials."""
        # Initialize tools
        tools = {}
        
        # Account analysis tool
        if accounting_db_connection:
            async def analyze_account(account_id: str) -> Dict[str, Any]:
                """Analyze payment history and current status of an account."""
                # In a real implementation, this would query an accounting database
                # Mocked for demonstration
                await asyncio.sleep(1)  # Simulate database query
                return {
                    "account_name": "Acme Corp",
                    "total_outstanding": 37500,
                    "aging": {
                        "current": 5000,
                        "30_days": 12500,
                        "60_days": 15000,
                        "90_plus_days": 5000
                    },
                    "payment_history": {
                        "avg_days_to_pay": 45,
                        "payment_frequency": "irregular",
                        "last_payment_date": "2025-03-15",
                        "last_payment_amount": 12500
                    },
                    "contact_info": {
                        "primary": "jane.doe@acmecorp.com",
                        "accounting": "ap@acmecorp.com"
                    }
                }
            
            tools["AnalyzeAccount"] = analyze_account
        
        # Credit risk assessment tool
        if credit_api_key:
            async def assess_credit_risk(company_name: str, tax_id: str = None) -> Dict[str, Any]:
                """Assess credit risk of a company using external credit API."""
                # In a real implementation, this would call a credit API
                # Mocked for demonstration
                await asyncio.sleep(1)  # Simulate API call
                return {
                    "credit_score": 72,
                    "risk_category": "medium",
                    "payment_index": 0.65,
                    "industry_avg_payment_index": 0.78,
                    "bankruptcy_risk": "low",
                    "suggested_credit_limit": 50000
                }
            
            tools["AssessCreditRisk"] = assess_credit_risk
        
        # Payment reminder tool
        if payment_processor_api_key:
            async def schedule_payment_reminder(
                account_id: str, 
                email: str, 
                amount: float, 
                due_date: str,
                template: str = "standard"
            ) -> Dict[str, Any]:
                """Schedule an automated payment reminder email."""
                # In a real implementation, this would call payment system API
                # Mocked for demonstration
                await asyncio.sleep(1)  # Simulate API call
                return {
                    "reminder_id": f"rem_{hash(account_id + email) % 10000}",
                    "scheduled_date": "2025-04-22T09:00:00Z",
                    "recipient": email,
                    "template_used": template,
                    "status": "scheduled"
                }
            
            tools["SchedulePaymentReminder"] = schedule_payment_reminder
        
        # Configure default storage policy for this agent
        merged_config = {
            "store_outputs_for_tools": ["AnalyzeAccount", "AssessCreditRisk"],
            **(config or {})
        }
        
        super().__init__(
            name="collections_score_agent",
            role="Collections Risk Analyst",
            description="Analyzes accounts receivable and recommends collection strategies",
            memory=memory,
            tools=tools,
            config=merged_config
        )
    
    async def plan(self, task: AgentTask, context: List[MemoryItem]) -> AgentPlan:
        """
        Create a collection analysis plan for an account.
        
        Args:
            task: The collections scoring task
            context: Relevant memory items
            
        Returns:
            A structured collection analysis plan
        """
        self.logger.info(f"Planning collections analysis for task {task['id']}")
        
        # Format context for the agent
        context_text = "\n".join([
            f"--- Context Item {i+1} ---\n{item['text']}\n"
            for i, item in enumerate(context)
        ])
        
        # Extract account details from task parameters
        collections_params = task["parameters"]
        account_id = collections_params.get("account_id", "")
        company_name = collections_params.get("company_name", "")
        tax_id = collections_params.get("tax_id", "")
        
        # Construct prompt for planning
        prompt = f"""
        You are a Collections Risk Analyst tasked with the following:
        
        Task: {task['description']}
        
        Account ID: {account_id}
        Company Name: {company_name}
        Tax ID: {tax_id}
        
        Here is relevant context from our system:
        {context_text}
        
        Available tools:
        1. AnalyzeAccount - Analyzes payment history and current status of an account
        2. AssessCreditRisk - Assesses credit risk of a company using external credit API
        3. SchedulePaymentReminder - Schedules an automated payment reminder email
        
        Create a detailed step-by-step plan for analyzing this account and recommending collection strategies. For each step:
        1. Explain your thought process
        2. Identify which tool to use
        3. Specify the exact input for the tool
        4. Describe what you expect to learn from this step
        
        Structure your plan as a sequence of well-reasoned steps.
        """
        
        # Use Agno for chain-of-thought reasoning
        plan_response = await self.agno_agent.run(prompt)
        
        # Parse the response to extract steps
        steps = []
        thought_process = plan_response
        
        # Structured step extraction based on collections parameters
        step_id = 1
        
        # Analyze account if account_id is available
        if "AnalyzeAccount" in self.tools and account_id:
            steps.append({
                "step_id": step_id,
                "tool_name": "AnalyzeAccount",
                "input_args": {"account_id": account_id},
                "expected_output": "Payment history and current status of the account",
                "status": "pending",
                "output": None,
                "error": None
            })
            step_id += 1
        
        # Assess credit risk if company name is available
        if "AssessCreditRisk" in self.tools and company_name:
            steps.append({
                "step_id": step_id,
                "tool_name": "AssessCreditRisk",
                "input_args": {"company_name": company_name, "tax_id": tax_id},
                "expected_output": "Credit risk assessment for the company",
                "status": "pending",
                "output": None,
                "error": None
            })
            step_id += 1
        
        # We'll decide whether to schedule a payment reminder in the act phase
        # based on the results of the analysis
        
        return {
            "task_id": task["id"],
            "thought_process": thought_process,
            "steps": steps,
            "estimated_duration_seconds": 30 * len(steps)  # Rough estimate
        }
    
    async def act(self, plan: AgentPlan) -> AgentResult:
        """
        Execute the collections analysis plan and recommend strategies.
        
        Args:
            plan: The collections analysis plan to execute
            
        Returns:
            Results from analysis and recommendations
        """
        self.logger.info(f"Executing collections analysis plan for task {plan['task_id']}")
        
        steps_executed = []
        tool_outputs = {}
        account_data = None
        credit_risk_data = None
        
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
                if tool_name == "AnalyzeAccount":
                    account_data = result
                elif tool_name == "AssessCreditRisk":
                    credit_risk_data = result
                
                # Store result
                step_copy["status"] = "completed"
                step_copy["output"] = result
                tool_outputs[f"{tool_name}_{step['step_id']}"] = result
                
            except Exception as e:
                self.logger.error(f"Error executing {tool_name}: {str(e)}")
                step_copy["status"] = "failed"
                step_copy["error"] = str(e)
        
        # Conditionally add a step to schedule a payment reminder if needed
        if account_data and "SchedulePaymentReminder" in self.tools:
            # Check if account needs a payment reminder (> 30 days outstanding)
            if account_data.get("aging", {}).get("30_days", 0) > 0:
                step_id = len(steps_executed) + 1
                new_step = {
                    "step_id": step_id,
                    "tool_name": "SchedulePaymentReminder",
                    "input_args": {
                        "account_id": step["input_args"].get("account_id", ""),
                        "email": account_data.get("contact_info", {}).get("accounting", ""),
                        "amount": account_data.get("aging", {}).get("30_days", 0),
                        "due_date": "2025-04-30",  # Example date
                        "template": "friendly_reminder"
                    },
                    "expected_output": "Scheduled payment reminder confirmation",
                    "status": "in_progress",
                    "output": None,
                    "error": None
                }
                
                try:
                    # Execute the reminder scheduling
                    result = await self.tools["SchedulePaymentReminder"](**new_step["input_args"])
                    new_step["status"] = "completed"
                    new_step["output"] = result
                    tool_outputs[f"SchedulePaymentReminder_{new_step['step_id']}"] = result
                except Exception as e:
                    self.logger.error(f"Error scheduling payment reminder: {str(e)}")
                    new_step["status"] = "failed"
                    new_step["error"] = str(e)
                
                steps_executed.append(new_step)
        
        # Generate analysis and recommendations with Agno
        if any(s["status"] == "completed" for s in steps_executed):
            outputs_text = "\n\n".join([
                f"--- {s['tool_name']} Result ---\n{str(s['output'])}"
                for s in steps_executed if s["status"] == "completed"
            ])
            
            analysis_prompt = f"""
            You've analyzed an account with the following results:
            
            {outputs_text}
            
            Create a comprehensive collections analysis report, including:
            1. Account overview with key metrics
            2. Payment pattern analysis
            3. Risk assessment with probability of default
            4. Recommended collection strategy (standard follow-up, escalation, payment plan, etc.)
            5. Specific next steps with timeline
            
            Provide your analysis in a clear, structured format that could be presented to a collections manager.
            """
            
            summary = await self.agno_agent.run(analysis_prompt)
            status = "success"
        else:
            summary = "Unable to complete collections analysis due to tool failures."
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
            "error": None if status != "failure" else "One or more collections analysis tools failed",
            "execution_time_seconds": 0  # Will be calculated by run()
        }
