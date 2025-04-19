"""
Memory Consistency Audit Workflow.

This module contains workflow definitions for auditing and reconciling memory
systems. Activities are defined separately in memory_audit_activities.py.
"""

import time
import logging
import datetime
from typing import Dict, Any, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

from orchestrator.workflows.memory_audit_activities import (
    count_redis_keys,
    count_firestore_documents,
    count_vector_embeddings,
    detect_orphaned_vectors,
    detect_missing_embeddings,
    detect_expired_sessions,
    cleanup_orphaned_vectors,
    cleanup_expired_conversations,
    generate_reconciliation_report,
    store_audit_report
)

# Set up logging
logger = logging.getLogger(__name__)


@workflow.defn
class MemoryAuditWorkflow:
    """
    Workflow for auditing and reconciling memory systems consistency.
    """
    
    @workflow.run
    async def run(self, perform_cleanup: bool = False) -> Dict[str, Any]:
        """
        Run the memory audit workflow.
        
        Args:
            perform_cleanup: Whether to clean up detected inconsistencies
            
        Returns:
            Audit report
        """
        # Define retry policy for activities
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=datetime.timedelta(seconds=1),
            maximum_interval=datetime.timedelta(seconds=10)
        )
        
        # Define standard activity options
        activity_options = {
            "start_to_close_timeout": datetime.timedelta(minutes=5),
            "retry_policy": retry_policy
        }
        
        # 1. Count keys in each memory system
        redis_counts = await workflow.execute_activity(
            count_redis_keys,
            **activity_options
        )
        
        firestore_counts = await workflow.execute_activity(
            count_firestore_documents,
            **activity_options
        )
        
        vector_counts = await workflow.execute_activity(
            count_vector_embeddings,
            **activity_options
        )
        
        # 2. Detect inconsistencies (extend timeout for these operations)
        inconsistency_options = activity_options.copy()
        inconsistency_options["start_to_close_timeout"] = datetime.timedelta(minutes=10)
        
        orphaned_vectors = await workflow.execute_activity(
            detect_orphaned_vectors,
            **inconsistency_options
        )
        
        missing_embeddings = await workflow.execute_activity(
            detect_missing_embeddings,
            **inconsistency_options
        )
        
        expired_sessions = await workflow.execute_activity(
            detect_expired_sessions,
            **activity_options
        )
        
        # 3. Clean up inconsistencies if requested
        cleanup_results = {}
        
        if perform_cleanup:
            # Clean up orphaned vectors
            orphaned_vector_ids = [v.get("vector_id") for v in orphaned_vectors if v.get("vector_id")]
            if orphaned_vector_ids:
                vectors_deleted = await workflow.execute_activity(
                    cleanup_orphaned_vectors,
                    orphaned_vector_ids,
                    **inconsistency_options
                )
                cleanup_results["vectors_deleted"] = vectors_deleted
            
            # Clean up expired sessions
            if expired_sessions:
                sessions_cleaned = await workflow.execute_activity(
                    cleanup_expired_conversations,
                    expired_sessions,
                    **inconsistency_options
                )
                cleanup_results["sessions_cleaned"] = sessions_cleaned
        
        # 4. Generate reconciliation report
        report = await workflow.execute_activity(
            generate_reconciliation_report,
            redis_counts,
            firestore_counts,
            vector_counts,
            orphaned_vectors,
            missing_embeddings,
            expired_sessions,
            **activity_options
        )
        
        # Add cleanup results to report if performed
        if perform_cleanup:
            report["cleanup_results"] = cleanup_results
        
        # 5. Store the report
        report_id = await workflow.execute_activity(
            store_audit_report,
            report,
            **activity_options
        )
        
        # Add report ID to report
        report["report_id"] = report_id
        
        return report


@workflow.defn
class ScheduledMemoryAuditWorkflow:
    """
    Scheduled workflow for periodic memory audits.
    """
    
    @workflow.run
    async def run(self, schedule_interval_hours: int = 24) -> None:
        """
        Run memory audits on a schedule.
        
        Args:
            schedule_interval_hours: Hours between audit runs
        """
        while True:
            # Get current timestamp for workflow ID
            timestamp = int(time.time())
            
            # Run the audit with automatic cleanup of expired sessions
            # but not orphaned vectors (which need manual review)
            report = await workflow.execute_child_workflow(
                MemoryAuditWorkflow.run,
                args=[True],  # perform_cleanup=True
                id=f"memory-audit-{timestamp}",
                task_queue="memory-audit-queue"
            )
            
            # Log completion
            workflow.logger.info(
                f"Completed scheduled memory audit. "
                f"Health status: {report.get('health_status', 'unknown')}"
            )
            
            # Sleep until next audit
            await workflow.sleep(datetime.timedelta(hours=schedule_interval_hours))


# Helper functions for manual execution

def start_memory_audit(client, task_queue="memory-audit-queue", perform_cleanup=False):
    """
    Start a memory audit workflow.
    
    Args:
        client: Temporal client
        task_queue: Task queue for the workflow
        perform_cleanup: Whether to perform automatic cleanup
        
    Returns:
        Workflow handle
    """
    workflow_id = f"memory-audit-{int(time.time())}"
    return client.start_workflow(
        MemoryAuditWorkflow.run,
        args=[perform_cleanup],
        id=workflow_id,
        task_queue=task_queue
    )


def start_scheduled_memory_audit(client, task_queue="memory-audit-queue", interval_hours=24):
    """
    Start a scheduled memory audit workflow.
    
    Args:
        client: Temporal client
        task_queue: Task queue for the workflow
        interval_hours: Hours between audit runs
        
    Returns:
        Workflow handle
    """
    workflow_id = f"scheduled-memory-audit-{int(time.time())}"
    return client.start_workflow(
        ScheduledMemoryAuditWorkflow.run,
        args=[interval_hours],
        id=workflow_id,
        task_queue=task_queue
    )
