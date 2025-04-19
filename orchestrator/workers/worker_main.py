"""
Main entry point for the Temporal worker.

This module sets up and runs a Temporal worker that processes workflows and activities.
"""

import asyncio
import logging
from typing import List, Type

from temporalio.client import Client
from temporalio.worker import Worker

from orchestrator.app.core.config import settings
from orchestrator.workflows.sample import PlannerToolResponderWorkflow
from orchestrator.workflows.enhanced_workflow import (
    EnhancedProcessingWorkflow,
    process_with_llm_and_memory,
    retrieve_conversation_history
)

# Set up logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)


async def run_worker():
    """
    Connect to Temporal and run a worker to process activities.
    
    This worker connects to the Temporal server, registers workflows and activities,
    and processes tasks from the specified task queue.
    """
    logger.info(f"Connecting to Temporal at {settings.TEMPORAL_HOST_URL}")
    
    # Create client connected to server
    client = await Client.connect(
        settings.TEMPORAL_HOST_URL,
        namespace=settings.TEMPORAL_NAMESPACE
    )
    
    # Create a worker to process tasks from the task queue
    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[
            PlannerToolResponderWorkflow,
            EnhancedProcessingWorkflow
        ],
        activities=[
            process_with_llm_and_memory,
            retrieve_conversation_history
        ]
    )
    
    logger.info(f"Worker connected and listening on task queue: {settings.TEMPORAL_TASK_QUEUE}")
    
    # Start the worker
    await worker.run()


if __name__ == "__main__":
    """
    Entry point when running this module directly.
    
    Starts the worker process and keeps it running until terminated.
    """
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker stopped with error: {e}")
        raise
