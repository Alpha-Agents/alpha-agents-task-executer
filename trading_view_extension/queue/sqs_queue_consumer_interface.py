from abc import ABC, abstractmethod
from typing import List, Optional

class IQueueConsumer(ABC):
    """
    An interface for queue consumers in Python.

    Concrete implementations (e.g., for SQS, RabbitMQ) should inherit from
    this class and implement the abstract methods.

    Typical usage pattern in your worker process:

        consumer = SomeConcreteQueueConsumer(...)
        while True:
            messages = consumer.receive_messages()
            for m in messages:
                # process the message
                # if successful:
                consumer.delete_message(m)
                # else: handle retries or errors
    """

    @abstractmethod
    def receive_messages(self):
        """
        Pull a batch of messages from the queue.

        Returns:
            A list of QueueMessage instances. The list could be empty if
            there are no messages available at the time of polling.
        """
        pass

    @abstractmethod
    def delete_message(self, message: any) -> None:
        """
        Permanently remove the specified message from the queue once processed.

        Args:
            message (QueueMessage): The message object to delete/acknowledge.

        This is typically required to signal the queue system that
        the message was successfully processed.
        """
        pass