import json
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict

class QueueMessage:
    """
    Data holder for a single queue message.
    """
    def __init__(self,
                 message_id: str,
                 body: str,
                 receipt_handle: Optional[str] = None,
                 attributes: Optional[dict] = None):
        self.message_id = message_id
        self.body = body
        self.receipt_handle = receipt_handle
        self.attributes = attributes or {}


class IQueuePublisher(ABC):
    @abstractmethod
    async def publish_task(self, job: dict) -> None:
        pass


class IQueueConsumer(ABC):
    @abstractmethod
    async def receive_messages(self, queue_name: str) -> List[QueueMessage]:
        pass

    @abstractmethod
    async def delete_message(self, queue_name: str, message: QueueMessage) -> None:
        pass

