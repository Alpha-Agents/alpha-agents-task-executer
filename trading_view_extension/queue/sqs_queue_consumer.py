import concurrent.futures
import asyncio
import json
import ssl
import threading
import time
from config import logger, sqs_client
from trading_view_extension.queue.sqs_queue_consumer_interface import IQueueConsumer
from trading_view_extension.orchestrators.ai_orchestrator import AiOrchestrator

class SqsQueueConsumer(IQueueConsumer):
    def __init__(self, sqs_queue_publisher, max_messages=5, visibility_timeout=300, wait_time=1):
        self.sqs_client = sqs_client
        self.sqs_queue_publisher = sqs_queue_publisher
        self.max_messages = max_messages
        self.visibility_timeout = visibility_timeout
        self.wait_time = wait_time

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)  # 5 workers, adjust if needed
        self.orchestrator = AiOrchestrator(self.sqs_queue_publisher)

        self.local_safe_store = {}  # Safe store for crash recovery (in-memory for now, can be moved to Redis)
        self.lock = threading.Lock()

        self.main_event_loop = asyncio.get_event_loop()

        self.shutdown_event = threading.Event()
        self.polling_thread = None

        logger.info("SqsQueueConsumer initialized with Immediate Delete + Safe Store strategy")

    def start_polling(self, queue_url: str):
        if self.polling_thread and self.polling_thread.is_alive():
            logger.warning("Polling thread already running, skipping duplicate start_polling() call.")
            return

        self.polling_thread = threading.Thread(target=self._polling_loop, args=(queue_url,), daemon=True)
        self.polling_thread.start()
        logger.info("Polling thread started.")

    def _polling_loop(self, queue_url: str):
        while not self.shutdown_event.is_set():
            messages = self.receive_messages(queue_url)

            for message in messages:
                self.executor.submit(self.safe_process_message, queue_url, message)

            time.sleep(0.5)  # Poll every 500ms, regardless of processing

    def safe_process_message(self, queue_url, message):
        message_id = message.get("MessageId")

        with self.lock:
            self.local_safe_store[message_id] = message  # Save message to safe store immediately

        try:
            # Delete message right away to avoid FIFO blocking
            asyncio.run(self.delete_message(queue_url, message))

            # Process message body (actual work)
            self.process_message_body(message)

            # If processing succeeds, remove from safe store
            with self.lock:
                self.local_safe_store.pop(message_id, None)

        except Exception as e:
            logger.error(f"Processing crashed for message {message_id}: {e}")
            logger.error(f"⚠️ Message {message_id} will stay in safe store for manual recovery.")

    def process_message_body(self, message: dict):
        message_id = message.get("MessageId")
        body = message.get("Body", "{}")

        logger.info(f"🚀 Processing message {message_id}")

        try:
            job_data = json.loads(body)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format in message {message_id}")
            return

        # future = asyncio.run_coroutine_threadsafe(self.orchestrator.handle_job(job_data), self.main_event_loop)
        # result = future.result(timeout=300)

        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        result = new_loop.run_until_complete(self.orchestrator.handle_job(job_data))
        new_loop.close()

        if result is None:
            raise ValueError(f"handle_job() returned None for message {message_id}")

        logger.info(f"handle_job() completed successfully for {message_id}, result: {result}")

    def receive_messages(self, queue_url: str):
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=self.max_messages,
                VisibilityTimeout=self.visibility_timeout,
                WaitTimeSeconds=self.wait_time,
                AttributeNames=["All"],
                MessageAttributeNames=["All"]
            )
        except ssl.SSLError as ssl_error:
            logger.error(f"SSL ERROR: {ssl_error}")
            return []
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            return []

        messages = response.get("Messages", [])
        for message in messages:
            logger.info(f"Received Message ID: {message.get('MessageId')}")
        return messages

    async def delete_message(self, queue_url: str, message: dict):
        receipt_handle = message.get("ReceiptHandle")
        if not receipt_handle:
            logger.warning(f"No receipt handle for message {message.get('MessageId')}")
            return
        try:
            await asyncio.to_thread(
                self.sqs_client.delete_message,
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info(f"Immediately deleted message {message.get('MessageId')} from {queue_url}")
        except Exception as e:
            logger.error(f"Failed to delete message {message.get('MessageId')}: {e}")

    def stop_polling(self):
        self.shutdown_event.set()
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        self.executor.shutdown(wait=True)
        logger.info("Stopped polling and shut down worker threads.")

    def replay_safe_store(self):
        logger.warning("Starting manual recovery from safe store (for crashed messages)")
        for message_id, message in list(self.local_safe_store.items()):
            try:
                self.process_message_body(message)
                with self.lock:
                    self.local_safe_store.pop(message_id, None)
                logger.info(f"Successfully recovered message {message_id}")
            except Exception as e:
                logger.error(f"Failed to recover message {message_id}: {e}")
