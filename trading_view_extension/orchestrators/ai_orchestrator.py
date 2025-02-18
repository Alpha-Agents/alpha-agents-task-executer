from config import logger
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
from trading_view_extension.orchestrators.task_executor import analyze_images
from trading_view_extension.orchestrators.gpt_client_sheets import GPTClient
from trading_view_extension.scripts.alpha_agent_analyzer import run_single_stock 

class AiOrchestrator:
    def __init__(self, sqs_queue_publisher : SQSQueuePublisher):
        self.sqs_queue_publisher = sqs_queue_publisher
        logger.info("AiOrchestrator initialized.")

    async def handle_job(self, job):
        logger.info(f"Processing job: {job}")
        # user_query = job.get("user_query", "Analyze this stock/crypto and provide a trade signal. Also, extract the name of the asset being analyzed.")
        asset = job.get("asset")
        image_urls = job.get("s3_urls", [])
        consensus_response, trade_signal = await run_single_stock(job, asset, image_urls)
        job["status"] = "COMPLETED"
        job["question"] = ""
        job["response"] = ""
        job["result"] = trade_signal
        job["action_type"] = "processed"
        await self.sqs_queue_publisher.publish_task(job)

