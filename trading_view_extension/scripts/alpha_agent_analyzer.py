import sys
from pathlib import Path
import concurrent.futures
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import COT_PROMPT, COT_QUESTIONS_START_RANGE,logger
from trading_view_extension.sheets.sheet_utils import get_cot_questions, get_user_prompt
from services.generate_reasoning import Reasoner

async def run_single_stock(job, asset: str, image_urls: list):
    """
    Runs a single conversation run for one stock.
    Assumes image URLs have already been captured and uploaded.
    Initializes a Reasoner with the common parameters and prints the consensus response and trade signal.
    """
    agents = {"Weinstein Agent": ["CoT!B2","CoT!C2"], "Reversion Agent": ["CoT!B3","CoT!C3"], "Specialists Agent": ["CoT!B4","CoT!C4"], "Momentum Agent": ["CoT!B5","CoT!C5"]}
    logger.info(f"Running conversation for stock #{asset}...")
    prompt_range = COT_PROMPT
    questions_range = COT_QUESTIONS_START_RANGE

    if job['agent']:
        if job['agent'][0] in agents:
            prompt_range, questions_range = agents[job['agent'][0]]
    else:
        logger.info(f"Agent not found using default agent")

    system_prompt = get_user_prompt(prompt_range)
    questions = get_cot_questions(questions_range)

    if not image_urls:
        print(f"Stock #{asset}: No images captured/uploaded. Aborting conversation run.")
        return None
    
    # Run the conversation reasoning using the preloaded parameters and provided image URLs.
    reasoner = Reasoner(job, system_prompt, questions, image_urls)
    consensus_response, trade_signal = await reasoner.run_reasoning()
    print("=" * 80)
    print("Conversation Completed:")
    print("Consensus Response:")
    print(consensus_response)
    print("Trade Signal:")
    print(trade_signal)
    print("=" * 80)
    
    return consensus_response, trade_signal
