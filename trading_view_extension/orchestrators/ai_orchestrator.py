from config import logger
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
from trading_view_extension.scripts.alpha_agent_analyzer import run_single_stock

class AiOrchestrator:
    def __init__(self, sqs_queue_publisher: SQSQueuePublisher):
        self.sqs_queue_publisher = sqs_queue_publisher
        logger.info("AiOrchestrator initialized.")

    async def handle_job(self, job):
        logger.info(f"Processing job: {job}")

        asset = job.get("asset")
        image_urls = job.get("s3_urls", [])

        # ✅ Input Validation
        if not asset:
            raise ValueError("Missing asset in job")
        if not isinstance(image_urls, list):
            raise ValueError("image_urls must be a list")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                consensus_response, trade_signal = await run_single_stock(job, asset, image_urls)
                break
            except Exception as e:
                logger.warning(f"Retry {attempt+1}/{max_retries} failed for job {job}: {e}")
                if attempt == max_retries - 1:
                    consensus_response, trade_signal = "AI Error", "Unknown"

        job["status"] = "COMPLETED"
        job["question"] = ""
        job["response"] = ""
        job["result"] = trade_signal
        job["action_type"] = "processed"

        await self.sqs_queue_publisher.publish_task(job)

        # ✅ Critical — Return Success Flag
        return True
