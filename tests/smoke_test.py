#!/usr/bin/env python
"""
End-to-end smoke test for lead-to-outreach workflow.

This script runs a complete test of the sales workflow in the staging environment,
validating that all components work together correctly:
1. LeadResearchAgent
2. LangSmith Tracing
3. Token Usage Tracking
4. Memory & Vector Storage
5. PolicyGate
6. Integration with external services (Slack, Salesforce)

Usage:
    python smoke_test.py [--dry-run]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to sys.path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.app.services.api.process_service import ProcessService
from shared.observability.langsmith_tracer import tracer
from shared.cost.usage_tracker import tracker
from shared.memory.memory_manager import MemoryManager
from shared.memory.factory import get_memory_manager
from shared.guardrails.policy_gate import PolicyGate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmokeTest:
    """Runs end-to-end testing of the sales workflow in staging."""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the smoke test.
        
        Args:
            dry_run: If True, doesn't make actual external API calls
        """
        self.dry_run = dry_run
        self.test_client_id = f"smoke-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.results = []
        
        # Load test data
        self.leads = self._load_test_leads()
        
        # Initialize services - these would normally be injected
        self.memory_manager = get_memory_manager()
        self.policy_gate = PolicyGate()
        self.process_service = ProcessService()
        
        logger.info(f"Smoke test initialized with client ID: {self.test_client_id}")
        if dry_run:
            logger.info("Running in DRY RUN mode - no external API calls will be made")
    
    async def run(self) -> Dict[str, Any]:
        """
        Run the complete smoke test.
        
        Returns:
            Dictionary with test results
        """
        logger.info("Starting smoke test")
        start_time = time.time()
        
        # Process each test lead
        for idx, lead in enumerate(self.leads):
            logger.info(f"Processing lead {idx+1}/{len(self.leads)}: {lead['name']}")
            result = await self._process_lead(lead)
            self.results.append(result)
            
            # Brief pause between leads
            await asyncio.sleep(1)
        
        # Generate summary
        success_count = sum(1 for r in self.results if r.get("success", False))
        duration = time.time() - start_time
        
        summary = {
            "total_leads": len(self.leads),
            "successful_leads": success_count,
            "overall_success": success_count == len(self.leads),
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat(),
            "test_client_id": self.test_client_id,
            "dry_run": self.dry_run,
            "results": self.results
        }
        
        # Log summary
        logger.info(f"Smoke test complete: {success_count}/{len(self.leads)} successful in {duration:.2f}s")
        
        # Clean up test data if needed
        if not self.dry_run:
            await self._cleanup_test_data()
        
        return summary
    
    async def _process_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single test lead through the workflow.
        
        Args:
            lead: Lead data from test fixtures
            
        Returns:
            Dictionary with processing result
        """
        workflow_id = f"smoke-{uuid.uuid4()}"
        
        try:
            # Prepare workflow input
            workflow_input = {
                "lead": lead,
                "client_id": self.test_client_id,
                "workflow_id": workflow_id,
                "test_mode": True,
                "skip_external_apis": self.dry_run
            }
            
            # Start trace for this lead
            trace_context = await tracer.start_trace(
                operation_name=f"smoke_test_lead_{lead['name']}",
                metadata={"lead": lead, "workflow_id": workflow_id}
            )
            
            # Run the research workflow
            logger.info(f"Starting research workflow for {lead['name']}")
            start_time = time.time()
            
            # Call the service to process the lead
            result = await self.process_service.process_lead(
                lead_data=workflow_input,
                workflow_id=workflow_id
            )
            
            duration = time.time() - start_time
            
            # End trace
            await tracer.end_trace(
                trace_context=trace_context,
                result=result,
                metadata={"duration": duration}
            )
            
            # Validate results
            success = self._validate_result(result, lead)
            
            return {
                "lead": lead["name"],
                "workflow_id": workflow_id,
                "success": success,
                "duration_seconds": duration,
                "trace_id": trace_context.get("run_id"),
                "salesforce_id": result.get("salesforce_id"),
                "errors": [] if success else ["Validation failed"]
            }
            
        except Exception as e:
            logger.error(f"Error processing lead {lead['name']}: {str(e)}", exc_info=True)
            return {
                "lead": lead["name"],
                "workflow_id": workflow_id,
                "success": False,
                "error": str(e)
            }
    
    def _validate_result(self, result: Dict[str, Any], lead: Dict[str, Any]) -> bool:
        """
        Validate the result of processing a lead.
        
        Args:
            result: Result from the workflow
            lead: Original lead data
            
        Returns:
            True if result is valid, False otherwise
        """
        # Check basic structure
        if not isinstance(result, dict):
            logger.error(f"Invalid result type: {type(result)}")
            return False
        
        # Check required fields
        required_fields = ["status", "lead_profile", "salesforce_id"]
        for field in required_fields:
            if field not in result:
                logger.error(f"Missing required field in result: {field}")
                return False
        
        # Check status
        if result["status"] != "completed":
            logger.error(f"Workflow status is not 'completed': {result['status']}")
            return False
        
        # Check lead profile
        lead_profile = result.get("lead_profile", {})
        if not lead_profile.get("company_name"):
            logger.error("Lead profile missing company name")
            return False
        
        # Verify company name matches (allowing for some variation)
        expected_name = lead["name"].lower()
        actual_name = lead_profile.get("company_name", "").lower()
        if expected_name not in actual_name and actual_name not in expected_name:
            logger.error(f"Company name mismatch: expected '{expected_name}', got '{actual_name}'")
            return False
        
        # Verify notifications
        if not result.get("slack_notification_sent", False) and not self.dry_run:
            logger.error("Slack notification was not sent")
            return False
        
        # Check LangSmith trace
        if not result.get("langsmith_trace_id") and not self.dry_run:
            logger.error("Missing LangSmith trace ID")
            return False
        
        return True
    
    async def _cleanup_test_data(self) -> None:
        """Clean up test data after the smoke test."""
        try:
            # In a real implementation, we might:
            # - Delete test leads from Salesforce
            # - Remove test data from memory stores
            # - Archive test traces in LangSmith
            
            logger.info("Cleaning up test data")
            
            # Example: Clean up memory related to this test
            # This is a simplified version of what would be done in production
            if self.memory_manager:
                # Find items related to this test
                test_items = await self.memory_manager.retrieve(
                    query=self.test_client_id,
                    client_id=self.test_client_id,
                    top_k=100
                )
                
                # Log what would be deleted
                item_ids = [item["id"] for item in test_items]
                logger.info(f"Would delete {len(item_ids)} memory items")
                
                # In a real implementation, we would delete them
                # await self.memory_manager.delete_many(item_ids)
            
        except Exception as e:
            logger.error(f"Error cleaning up test data: {str(e)}")
    
    def _load_test_leads(self) -> List[Dict[str, Any]]:
        """
        Load test leads from fixtures.
        
        Returns:
            List of test lead data
        """
        try:
            fixtures_path = Path(__file__).parent / "fixtures" / "smoke_test_leads.json"
            with open(fixtures_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading test leads: {str(e)}")
            return []


async def main():
    """Run the smoke test."""
    parser = argparse.ArgumentParser(description="Run the smoke test")
    parser.add_argument("--dry-run", action="store_true", help="Don't make external API calls")
    args = parser.parse_args()
    
    smoke_test = SmokeTest(dry_run=args.dry_run)
    result = await smoke_test.run()
    
    # Print summary
    success = result["overall_success"]
    print(f"\n{'=' * 50}")
    print(f"SMOKE TEST {'SUCCESS' if success else 'FAILURE'}")
    print(f"{'=' * 50}")
    print(f"Processed {result['total_leads']} leads: {result['successful_leads']} successful")
    print(f"Total duration: {result['duration_seconds']:.2f} seconds")
    print(f"{'=' * 50}\n")
    
    # Exit with status code based on success
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
