import sys
from pathlib import Path
import concurrent.futures
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import DEFAULT_PROMPT, DEFAULT_QUERY
from trading_view_extension.database.db_utilities import get_conversation_by_id, add_conversation
from trading_view_extension.services.generate_reasoning import generate_response

async def analyze(job, image_urls: list): 
    """
    Runs a single conversation run for one stock.
    Assumes image URLs have already been captured and uploaded.
    Initializes a Reasoner with the common parameters and prints the consensus response and trade signal.
    """
    show_query = True
    if job.get("agent") == "custom": 
        system_prompt = job.get("prompt")
        query = job.get("agent_query")
    else:
        system_prompt = DEFAULT_PROMPT
        query = DEFAULT_QUERY

    if job.get("is_chat"):
        query = job.get("agent_query")
        if query == "":
            query = "Consider the new images."
            show_query = False

        conversation_history = [
            {key: value for key, value in message.items() if key != "message_id"}
            for message in get_conversation_by_id(job.get("job_id"))
        ]
        message_id =job.get("message_id")
        response, trade_signal, response_message_id = generate_response(
            job,
            system_prompt,
            query,
            conversation_history,
            image_urls,
            message_id,
            is_trade_signal=True,
            show_query
        )
    else:
        conversation_history = []
        additional_info = job.get("user_instructions")
        system_prompt = system_prompt + "\n" + additional_info
        add_conversation(
            job.get("job_id"),
            conversation_history,
            job.get("email_id"),
            job.get("asset"),
            job.get("agent")
        )

        response, trade_signal, response_message_id = generate_response(
            job,
            system_prompt,
            query,
            conversation_history,
            image_urls,
            message_id = None,
            is_trade_signal=True,
            show_query
        )

    # print("=" * 80)
    # print("Response:")
    # print(response)
    # print("Trade Signal:")
    # print(trade_signal)
    # print("=" * 80)

    return response, trade_signal, response_message_id
    