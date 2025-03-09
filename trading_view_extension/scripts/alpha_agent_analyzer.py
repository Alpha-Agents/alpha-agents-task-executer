import sys
from pathlib import Path
import concurrent.futures
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import COT_PROMPT, COT_QUESTIONS_START_RANGE,logger
from trading_view_extension.sheets.sheet_utils import get_cot_questions, get_user_prompt
from database.db_utilities import add_conversation
from services.generate_reasoning import Reasoner

async def run_single_stock(job, image_urls: list):
    """
    Runs a single conversation run for one stock.
    Assumes image URLs have already been captured and uploaded.
    Initializes a Reasoner with the common parameters and prints the consensus response and trade signal.
    """
    agents = {"Weinstein Agent": ["CoT!B2","CoT!C2"], "Reversion Agent": ["CoT!B3","CoT!C3"], "Specialists Agent": ["CoT!B4","CoT!C4"], "Momentum Agent": ["CoT!B5","CoT!C5"]}
    prompt_range = COT_PROMPT

    agent = (job.get("agent") or "").strip()
    user_prompt = (job.get("user_prompt") or "").strip()
    # message_id = (job.get("message_id") or "").strip()

    if agent == "" and user_prompt == "":
        # This is a fallback case - if both are missing, you can either skip or set a default prompt
        system_prompt = "You are a financial analysis assistant. Analyze the provided chart and give your observations."
        job["status"] = "COMPLETED"
    elif agent == "" and user_prompt != "":
        system_prompt = user_prompt
    else:
        agent_name = agent if agent in agents else "Specialists Agent"
        prompt_range, questions_range = agents[agent_name]
        system_prompt = get_user_prompt(prompt_range)

    reasoner = Reasoner(job, system_prompt, image_urls)
    consensus_response, trade_signal, response_message_id = await reasoner.run_reasoning()

    print("=" * 80)
    print("Conversation Completed:")
    print("Consensus Response:")
    print(consensus_response)
    print("Trade Signal:")
    print(trade_signal)
    print("=" * 80)

    return consensus_response, trade_signal, response_message_id
