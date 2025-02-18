import sys
from pathlib import Path
import concurrent.futures
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import COT_PROMPT, COT_QUESTIONS_START_RANGE, MULTI_OUTPUT_START_RANGE
from trading_view_extension.sheets.sheet_utils import get_cot_questions, get_user_prompt, write_structured_signal_multi_row, clear_output_range
from services.generate_reasoning import Reasoner

async def run_single_stock(job, asset: str, image_urls: list):
    """
    Runs a single conversation run for one stock.
    Assumes image URLs have already been captured and uploaded.
    Initializes a Reasoner with the common parameters and prints the consensus response and trade signal.
    """
    system_prompt = get_user_prompt(COT_PROMPT)
    questions = get_cot_questions(COT_QUESTIONS_START_RANGE)

    clear_output_range(MULTI_OUTPUT_START_RANGE)
    print(f"\n--- Running conversation for stock #{asset} ---")
    
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




# def main(num_stocks: int = 1):
#     """
#     Runs multiple conversation runs concurrently.
#     Loads common conversation parameters once, then for each stock:
#       1. Captures images for the current stock.
#       2. Submits a conversation run to a thread with these images.
#       3. Steps forward to prepare for the next stock.
#     """

#     # Load common conversation parameters once
#     system_prompt = get_user_prompt(COT_PROMPT)
#     # time_frames = get_time_frame(TIME_FRAME_RANGE)
#     image_urls = ['https://web-extension-screenshots.s3.us-east-1.amazonaws.com/f896d868-4fc1-4823-96a4-de2806e55d55_RDetEVBB_BTCUSD_1.png']
#     questions = get_cot_questions(COT_QUESTIONS_START_RANGE)

#     clear_output_range(MULTI_OUTPUT_START_RANGE)

#     futures = []
#     with concurrent.futures.ThreadPoolExecutor(max_workers=num_stocks) as executor:
#         for i in range(num_stocks):
#             # Capture images for the current stock in the main thread
#             # image_urls = capture_and_upload_images_tf(time_frames, sleep_time=5)
#             # if not image_urls:
#             #     print(f"Stock #{i+1}: No images captured/uploaded. Skipping this stock.")
#             #     continue
            
#             # Submit a conversation run for this stock, passing the pre-captured images
#             future = executor.submit(run_single_stock, i + 1, system_prompt, questions, image_urls)
#             futures.append(future)
            
#             # Step forward if more stocks remain
#             # if i < num_stocks - 1:
#             #     change_stock_or_step("DOWN")
#             #     time.sleep(3)  # Allow time for the UI to update
        
#         # Process results as threads complete
#         for future in concurrent.futures.as_completed(futures):
#             result = future.result()  # Each result is a tuple (consensus_response, trade_signal)
#             if result:
#                 consensus_response, trade_signal = result
#                 print("=" * 80)
#                 print("Conversation Thread Completed:")
#                 print("Consensus Response:")
#                 print(consensus_response)
#                 print("Trade Signal:")
#                 print(trade_signal)
#                 print("=" * 80)




