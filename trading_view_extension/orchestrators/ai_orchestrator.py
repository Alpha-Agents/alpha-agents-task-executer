from config import logger
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
from trading_view_extension.services.alpha_agent_analyzer import analyze

class AiOrchestrator:
    def __init__(self, sqs_queue_publisher: SQSQueuePublisher):
        self.sqs_queue_publisher = sqs_queue_publisher
        logger.info("AiOrchestrator initialized.")

    async def handle_job(self, job):
        logger.info(f"Processing job: {job}")
        image_urls = job.get("s3_urls", [])

        if not isinstance(image_urls, list):
            raise ValueError("image_urls must be a list")

        max_retries = 1
        for attempt in range(max_retries):
            try:
                consensus_response, trade_signal, response_message_id = await analyze(job, image_urls)
                break
            except Exception as e:
                logger.warning(f"Retry {attempt+1}/{max_retries} failed for job {job}: {e}")
                if attempt == max_retries - 1:
                    consensus_response, trade_signal, response_message_id = "AI Error", "Unknown", "error"

        job["status"] = "COMPLETED"
        job["response"] = consensus_response
        job["result"] = trade_signal
        job["action_type"] = "processed"
        job["message_id"] = response_message_id

        await self.sqs_queue_publisher.publish_task(job)

        #Critical — Return Success Flag
        return True
