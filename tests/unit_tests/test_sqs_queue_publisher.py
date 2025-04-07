import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path to allow absolute import resolution
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Import the class under test
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher


@pytest.fixture
def mock_config():
    """
    Mocks input_tasks_queue, output_tasks_queue, and logger from config.py.
    """
    input_mock = MagicMock()
    output_mock = MagicMock()
    logger_mock = MagicMock()

    with patch('trading_view_extension.queue.sqs_queue_publisher.input_tasks_queue', input_mock), \
         patch('trading_view_extension.queue.sqs_queue_publisher.output_tasks_queue', output_mock), \
         patch('trading_view_extension.queue.sqs_queue_publisher.logger', logger_mock):
        yield {
            "input": input_mock,
            "output": output_mock,
            "logger": logger_mock
        }


def test_init_success(mock_config):
    """
    Tests that the publisher initializes correctly and assigns the right SQS clients.
    """
    mock_config["input"].client = MagicMock()
    mock_config["output"].client = MagicMock()

    publisher = SQSQueuePublisher()

    assert publisher.input_sqs_client == mock_config["input"].client
    assert publisher.output_sqs_client == mock_config["output"].client
    mock_config["logger"].info.assert_called_with("SQS clients initialized successfully.")


def test_init_failure(mock_config):
    """
    Tests that an exception is raised if SQS client initialization fails.
    """
    mock_config["input"].client = None
    mock_config["output"].client = None

    # Force an exception when accessing client
    del mock_config["input"].client

    with pytest.raises(Exception):
        SQSQueuePublisher()
    mock_config["logger"].exception.assert_called_once()


@pytest.mark.asyncio
async def test_publish_task_completed_analysis(mock_config):
    """
    Tests that a COMPLETED job with action_type='analysis' is published to the input queue.
    """
    mock_client = MagicMock()
    mock_config["input"].client = mock_client
    mock_config["input"].url = "input-url"
    mock_config["output"].client = MagicMock()
    mock_config["output"].url = "output-url"

    publisher = SQSQueuePublisher()

    job = {
        "status": "COMPLETED",
        "action_type": "analysis",
        "result": [{"trade": "BUY"}]
    }

    await publisher.publish_task(job)

    # Validate call to send_message
    mock_client.send_message.assert_called_once()
    args, kwargs = mock_client.send_message.call_args

    assert kwargs["QueueUrl"] == "input-url"
    assert kwargs["MessageGroupId"] == "analysis_tasks"
    assert json.loads(kwargs["MessageBody"])["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_publish_task_completed_processed(mock_config):
    """
    Tests that a COMPLETED job with action_type='processed' is published to the output queue.
    """
    mock_client = MagicMock()
    mock_config["output"].client = mock_client
    mock_config["output"].url = "output-url"
    mock_config["input"].client = MagicMock()
    mock_config["input"].url = "input-url"

    publisher = SQSQueuePublisher()

    job = {
        "status": "COMPLETED",
        "action_type": "processed",
        "result": [{"trade": "SELL"}]
    }

    await publisher.publish_task(job)

    mock_client.send_message.assert_called_once()
    args, kwargs = mock_client.send_message.call_args
    assert kwargs["QueueUrl"] == "output-url"
    assert kwargs["MessageGroupId"] == "processed_tasks"


@pytest.mark.asyncio
async def test_publish_task_running(mock_config):
    """
    Tests that a RUNNING job is published to the output queue.
    """
    mock_client = MagicMock()
    mock_config["output"].client = mock_client
    mock_config["output"].url = "output-url"
    mock_config["input"].client = MagicMock()
    mock_config["input"].url = "input-url"

    publisher = SQSQueuePublisher()

    job = {
        "status": "RUNNING",
        "action_type": "analysis"
    }

    await publisher.publish_task(job)

    mock_client.send_message.assert_called_once()
    args, kwargs = mock_client.send_message.call_args
    assert kwargs["QueueUrl"] == "output-url"
    assert kwargs["MessageGroupId"] == "analysis_tasks"


@pytest.mark.asyncio
async def test_publish_task_error_handling(mock_config):
    """
    Tests that logger.exception is called when publishing fails.
    """
    mock_config["output"].client.send_message.side_effect = Exception("SQS error")
    mock_config["output"].url = "output-url"
    mock_config["input"].client = MagicMock()
    mock_config["input"].url = "input-url"

    publisher = SQSQueuePublisher()

    job = {
        "status": "RUNNING",
        "action_type": "analysis"
    }

    with pytest.raises(Exception):
        await publisher.publish_task(job)

    mock_config["logger"].exception.assert_called_once_with("Failed to publish message to SQS.")
