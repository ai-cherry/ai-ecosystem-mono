# E-01 Staging Smoke-Run

## What & Why
Before releasing our system to production, we need to verify that the end-to-end workflow functions correctly in the staging environment. This ticket involves creating and executing a smoke test that runs a complete lead-to-outreach workflow with dummy data, confirming that all components are integrated properly.

This will serve as our final validation that all Sprint-0 components work together as expected, ensuring a smooth path to production deployment.

## Acceptance Criteria
- [ ] Create a smoke test script that:
  - [ ] Sets up 3 dummy leads with test data
  - [ ] Executes the complete workflow from lead research to outreach
  - [ ] Validates all steps complete successfully
  - [ ] Verifies integration with external systems
- [ ] Confirm successful execution generates:
  - [ ] Slack notification with workflow summary
  - [ ] Salesforce lead note update
  - [ ] Complete LangSmith trace of the execution
- [ ] Document any manual setup required for the test
- [ ] Create a runbook for executing this test in future sprints
- [ ] All test runs pass in the staging environment

## Implementation Notes
- Create a standalone script that can be executed via CLI
- Use deterministic test data to ensure reproducibility
- Mock external APIs where appropriate, but use real integrations for:
  - Slack notifications
  - LangSmith tracing
  - Memory systems
- Implement proper cleanup to avoid test data pollution
- Add detailed logging throughout the test for debugging
- Consider implementing as a Temporal workflow for easier management
- Include timing metrics to monitor performance

## Example Test Structure
```python
async def run_smoke_test():
    """Run end-to-end smoke test for the lead-to-outreach flow."""
    
    # 1. Set up test data
    test_leads = [
        {"name": "Acme Corp", "website": "acme-test.example.com", "contact": "john.doe@example.com"},
        {"name": "Beta Industries", "website": "beta-test.example.com", "contact": "jane.smith@example.com"},
        {"name": "Gamma Services", "website": "gamma-test.example.com", "contact": "sam.wilson@example.com"}
    ]
    
    results = []
    for lead in test_leads:
        # 2. Initialize workflow
        workflow_id = f"smoke-test-{uuid.uuid4()}"
        workflow_input = {
            "lead": lead,
            "client_id": "smoke-test-client",
            "test_mode": True
        }
        
        # 3. Execute workflow
        try:
            result = await orchestrator.run_workflow(
                "lead_research_to_outreach", 
                workflow_input,
                workflow_id=workflow_id
            )
            
            # 4. Validate results
            assert result["status"] == "completed"
            assert "lead_profile" in result
            assert "salesforce_id" in result
            assert "slack_notification_sent" in result and result["slack_notification_sent"]
            assert "langsmith_trace_id" in result
            
            # 5. Store result for reporting
            results.append({
                "lead": lead["name"],
                "success": True,
                "duration": result["duration_seconds"],
                "trace_id": result["langsmith_trace_id"]
            })
            
        except Exception as e:
            results.append({
                "lead": lead["name"],
                "success": False,
                "error": str(e)
            })
    
    # 6. Generate summary report
    success_count = sum(1 for r in results if r["success"])
    print(f"Smoke test complete: {success_count}/{len(test_leads)} successful")
    
    return {
        "overall_success": success_count == len(test_leads),
        "results": results
    }
```

## Related Files
- Test script: `tests/smoke_test.py`
- Workflow: `orchestrator/workflows/lead_to_outreach.py`
- Configuration: `tests/config/smoke_test_config.py`
- Test data: `tests/fixtures/smoke_test_leads.json`
- Documentation: `docs/smoke_test_runbook.md`
