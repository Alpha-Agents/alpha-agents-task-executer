import asyncio
from services.openrouter_client import query_openrouter
from services.structured_output_service import StructuredOutputService
from config import OBSERVATION_MODEL_NAME, logger, CONSENSUS_MODEL
from trading_view_extension.database.db_utilities import add_message, update_trade_signal_db_and_symbol, deduct_user_credits
from trading_view_extension.queue.sqs_queue_publisher import SQSQueuePublisher
import uuid

def generate_response(job, system_prompt, query, conversation_history, image_urls=None, message_id=None, is_trade_signal=True):
    """
    Process a reasoning conversation for the given symbol and parameters.
    
    Args:
        job (dict): The job object.
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
        add_message(job['job_id'], {"message_id": uuid.uuid4().hex, "role": "system", "content": [{"type": "text", "text": system_prompt}]})
        conversation_history.insert(0, system_message)

    # Build content for the new user message, including text and images.
    content = [{"type": "text", "text": query}]
    if image_urls:
        content.extend([{"type": "image_url", "image_url": {"url": url}} for url in image_urls])
    
    # Append the user message with both text and images.
    conversation_history.append({"role": "user", "content": content})
    if message_id:
        add_message(job['job_id'], {"message_id": message_id, "role": "user", "content": content})
    else: 
        add_message(job['job_id'], {"message_id": uuid.uuid4().hex, "role": "user", "content": content})

    # Get response from the API using the conversation history directly.
    try:
        response, credits = query_openrouter(conversation_history)
    except Exception as e:
        print(f"Error in API call: {e}")
        response = "Error occurred during processing."
        credits = 0
    
    # Append the assistant's response as a new message.
    conversation_history.append({"role": "assistant", "content": [{"type": "text", "text": response}]})
    response_message_id = uuid.uuid4().hex
    add_message(job['job_id'], {"message_id": response_message_id, "role": "assistant", "content": [{"type": "text", "text": response}]})
    deduct_user_credits("shruti@gmail.com",credits)

    # Extract trade signal from the response if requested.
    trade_signal_result = None
    if is_trade_signal:
        trade_signal_result = StructuredOutputService().get_trade_signal(response, job["asset"])
        update_trade_signal_db_and_symbol(job.get("job_id"), trade_signal_result, job['asset'])

    return response, trade_signal_result, response_message_id
