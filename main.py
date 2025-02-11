import asyncio
import threading
import os
from config import logger, input_tasks_queue
from trading_view_extension.queue.sqs_queue_consumer import SqsQueueConsumer
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
from trading_view_extension.workers.analysis_worker import AnalysisWorker
from trading_view_extension.orchestrators.ai_orchestrator import AiOrchestrator
from thread_manager import ThreadManager

async def main():
    # Initialize dependencies
    iqp = SQSQueuePublisher()
    sqs_consumer = SqsQueueConsumer()
    ai_orchestrator = AiOrchestrator(iqp)
    analysis_worker = AnalysisWorker(
        queue_consumer=sqs_consumer,
        orchestrator=ai_orchestrator
    )

    queue_url = input_tasks_queue.url
    logger.info(f"AnalysisWorker listening on {queue_url}")

    # Create a ThreadManager to spawn and track threads
    thread_manager = ThreadManager()

    while True:
        # Poll SQS asynchronously
        jobs = await sqs_consumer.receive_messages(queue_url)

        if jobs:
            logger.debug(f"Received {len(jobs)} jobs in input queue")

        # For each job, wait until there's capacity based on the dynamic CPU count check
        for job in jobs:
            while thread_manager.active_thread_count() >= (
                (os.cpu_count() or 1) - 2 if (os.cpu_count() or 1) > 2 else 1
            ):
                logger.debug("Not enough available system threads, waiting for one to free up...")
                await asyncio.sleep(0.1)
            thread_manager.start_thread(analysis_worker, sqs_consumer, queue_url, job)

        # A small sleep to avoid hammering SQS if it's empty
        await asyncio.sleep(1)


if __name__ == "__main__":
    logger.info("Starting standalone ResponseWorker with dynamic threads (no fixed pool).")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt: shutting down ResponseWorker.")

    logger.info("All done.")
