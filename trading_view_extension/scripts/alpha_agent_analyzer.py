import sys
from pathlib import Path
import concurrent.futures
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import (CUSTOM_AGENT_PROMPT_RANGE, CUSTOM_AGENT_QUERY_RANGE, 
                    DEFAULT_AGENT_PROMPT_RANGE, DEFAULT_AGENT_QUERY_RANGE, ADDITIONAL_INFO_RANGE, logger)

from trading_view_extension.sheets.sheet_utils import get_user_prompt, get_is_custom, get_data_string

from database.db_utilities import add_conversation
from services.generate_reasoning import Reasoner

async def analyze(job, image_urls: list): 
    """
    Runs a single conversation run for one stock.
    Assumes image URLs have already been captured and uploaded.
    Initializes a Reasoner with the common parameters and prints the consensus response and trade signal.
    """

    if get_is_custom(): # CURRENTLY PULLS FROM GOOGLE SHEET - CHANGE TO PULL FROM DB - MAKE A NEW SCRIPT SIMILUAR TO SHEETS_UTILS BUT DB_UTILS
        system_prompt = get_data_string(CUSTOM_AGENT_PROMPT_RANGE)
        query = [get_data_string(CUSTOM_AGENT_QUERY_RANGE)]
    else:
        system_prompt = get_data_string(DEFAULT_AGENT_PROMPT_RANGE)
        query = [get_data_string(DEFAULT_AGENT_QUERY_RANGE)] # Remove the questions for loop and the list later

    additional_info = get_data_string(ADDITIONAL_INFO_RANGE)

    system_prompt = system_prompt + "\n" + additional_info



    # NEED CODE TO CHECK THE DATA BASE IF A CONVERSATION EXISTS ALREADY OR NOT
    # Check if a conversation already exists
    conversation_history = get_conversation_history(job)
    is_new_conversation = #need def to check if this is a new convo

    if is_new_conversation:
        response, trade_signal = generate_response(
            conversation_history,
            system_prompt,
            query,
            image_urls,
            is_trade_signal=True
        )

    else:
        
        if the user entered a query:
            query = new user input 
        else:
            query = "Consider the new images."

         response, trade_signal = generate_response(
            conversation_history,
            system_prompt,
            query,
            image_urls,
            is_trade_signal=True
        )


 
    # Update the conversation history in db
    update_conversation_history_db(conversation_history?, response)
    update_trade_signal_db(trade_signal)

    print("=" * 80)
    print("Response:")
    print(response)
    print("Trade Signal:")
    print(trade_signal)
    print("=" * 80)

    update_frontend(response, trade_signal)?
    or return response, trade_signal
    
