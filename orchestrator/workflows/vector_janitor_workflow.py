"""
Temporal workflow for running the VectorJanitor on a scheduled basis.

This module defines a Temporal workflow and activities that handle:
1. Scheduled nightly runs of the VectorJanitor
2. Safe cleanup of duplicate and orphaned vectors
3. Notifications about the cleanup results
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from shared.memory.vector_janitor import VectorJanitor
from shared.memory.memory_manager import MemoryManager
from shared.memory.vectorstore import VectorStore
from shared.memory.firestore import FirestoreMemory

# Initialize logger
logger = logging.getLogger(__name__)


@activity.defn
async def analyze_vector_store(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity to analyze the vector store for cleanup candidates.
    
    Args:
        config: Configuration parameters for the janitor
        
    Returns:
        Dictionary with analysis results
    """
    # Initialize janitor with config
    vector_janitor = await _create_janitor(config)
    
    # Run analysis
    try:
        analysis_results = await vector_janitor.analyze()
        logger.info(
            f"Vector store analysis complete: "
            f"{analysis_results['duplicates_found']} duplicates, "
            f"{analysis_results['orphans_found']} orphans found"
        )
        return analysis_results
    except Exception as e:
        logger.error(f"Error analyzing vector store: {str(e)}")
        raise


@activity.defn
async def cleanup_vector_store(
    duplicates: List[str],
    orphans: List[str],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Activity to clean up duplicates and orphans from vector store.
    
    Args:
        duplicates: List of duplicate vector IDs to remove
        orphans: List of orphan vector IDs to remove
        config: Configuration parameters for the janitor
        
    Returns:
        Dictionary with cleanup results
    """
    # Initialize janitor with config
    vector_janitor = await _create_janitor(config)
    
    # Run cleanup with pre-analyzed candidates
    try:
        cleanup_results = await vector_janitor.cleanup({
            "duplicates": duplicates,
            "orphans": orphans
        })
        
        logger.info(
            f"Vector store cleanup complete: "
            f"{cleanup_results['stats']['duplicates_removed']} duplicates, "
            f"{cleanup_results['stats']['orphans_removed']} orphans removed"
        )
        
        return cleanup_results
    except Exception as e:
        logger.error(f"Error cleaning up vector store: {str(e)}")
        raise


@activity.defn
async def send_slack_notification(results: Dict[str, Any], channel: str) -> Dict[str, Any]:
    """
    Activity to send notification about janitor results to Slack.
    
    Args:
        results: Cleanup results to report
        channel: Slack channel to send notification to
        
    Returns:
        Dictionary with notification status
    """
    # Mock implementation - would use a proper Slack client in production
    try:
        # Generate human-readable report
        stats = results.get("stats", {})
        
        # Format message
        duplicates_removed = stats.get("duplicates_removed", 0)
        orphans_removed = stats.get("orphans_removed", 0)
        kb_saved = stats.get("bytes_saved", 0) / 1024
        
        message = (
            f"*VectorJanitor Nightly Run Complete* :broom:\n\n"
            f"• *{duplicates_removed}* duplicates removed\n"
            f"• *{orphans_removed}* orphaned vectors purged\n"
            f"• *{kb_saved:.2f} KB* storage reclaimed\n\n"
            f"_Run time: {stats.get('operation_time_seconds', 0):.2f} seconds_"
        )
        
        # In a real implementation, we would call the Slack API here
        logger.info(f"Slack notification would be sent to {channel}: {message}")
        
        return {
            "success": True,
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error sending Slack notification: {str(e)}")
        raise


@activity.defn
async def send_alert(message: str, channel: str) -> Dict[str, Any]:
    """
    Activity to send alert about janitor issues to Slack.
    
    Args:
        message: Alert message
        channel: Slack channel to send alert to
        
    Returns:
        Dictionary with alert status
    """
    # Mock implementation - would use a proper Slack client in production
    try:
        # Format message
        alert_message = (
            f"*VectorJanitor Alert* :warning:\n\n"
            f"{message}\n\n"
            f"_Timestamp: {datetime.utcnow().isoformat()}_"
        )
        
        # In a real implementation, we would call the Slack API here
        logger.info(f"Slack alert would be sent to {channel}: {alert_message}")
        
        return {
            "success": True,
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error sending Slack alert: {str(e)}")
        raise


async def _create_janitor(config: Dict[str, Any]) -> VectorJanitor:
    """
    Create a VectorJanitor instance with the provided configuration.
    
    Args:
        config: Configuration parameters for the janitor
        
    Returns:
        Initialized VectorJanitor instance
    """
    # Extract config values with defaults
    similarity_threshold = config.get("similarity_threshold", 0.98)
    max_deletion_percentage = config.get("max_deletion_percentage", 5.0)
    dry_run = config.get("dry_run", False)
    
    # Initialize stores
    vector_store = VectorStore()  # Would use proper initialization in production
    firestore = FirestoreMemory()  # Would use proper initialization in production
    
    # Create janitor
    return VectorJanitor(
        vector_store=vector_store,
        firestore=firestore,
        similarity_threshold=similarity_threshold,
        max_deletion_percentage=max_deletion_percentage,
        dry_run=dry_run
    )


@workflow.defn
class VectorJanitorWorkflow:
    """Workflow that orchestrates the vector janitor operations."""

    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the vector janitor workflow.
        
        Args:
            config: Configuration parameters for the janitor
            
        Returns:
            Dictionary with workflow results
        """
        # Set default config if not provided
        if not config:
            config = {
                "similarity_threshold": 0.98,
                "max_deletion_percentage": 5.0,
                "dry_run": False,
                "notification_channel": "vector-store-monitoring",
                "alert_channel": "vector-store-alerts"
            }
        
        # Initialize retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=10),
            maximum_attempts=3,
            non_retryable_error_types=["ValueError"]
        )
        
        # Initialize activities
        janitor_activities = workflow.ActivityStub(
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=retry_policy
        )
        
        # Start timing
        start_time = workflow.now()
        
        try:
            # Step 1: Analyze vector store
            workflow.logger.info("Starting vector store analysis")
            analysis_result = await janitor_activities.execute(
                analyze_vector_store,
                config
            )
            
            # Step 2: Check if cleanup is needed
            total_candidates = analysis_result["deletion_candidates"]
            if total_candidates == 0:
                # No cleanup needed, send notification and exit
                await janitor_activities.execute(
                    send_slack_notification,
                    {"stats": {"duplicates_removed": 0, "orphans_removed": 0, "bytes_saved": 0}},
                    config["notification_channel"]
                )
                
                return {
                    "status": "completed",
                    "message": "No cleanup needed - no duplicates or orphans found",
                    "analysis": analysis_result
                }
            
            # Step 3: Safety check - make sure we're not deleting too much
            duplicates = analysis_result.get("duplicates", [])
            orphans = analysis_result.get("orphans", [])
            total_vectors = analysis_result.get("total_vectors", 0)
            
            if total_vectors > 0:
                deletion_percentage = (len(duplicates) + len(orphans)) / total_vectors * 100
                if deletion_percentage > config.get("max_deletion_percentage", 5.0):
                    # Safety threshold exceeded, send alert and exit
                    await janitor_activities.execute(
                        send_alert,
                        f"Safety threshold exceeded: {deletion_percentage:.2f}% of vectors would be deleted",
                        config["alert_channel"]
                    )
                    
                    return {
                        "status": "aborted",
                        "reason": "safety_threshold_exceeded",
                        "deletion_percentage": deletion_percentage,
                        "max_allowed_percentage": config.get("max_deletion_percentage", 5.0),
                        "analysis": analysis_result
                    }
            
            # Step 4: Perform cleanup
            workflow.logger.info(f"Starting vector store cleanup: {len(duplicates)} duplicates, {len(orphans)} orphans")
            cleanup_result = await janitor_activities.execute(
                cleanup_vector_store,
                duplicates,
                orphans,
                config
            )
            
            # Step 5: Send notification
            await janitor_activities.execute(
                send_slack_notification,
                cleanup_result,
                config["notification_channel"]
            )
            
            # Calculate duration
            end_time = workflow.now()
            duration = (end_time - start_time).total_seconds()
            
            # Return final results
            return {
                "status": "completed",
                "cleanup": cleanup_result,
                "analysis": analysis_result,
                "duration_seconds": duration
            }
            
        except Exception as e:
            # Send alert about failure
            try:
                await janitor_activities.execute(
                    send_alert,
                    f"VectorJanitor workflow failed: {str(e)}",
                    config["alert_channel"]
                )
            except Exception:
                # Ignore errors in sending the alert
                pass
                
            # Re-raise the exception
            raise
