import sys
from pathlib import Path
import concurrent.futures
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import COT_PROMPT, COT_QUESTIONS_START_RANGE,logger
from trading_view_extension.sheets.sheet_utils import get_user_prompt
from database.db_utilities import get_conversation_by_id, update_trade_signal_db, add_conversation
from services.generate_reasoning import generate_response

# async def run_single_stock(job, image_urls: list):
#     """
#     Runs a single conversation run for one stock.
#     Assumes image URLs have already been captured and uploaded.
#     Initializes a Reasoner with the common parameters and prints the consensus response and trade signal.
#     """
#     agents = {"Weinstein Agent": ["CoT!B2","CoT!C2"], "Reversion Agent": ["CoT!B3","CoT!C3"], "Specialists Agent": ["CoT!B4","CoT!C4"], "Momentum Agent": ["CoT!B5","CoT!C5"]}
#     prompt_range = COT_PROMPT

#     agent = (job.get("agent") or "").strip()
#     user_prompt = (job.get("user_prompt") or "").strip()
#     # message_id = (job.get("message_id") or "").strip()

#     if agent == "" and user_prompt == "":
#         # This is a fallback case - if both are missing, you can either skip or set a default prompt
#         system_prompt = "You are a financial analysis assistant. Analyze the provided chart and give your observations."
#         job["status"] = "COMPLETED"
#     elif agent == "" and user_prompt != "":
#         system_prompt = user_prompt
#     else:
#         agent_name = agent if agent in agents else "Specialists Agent"
#         prompt_range, questions_range = agents[agent_name]
#         system_prompt = get_user_prompt(prompt_range)

#     reasoner = Reasoner(job, system_prompt, image_urls)
#     consensus_response, trade_signal, response_message_id = await reasoner.run_reasoning()

#     print("=" * 80)
#     print("Conversation Completed:")
#     print("Consensus Response:")
#     print(consensus_response)
#     print("Trade Signal:")
#     print(trade_signal)
#     print("=" * 80)

#     return consensus_response, trade_signal, response_message_id



async def analyze(job, image_urls: list): 
    """
    Runs a single conversation run for one stock.
    Assumes image URLs have already been captured and uploaded.
    Initializes a Reasoner with the common parameters and prints the consensus response and trade signal.
    """

    if job.get("agent") == "custom": # CURRENTLY PULLS FROM GOOGLE SHEET - CHANGE TO PULL FROM DB - MAKE A NEW SCRIPT SIMILUAR TO SHEETS_UTILS BUT DB_UTILS
        system_prompt = job.get("prompt")
        query = job.get("agent_query")
    else:
        system_prompt = get_user_prompt("CoT!B4")
        query = job.get("agent_query")

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
        add_conversation(job.get("job_id"),conversation_history)
        response, trade_signal, response_message_id = generate_response(
            job,
            system_prompt,
            query,
            conversation_history,
            image_urls,
            message_id = None,
            is_trade_signal=True
        )

    print("=" * 80)
    print("Response:")
    print(response)
    print("Trade Signal:")
    print(trade_signal)
    print("=" * 80)

    return response, trade_signal, response_message_id
    