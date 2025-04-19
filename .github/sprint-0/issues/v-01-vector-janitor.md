# V-01 VectorJanitor Nightly Workflow

## What & Why
As our vector database grows with embeddings from agent operations, we need to maintain its quality and efficiency. The VectorJanitor will run as a scheduled process to identify and remove duplicate and orphaned vectors, ensuring the system remains performant.

This task involves implementing a complete VectorJanitor workflow that will run on a nightly basis via Temporal, send Slack notifications about its operations, and maintain the health of our vector stores.

## Acceptance Criteria
- [ ] Create a `VectorJanitor` class in a new `shared/memory/vector_janitor.py` file
- [ ] Implement methods to:
  - [ ] Identify duplicate vectors (cosine similarity ≥ 0.98)
  - [ ] Identify orphaned vectors (no corresponding document in Firestore)
  - [ ] Safely purge identified vectors
  - [ ] Calculate space savings from cleanup
- [ ] Set up a Temporal workflow that:
  - [ ] Runs nightly via cron scheduling
  - [ ] Executes the VectorJanitor operations
  - [ ] Logs activities for monitoring
  - [ ] Handles failures gracefully
- [ ] Send a Slack notification with the summary:
  - [ ] Number of duplicates found and removed
  - [ ] Number of orphaned vectors purged
  - [ ] Storage space reclaimed (in KB)
  - [ ] Total operation time
- [ ] Create unit and integration tests
- [ ] Deploy to staging environment and verify operation

## Implementation Notes
- Consider a multi-phase approach:
  - Phase 1: Detection only (no deletion)
  - Phase 2: Detection + logging
  - Phase 3: Full cleanup with safeguards
- Add safeguards against mass deletion (e.g., max 5% of vectors in one run)
- Implement a dryrun mode for testing
- Use batching for performance when dealing with large vector sets
- Create a backup mechanism before deletion
- Consider ways to manually trigger the job if needed
- Implement detailed logging for audit purposes
- Add metrics for monitoring vector store health over time

## Example Workflow Structure
```python
@workflow.defn
class VectorJanitorWorkflow:
    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # Initialize activities
        janitor_activities = workflow.ActivityStub(
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(...)
        )
        
        # Run analysis phase
        analysis_result = await janitor_activities.analyze_vector_store(config)
        
        # Safety check
        if self._is_safe_to_proceed(analysis_result):
            # Proceed with cleanup
            cleanup_result = await janitor_activities.cleanup_vector_store(
                analysis_result["duplicates"],
                analysis_result["orphans"],
                config
            )
            
            # Send notification
            await janitor_activities.send_slack_notification(
                cleanup_result, config["notification_channel"]
            )
            
            return cleanup_result
        else:
            # Log warning and exit
            workflow.logger.warning("Vector cleanup exceeded safety thresholds")
            await janitor_activities.send_alert(
                "Vector janitor safety thresholds exceeded", 
                config["alert_channel"]
            )
            return {"status": "aborted", "reason": "safety_threshold"}
```

## Related Files
- New implementation: `shared/memory/vector_janitor.py`
- Temporal workflow: `orchestrator/workflows/vector_janitor_workflow.py`
- Integration with: `shared/memory/vectorstore.py` and `shared/memory/memory_manager.py`
- Test file: `tests/vector_janitor_test.py`
- Notification utility: `shared/utils/slack_notifier.py`
