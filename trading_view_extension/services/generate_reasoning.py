import asyncio
from services.openrouter_client import query_openrouter
from services.structured_output_service import StructuredOutputService
from config import OBSERVATION_MODEL_NAME, logger, CONSENSUS_MODEL
from database.db_utilities import get_conversation_by_id, add_message, add_conversation, conversation_exists
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
import uuid


def generate_response(system_prompt, query, conversation_history, image_urls=None, is_trade_signal=True):
    """
    Process a reasoning conversation for the given symbol and parameters.
    
    Args:
        symbol (str): The stock symbol for conversation history management.
        system_prompt (str): The system prompt for the AI.
        query (str): The query to ask.
        image_urls (list, optional): List of image URLs to include.
        is_trade_signal (bool): Whether to extract a trade signal.
        
    Returns:
        tuple: (response, trade_signal)
    """
    
    # Ensure the system prompt is the first message, formatted properly as text.
    if not any(msg["role"] == "system" for msg in conversation_history):
        system_message = {"role": "system", "content": [{"type": "text", "text": system_prompt}]}
        conversation_history.insert(0, system_message)

    # Build content for the new user message, including text and images.
    content = [{"type": "text", "text": query}]
    if image_urls:
        content.extend([{"type": "image_url", "image_url": {"url": url}} for url in image_urls])
    
    # Append the user message with both text and images.
    conversation_history.append({"role": "user", "content": content})
    
    # Get response from the API using the conversation history directly.
    try:
        response = query_openrouter(conversation_history)
    except Exception as e:
        print(f"Error in API call: {e}")
        response = "Error occurred during processing."
    
    # Append the assistant's response as a new message.
    conversation_history.append({"role": "assistant", "content": [{"type": "text", "text": response}]})
    
    # Extract trade signal from the response if requested.
    trade_signal_result = None
    if is_trade_signal:
        trade_signal_result = StructuredOutputService().get_trade_signal(response)
    
    return response, trade_signal_result

