from config import logger, sqs_client
from config import logger
from trading_view_extension.queue.sqs_queue_consumer_interface import IQueueConsumer


class SqsQueueConsumer(IQueueConsumer):
    """
    A simple SQS consumer class for receiving and deleting messages from a queue.
    """
    def __init__(self, max_messages=10, visibility_timeout=600, wait_time=5):
        """
        Args:
            max_messages: Max number of messages to fetch in one call.
            visibility_timeout: Time in seconds that the received messages are hidden.
            wait_time: Long polling wait time in seconds.
        """
        self.sqs_client = sqs_client  # Use the SQS client from config.py
        self.max_messages = max_messages
        self.visibility_timeout = visibility_timeout
        self.wait_time = wait_time
        logger.info("SqsQueueConsumer initialized")

    async def receive_messages(self, queue_url: str):
        """
        Fetch a batch of messages from SQS.
        Returns a list of dictionaries as received from SQS.
        """
        response = self.sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=self.max_messages,
            VisibilityTimeout=self.visibility_timeout,
            WaitTimeSeconds=self.wait_time,
            AttributeNames=["All"],
            MessageAttributeNames=["All"]
        )
        messages = response.get("Messages", [])
        logger.debug(f"Received {len(messages)} messages from {queue_url}")
        return messages

    async def delete_message(self, queue_url: str, message: dict):
        """
        Delete the given message from the queue to acknowledge successful processing.
        """
        receipt_handle = message.get("ReceiptHandle")
        if not receipt_handle:
            logger.warning(f"No receipt handle for message {message.get('MessageId')}")
            return
        self.sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logger.debug(f"Deleted message {message.get('MessageId')} from {queue_url}")
