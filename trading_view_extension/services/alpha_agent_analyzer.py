import sys
from pathlib import Path
import concurrent.futures
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import COT_PROMPT, COT_QUESTIONS_START_RANGE,logger
from trading_view_extension.database.db_utilities import get_conversation_by_id, add_conversation
from services.generate_reasoning import generate_response

async def analyze(job, image_urls: list): 
    """
    Runs a single conversation run for one stock.
    Assumes image URLs have already been captured and uploaded.
    Initializes a Reasoner with the common parameters and prints the consensus response and trade signal.
    """

    if job.get("agent") == "custom": 
        system_prompt = job.get("prompt")
        query = job.get("agent_query")
    else:
        system_prompt = """Your role is to analyze stock charts with exceptional expertise. You will provide your analysis, your expert opinion on if you should BUY / SELL / WAIT.
        You will provide a confidence score of your decision. And you will provide entry, profit target, and stop loss, for any BUY or SELL decision.
        Note: The price will be highlighed on the right side as the same color as the indicator
        Respond in markdown format."""
        query = "Do you see any trade setups? How confident are you? Trade or wait?"

    if job.get("is_chat"):
        query = job.get("agent_query")
        if query == "":
            query = "Consider the new images."
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
            is_trade_signal=False,
        )
    else:
        conversation_history = []
        additional_info = job.get("user_instructions")
        system_prompt = system_prompt + "\n" + additional_info
        add_conversation(
            job.get("job_id"),
            conversation_history,
            "shruti@gmail.com",
            job.get("symbol")
        )

        response, trade_signal, response_message_id = generate_response(
            job,
            system_prompt,
            query,
            conversation_history,
            image_urls,
            message_id = None,
            is_trade_signal=True
        )

    # print("=" * 80)
    # print("Response:")
    # print(response)
    # print("Trade Signal:")
    # print(trade_signal)
    # print("=" * 80)

    return response, trade_signal, response_message_id
    