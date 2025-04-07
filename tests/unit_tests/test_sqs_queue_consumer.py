import pytest
import threading
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys
from pathlib import Path

# Add the parent path to sys.path so imports work properly
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Import the class under test
from trading_view_extension.queue.sqs_queue_consumer import SqsQueueConsumer
from concurrent.futures import ThreadPoolExecutor

# -------- Fixtures --------

@pytest.fixture
def mock_dependencies():
    """
    Mocks all external dependencies used in SqsQueueConsumer.
    This includes sqs_client, AiOrchestrator, and sqs_queue_publisher.
    """
    sqs_queue_publisher = MagicMock()
    sqs_client_mock = MagicMock()
    orchestrator_mock = AsyncMock()

    with patch('trading_view_extension.queue.sqs_queue_consumer.sqs_client', sqs_client_mock), \
         patch('trading_view_extension.queue.sqs_queue_consumer.AiOrchestrator', return_value=orchestrator_mock):
        yield {
            'publisher': sqs_queue_publisher,
            'sqs_client': sqs_client_mock,
            'orchestrator': orchestrator_mock
        }

# -------- Tests --------

def test_init(mock_dependencies):
    """
    Tests the initialization of the SqsQueueConsumer class.
    Verifies that dependencies are correctly assigned and internal components (lock, executor) are set up.
    """
    consumer = SqsQueueConsumer(mock_dependencies['publisher'])

    assert consumer.sqs_queue_publisher == mock_dependencies['publisher']
    assert isinstance(consumer.lock, type(threading.Lock()))
    assert isinstance(consumer.executor, ThreadPoolExecutor)
    assert consumer.local_safe_store == {}

def test_receive_messages(mock_dependencies):
    """
    Tests whether receive_messages correctly pulls messages from the SQS client.
    """
    mock_dependencies['sqs_client'].receive_message.return_value = {
        'Messages': [{'MessageId': '1', 'Body': '{}'}]
    }

    consumer = SqsQueueConsumer(mock_dependencies['publisher'])
    messages = consumer.receive_messages("dummy-queue")

    assert len(messages) == 1
    assert messages[0]['MessageId'] == '1'

@pytest.mark.asyncio
async def test_delete_message_success(mock_dependencies):
    """
    Tests that delete_message asynchronously calls the SQS client's delete_message method using asyncio.to_thread.
    """
    consumer = SqsQueueConsumer(mock_dependencies['publisher'])
    message = {'MessageId': '1', 'ReceiptHandle': 'abc'}

    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
        await consumer.delete_message("dummy-queue", message)
        mock_to_thread.assert_awaited_once()

@patch('trading_view_extension.queue.sqs_queue_consumer.asyncio.run')
def test_safe_process_message_success(mock_asyncio_run, mock_dependencies):
    """
    Tests that safe_process_message stores the message, deletes it, processes it,
    and then removes it from the safe store upon success.
    """
    mock_asyncio_run.return_value = None
    consumer = SqsQueueConsumer(mock_dependencies['publisher'])

    message = {'MessageId': '1', 'Body': '{"job": "test"}', 'ReceiptHandle': 'abc'}
    consumer.process_message_body = MagicMock()

    consumer.safe_process_message("dummy-queue", message)

    assert '1' not in consumer.local_safe_store  # Message should be removed after processing


def test_process_message_body_invalid_json(mock_dependencies):
    consumer = SqsQueueConsumer(mock_dependencies['publisher'])

    message = {'MessageId': '1', 'Body': 'not-a-json'}

    consumer.orchestrator.handle_job = AsyncMock()

    consumer.process_message_body(message)

    consumer.orchestrator.handle_job.assert_not_called()



def test_replay_safe_store(mock_dependencies):
    """
    Tests that replay_safe_store processes and removes messages from the local_safe_store.
    """
    consumer = SqsQueueConsumer(mock_dependencies['publisher'])

    message = {'MessageId': '1', 'Body': '{"job": "test"}'}
    consumer.local_safe_store['1'] = message

    consumer.process_message_body = MagicMock()
    consumer.replay_safe_store()

    assert '1' not in consumer.local_safe_store  # Message should be removed after successful replay
