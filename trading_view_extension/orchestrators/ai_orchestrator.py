from config import logger
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
from trading_view_extension.orchestrators.task_executor import analyze_images
from trading_view_extension.orchestrators.gpt_client_sheets import GPTClient

class AiOrchestrator:
    # def __init__(self,sqs_queue_publisher : SQSQueuePublisher):
    #     self.sqs_queue_publisher = sqs_queue_publisher
    #     logger.info("AiOrchestrator initialized.")
    #     self.assistant_id = "asst_XEPZhRaGbY7gOlkJTVUq12En"
    #     self.openai_key = "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"

    # async def handle_job(self,job):
    #     logger.info(f"Job to process: {job}")
    #     analysis_result = analyze_images(self.assistant_id,job["s3_urls"],self.openai_key)
    #     job["status"] = "COMPLETED"
    #     job["action_type"] = "processed"
    #     job["result"] = analysis_result
    #     await self.sqs_queue_publisher.publish_task(job)

    def __init__(self, sqs_queue_publisher : SQSQueuePublisher):
        self.sqs_queue_publisher = sqs_queue_publisher
        logger.info("AiOrchestrator initialized.")
        self.gpt_client = GPTClient()  # Initialize GPTClient
        self.assistant_id = "asst_XEPZhRaGbY7gOlkJTVUq12En"  # Replace with actual ID

    async def handle_job(self, job):
        logger.info(f"Processing job: {job}")
        user_query = job.get("user_query", "Analyze this stock/crypto and provide a trade signal. Also, extract the name of the asset being analyzed.")
        asset = job.get("asset")
        user_query = f"""Extract the trade signal from this message.
                ONLY return a valid JSON object. **DO NOT** include markdown, explanations, or any extra text.
                the asset we are looking at is {asset}
                The response **MUST** match this exact format, replacing placeholders with actual values:

                {{
                    'asset': '<asset_name>',  '// Example: BTC'
                    'action': '<BUY/SELL/WAIT>',  '// Choose one based on analysis'
                    'current_price': '<current_price>',  '// Current price as a number'
                    'stop_loss': '<stop_loss>',  '// Stop loss price as a number'
                    'take_profit': '<take_profit>',  '// Take profit price as a number'
                    'confidence': '<confidence>',  '// Confidence level (1 to 10)'
                    'R2R': '<risk_to_reward_ratio>'  '// Risk to Reward Ratio (e.g., 1.5, 2.5)'
                }}

                DO NOT wrap the response in ```json or ``` marks. **JUST RETURN RAW JSON.**
                Replace placeholders with actual values from the trade analysis."""

        image_urls = job.get("s3_urls", [])
        response = self.gpt_client.ask_assistant(
            assistant_id=self.assistant_id,
            user_text=user_query,
            image_urls=image_urls,
            combined=True
        )

        job["status"] = "COMPLETED"
        job["result"] = response
        job["action_type"] = "processed"
        await self.sqs_queue_publisher.publish_task(job)

