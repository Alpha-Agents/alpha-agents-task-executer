import asyncio
import json
from config import logger, input_tasks_queue
from trading_view_extension.queue.sqs_queue_consumer import SqsQueueConsumer
from trading_view_extension.orchestrators.ai_orchestrator import AiOrchestrator

class AnalysisWorker:
    """
    Microservice that consumes jobs from SQS and processes them.
    """
    def __init__(self, queue_consumer: SqsQueueConsumer, orchestrator: AiOrchestrator):
        """
        Args:
            queue_consumer: An instance of SqsQueueConsumer (or similar).
            orchestrator: Optional object to handle business logic (e.g., AI tasks).
        """
        self.queue_consumer = queue_consumer
        self.orchestrator = orchestrator
        logger.info("AnalysisWorker initialized")

    async def start_listening(self) -> None:
        queue_url = input_tasks_queue.url
        logger.info(f"AnalysisWorker listening on {queue_url}")

        while True:
            jobs = await self.queue_consumer.receive_messages(queue_url)
            logger.debug(f"Received {len(jobs)} jobs in input queue")

            for job in jobs:
                try:
                    await self.process_message(job)
                except Exception as exc:
                    logger.exception(f"Failed to process job {job.get('MessageId')}: {exc}")
                finally:
                    await self.queue_consumer.delete_message(queue_url, job)

            # This short pause gives control back to the event loop if no messages
            # (or after finishing current batch).
            await asyncio.sleep(1)

    async def process_message(self, job: dict) -> None:
        """
        Basic placeholder for job parsing or logging. Adapt to your needs.
        """
        msg_id = job.get("MessageId")
        logger.info(f"Processing job: {msg_id}")
        if self.orchestrator:
            data = json.loads(job.get("Body", "{}"))
            await self.orchestrator.handle_job(data)
