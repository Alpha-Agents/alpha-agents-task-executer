import asyncio
from services.openrouter_client import query_conversation, get_consensus
from services.structured_output_service import StructuredOutputService
from config import OBSERVATION_MODEL_NAME, logger

from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher

class Reasoner:
    def __init__(self, job, system_prompt, questions, image_urls):
        self.system_prompt = system_prompt
        self.questions = questions
        self.image_urls = image_urls
        self.job = job
        self.conversation_history = [{"role": "system", "content": system_prompt}]
        self.structured_service = StructuredOutputService()
        self.sqs_queue_publisher = SQSQueuePublisher()  # This makes Reasoner directly talk to SQS


    async def run_reasoning(self):
        if not self.image_urls:
            raise ValueError("No images provided for reasoning")

        for question in self.questions:
            self.conversation_history.append({"role": "user", "content": question})
            response = await self._query_with_retry(question)

            self.conversation_history.append({"role": "assistant", "content": response})

            # 💥 Immediately notify frontend (or any listener) via SQS
            self.job["question"] = question
            self.job["response"] = response
            self.job["status"] = "RUNNING"
            self.job["result"] = []
            await self.sqs_queue_publisher.publish_task(self.job)

        # Final Consensus Processing
        try:
            consensus_response = get_consensus(self.conversation_history)
        except Exception as e:
            logger.error(f"Consensus generation failed: {e}")
            consensus_response = "Consensus generation failed."

        trade_signal = self.structured_service.get_trade_signal(consensus_response, self.job["asset"])

        return consensus_response, trade_signal


    async def _query_with_retry(self, question, max_retries=3):
        for attempt in range(max_retries):
            try:
                if question == self.questions[0]:
                    response = await asyncio.to_thread(query_conversation, self.conversation_history, self.image_urls, specified_model=OBSERVATION_MODEL_NAME)
                else:
                    response = await asyncio.to_thread(query_conversation, self.conversation_history, self.image_urls)

                if response and response != "Error":
                    return response

                logger.warning(f"Invalid or empty response on attempt {attempt+1}")
            except Exception as e:
                logger.warning(f"Exception during query on attempt {attempt+1}: {e}")

        logger.error(f"All retries failed for question: {question}")
        return "AI Error: No valid response after retries"
