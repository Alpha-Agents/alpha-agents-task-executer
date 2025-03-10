import asyncio
from services.openrouter_client import query_conversation, get_consensus, query_openrouter
from services.structured_output_service import StructuredOutputService
from config import OBSERVATION_MODEL_NAME, logger, CONSENSUS_MODEL
from database.db_utilities import get_conversation_by_id, add_message, add_conversation, conversation_exists
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
import uuid


class Reasoner:
    def __init__(self, job, system_prompt, image_urls=None, questions=None,message_id=None):
        self.system_prompt = system_prompt
        self.questions = questions
        self.image_urls = image_urls or job.get('s3_urls', [])  # Use images from job if not explicitly provided
        self.job = job
        self.conversation_history = [{"role": "system", "content": system_prompt}]
        self.message_id = message_id
        self.structured_service = StructuredOutputService()
        self.sqs_queue_publisher = SQSQueuePublisher()  # This makes Reasoner directly talk to SQS

    async def run_reasoning(self, is_consensus=True):
        if self.job['status'] == "PENDING":
            if not conversation_exists(self.job['job_id']):
                add_conversation(self.job['job_id'], [])
                add_message(self.job['job_id'], {
                    "message_id": uuid.uuid4().hex,
                    "role": "system",
                    "content": self.system_prompt
                })
            else:
                logger.info(f"Conversation already exists for job_id {self.job['job_id']}, skipping creation.")

        self.conversation_history = get_conversation_by_id(self.job["job_id"])
        user_instructions = self.job.get('user_instructions', '').strip()

        combined_content = []
        if user_instructions:
            combined_content.append({
                "type": "text",
                "text": f"User Instructions: {user_instructions}"
            })
        if self.image_urls:
            for url in self.image_urls:
                combined_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
        self.conversation_history.append({
            "role": "user",
            "content": combined_content
        })
        add_message(self.job['job_id'], {
            "message_id": uuid.uuid4().hex,
            "role": "user",
            "content": combined_content  # Store the combined list directly in the DB
        })

        consensus_response = None

        if is_consensus:
            consensus_messages = self._prepare_consensus_messages()

            # Call OpenRouter for consensus
            consensus_response = await query_openrouter(consensus_messages, specified_model=CONSENSUS_MODEL)

            # Save the assistant's consensus response in the history
            self.conversation_history.append({
                "role": "assistant",
                "content": consensus_response
            })
            response_message_id = uuid.uuid4().hex
            add_message(self.job['job_id'], {
                "message_id": response_message_id,
                "role": "assistant",
                "content": consensus_response
            })

        trade_signal_result = None
        if self.job['status'] == "PENDING":
            text_to_analyze = consensus_response if consensus_response else self.conversation_history[-1]["content"]
            trade_signal_result = self.structured_service.get_trade_signal(text_to_analyze, self.job["asset"])

        return consensus_response, trade_signal_result, response_message_id

    def _prepare_consensus_messages(self):
        """
        Prepares conversation history for consensus request.
        - Removes `message_id` if present.
        - Ensures it ends with a user message.
        - Removes the final assistant message if necessary.
        - Attaches images and user instructions if they exist.
        """
        consensus_messages = []

        for msg in self.conversation_history:
            content = msg.get("content")
            if isinstance(content, dict) and "text" in content:
                content = content["text"]

            consensus_messages.append({
                "role": msg["role"],
                "content": [{"type": "text", "text": content}]
            })

        if self.image_urls:
            for i in range(len(consensus_messages) - 1, -1, -1):
                if consensus_messages[i]["role"] == "user":
                    for url in self.image_urls:
                        consensus_messages[i]["content"].append(
                            {"type": "image_url", "image_url": {"url": url}}
                        )
                    break

        while consensus_messages and consensus_messages[-1]["role"] == "assistant":
            consensus_messages.pop()

        if not consensus_messages or consensus_messages[-1]["role"] != "user":
            for i in range(len(consensus_messages) - 1, -1, -1):
                if consensus_messages[i]["role"] == "user":
                    user_msg = consensus_messages.pop(i)
                    consensus_messages.append(user_msg)
                    break

        return consensus_messages
