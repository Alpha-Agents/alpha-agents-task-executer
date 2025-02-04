import sys
import time
from pathlib import Path
from datetime import datetime
import json
# Ensure local modules (config, sheet_utils, etc.) are importable
sys.path.append(str(Path(__file__).resolve().parent.parent))

from openai import OpenAI
from config import API_KEY, MAX_TOKENS, IMAGE_DETAIL, IMAGE_HOST, SPREADSHEET_ID, logger
from utils.sheet_utils import (
    get_selected_assistants_ids_prompts,
    get_is_take_image,
    get_number_of_images,
    get_user_prompt,
    get_is_separated,
    write_structured_signal,
    clear_output_range
)
from services.openai_service import OpenAIService
from services.image_service import upload_images
from services.structured_output_service import StructuredOutputService
from screen_shot.screenshot import take_screenshot
from services.structured_output_service import StructuredOutputService

# -------------------------------------------------------------------
# Retrieve / update assistant instructions
# -------------------------------------------------------------------

def get_assistant_details(client, assistant_id):
    """Retrieve the details (instructions, etc.) of a specified assistant."""
    try:
        return client.beta.assistants.retrieve(assistant_id)
    except Exception as e:
        print(f"Error retrieving assistant details for {assistant_id}: {e}")
        return None

def update_assistant_instructions(client, assistant_id, new_instructions):
    """Update the instructions for a specific assistant, if needed."""
    try:
        updated = client.beta.assistants.update(
            assistant_id,
            instructions=new_instructions
        )
        print(f"[{assistant_id}] Instructions updated successfully.")
        return updated
    except Exception as e:
        print(f"[{assistant_id}] Error updating instructions: {e}")
        return None

# -------------------------------------------------------------------
# GPTClient: builds message content & interacts with ephemeral threads
# -------------------------------------------------------------------

class GPTClient:
    """
    A GPT client that:
      - Creates ephemeral threads
      - Sends user text + image URLs (no screenshot capture logic here)
      - Has synchronous & parallel-friendly methods
    """
    def __init__(self):
        self.client = OpenAI(api_key=API_KEY)
        self.openai_service = OpenAIService(self.client)

    def build_message_content(self, user_text: str, image_urls: list) -> list:
        """
        Build message blocks from the user's text plus pre-uploaded image URLs.
        """
        message_blocks = [{"type": "text", "text": user_text}]

        for url in image_urls:
            message_blocks.append({
                "type": "image_url",
                "image_url": {
                    "url": url,
                    "detail": IMAGE_DETAIL
                }
            })

        return message_blocks

    # def ask_assistant(self, assistant_id: str, user_text: str, image_urls: list) -> str:
    #     """
    #     SYNC: Creates ephemeral thread, sends user_text + image_urls,
    #     waits for completion, then returns the assistant's response.
    #     """
    #     thread_id = None
    #     try:
    #         # Create ephemeral thread
    #         thread = self.client.beta.threads.create()
    #         thread_id = thread.id

    #         # Build content
    #         content_blocks = self.build_message_content(user_text, image_urls)

    #         # Send user message
    #         self.openai_service.send_user_message(thread_id, content_blocks, role="user")

    #         # Create run & wait
    #         run = self.client.beta.threads.runs.create(
    #             thread_id=thread_id,
    #             assistant_id=assistant_id,
    #             max_completion_tokens=MAX_TOKENS
    #         )
    #         run_id = run.id

    #         response = self.openai_service.wait_for_run(run_id, thread_id)
    #         return response

    #     except Exception as e:
    #         print(f"Error interacting with assistant {assistant_id}: {e}")
    #         return f"Error from {assistant_id}: {e}"
    #     finally:
    #         # Delete ephemeral thread
    #         if thread_id:
    #             try:
    #                 self.client.beta.threads.delete(thread_id)
    #             except Exception as e:
    #                 print(f"Error deleting thread {thread_id}: {e}")

    def ask_assistant(self, assistant_id: str, user_text: str, image_urls: list) -> dict:
        """Sends query to OpenAI and ensures structured JSON response"""
        thread_id = None
        try:
            thread = self.client.beta.threads.create()
            thread_id = thread.id
            content_blocks = self.build_message_content(user_text, image_urls)
            self.openai_service.send_user_message(thread_id, content_blocks, role="user")

            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id,
                max_completion_tokens=MAX_TOKENS,
                response_format="auto"  # Ensure JSON format
            )
            run_id = run.id

            response = self.openai_service.wait_for_run(run_id, thread_id)

            structured_service = StructuredOutputService(self.client)
            structured_response = structured_service.get_trade_signal(response)

            if structured_response:
                structured_data =  [{
                    "image_url": image_urls,  # Ensure image is correctly mapped
                    "analysis": structured_response.dict()  # Structured trade signal
                }]

                logger.info(f"Successfully extracted trade signal: {structured_data}")
                return structured_data

            logger.error(f"AI response did not contain structured output! {response}")
            return {"error": "AI did not return structured output"}

        except Exception as e:
            logger.error(f"Error interacting with assistant {assistant_id}: {e}")
            return {"error": str(e)}

    # --------------------------
    # Async / Parallel Helpers
    # --------------------------
    def start_assistant_run(self, assistant_id: str, user_text: str, image_urls: list):
        """
        Create an ephemeral thread, send user_text + image_urls,
        create a run for 'assistant_id', but do NOT wait for completion.
        Returns (thread_id, run_id).
        """
        thread = self.client.beta.threads.create()
        thread_id = thread.id

        content_blocks = self.build_message_content(user_text, image_urls)
        self.openai_service.send_user_message(thread_id, content_blocks, role="user")

        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            max_completion_tokens=MAX_TOKENS
        )
        run_id = run.id

        return thread_id, run_id

    def check_run_status(self, thread_id: str, run_id: str) -> str:
        """Return the run status: 'completed', 'failed', 'cancelled', 'expired', or 'running'."""
        run_info = self.client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        return run_info.status

    def fetch_latest_assistant_message(self, thread_id: str) -> str:
        """Get the entire content of the most recent assistant message."""
        return self.openai_service.get_latest_assistant_message(thread_id)

    def delete_thread(self, thread_id: str):
        """Safely delete a thread."""
        try:
            self.client.beta.threads.delete(thread_id)
        except Exception as e:
            print(f"Error deleting thread {thread_id}: {e}")

# -------------------------------------------------------------------
# Capture & upload images once
# -------------------------------------------------------------------

def capture_and_upload_images(num_images: int) -> list:
    """
    Capture num_images screenshots (pausing if >1), upload them once,
    return the list of image URLs.
    """
    if num_images <= 0:
        return []

    image_paths = []
    for i in range(num_images):
        if num_images > 1:
            print(f"Prepare screen for screenshot {i+1}/{num_images}. Press Enter when ready.")
            input()

        image_path = take_screenshot()
        if not image_path:
            print("Failed to capture screenshot. Skipping this one.")
            continue

        print(f"Captured screenshot {i+1} at {image_path}.")
        image_paths.append(image_path)

    if not image_paths:
        return []

    # Upload once
    urls = upload_images(image_paths, IMAGE_HOST)
    return urls

# -------------------------------------------------------------------
# run_parallel_queries with "is_separated"
# -------------------------------------------------------------------

def run_parallel_queries(
    gpt_client: GPTClient,
    assistant_ids: list,
    user_query: str,
    image_urls: list,
    is_separated: bool,
    max_wait=300,
    max_retries=1
):
    """
    If is_separated == False:
      - For each assistant, build ONE run that includes ALL image_urls.

    If is_separated == True:
      - For each assistant, for each image, build a run with ONLY that single image URL.
      - We'll end up with (num_images * number_of_assistants) runs in parallel.

    Returns a data structure:
      - If is_separated == False: {assistant_id: single_string_response}
      - If is_separated == True:  {assistant_id: [resp_for_image0, resp_for_image1, ...]}
    """
    results = {}
    run_data = []

    num_images = len(image_urls)

    if not is_separated:
        # -- COMBINED: single run per assistant with all images --
        for assistant_id in assistant_ids:
            try:
                thread_id, run_id = gpt_client.start_assistant_run(
                    assistant_id,
                    user_text=user_query,
                    image_urls=image_urls
                )
                run_data.append({
                    "assistant_id": assistant_id,
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "done": False,
                    "response": None,
                    "retries": 0,
                    "image_index": None  # no index, because they're all combined
                })
                print(f"[Combined] Started run for {assistant_id} => thread={thread_id}, run={run_id}")
            except Exception as e:
                results[assistant_id] = f"ERROR starting run: {e}"
                print(results[assistant_id])

    else:
        # -- SEPARATE: multiple runs per assistant (1 per image) --
        for assistant_id in assistant_ids:
            # We'll store each assistant's responses in a list
            results[assistant_id] = [None] * num_images  # placeholder list
            for idx in range(num_images):
                single_image_list = [image_urls[idx]]  # only the i-th image
                try:
                    thread_id, run_id = gpt_client.start_assistant_run(
                        assistant_id,
                        user_text=user_query,
                        image_urls=single_image_list
                    )
                    run_data.append({
                        "assistant_id": assistant_id,
                        "thread_id": thread_id,
                        "run_id": run_id,
                        "done": False,
                        "response": None,
                        "retries": 0,
                        "image_index": idx  # track which image this run is for
                    })
                    print(f"[Separate] Started run for {assistant_id} image={idx} => thread={thread_id}, run={run_id}")
                except Exception as e:
                    # If we couldn't start, store an error right away
                    results[assistant_id][idx] = f"ERROR starting run: {e}"
                    print(results[assistant_id][idx])

    # 2. Poll until done or timeout
    start_time = time.time()

    while True:
        all_done = True

        for rd in run_data:
            if rd["done"]:
                continue
            all_done = False

            current_status = None
            try:
                current_status = gpt_client.check_run_status(rd["thread_id"], rd["run_id"])
            except Exception as e:
                print(f"Error checking run status for {rd['assistant_id']}: {e}")
                current_status = "failed"

            if current_status == "completed":
                # fetch final message
                try:
                    final_text = gpt_client.fetch_latest_assistant_message(rd["thread_id"])
                    rd["response"] = final_text
                except Exception as e:
                    rd["response"] = f"ERROR retrieving final text: {e}"

                rd["done"] = True
                gpt_client.delete_thread(rd["thread_id"])
                print(f"[{rd['assistant_id']}] run {rd['run_id']} completed.")

            elif current_status in ["failed", "cancelled", "expired"]:
                rd["retries"] += 1
                if rd["retries"] <= max_retries:
                    print(f"[{rd['assistant_id']}] run {rd['run_id']} -> {current_status}, retry #{rd['retries']}")
                    gpt_client.delete_thread(rd["thread_id"])
                    # Re-start
                    # If is_separated, we have an image_index; if combined, it's None => we pass all
                    if rd["image_index"] is not None:
                        single_image_list = [image_urls[rd["image_index"]]]
                    else:
                        single_image_list = image_urls  # all images
                    try:
                        thread_id, run_id = gpt_client.start_assistant_run(
                            rd["assistant_id"],
                            user_text=user_query,
                            image_urls=single_image_list
                        )
                        rd["thread_id"] = thread_id
                        rd["run_id"] = run_id
                    except Exception as e2:
                        rd["response"] = f"ERROR even on retry: {e2}"
                        rd["done"] = True
                else:
                    rd["response"] = f"ERROR: run status={current_status}"
                    rd["done"] = True
                    gpt_client.delete_thread(rd["thread_id"])
                    print(f"[{rd['assistant_id']}] run {rd['run_id']} ended with {current_status} after max retries.")

        if all_done:
            break

        elapsed = time.time() - start_time
        if elapsed >= max_wait:
            print(f"Timeout after {max_wait} seconds.")
            for rd in run_data:
                if not rd["done"]:
                    rd["done"] = True
                    rd["response"] = "ERROR: Timed out."
                    gpt_client.delete_thread(rd["thread_id"])
            break

        time.sleep(0.5)

    # 3. Compile final results
    if not is_separated:
        # Single response per assistant
        final_results = {}
        for rd in run_data:
            assistant_id = rd["assistant_id"]
            if rd["response"] is None:
                rd["response"] = "ERROR: Unknown final result."
            final_results[assistant_id] = rd["response"]
        return final_results

    else:
        # multiple responses per assistant => results[assistant_id] is a list
        # We placed placeholders in results[...] at the start. Let's fill them in.
        for rd in run_data:
            assistant_id = rd["assistant_id"]
            idx = rd["image_index"]
            # If we haven't set an error earlier, store the final response
            if rd["response"] is None:
                rd["response"] = "ERROR: Unknown final result."
            results[assistant_id][idx] = rd["response"]

        return results

# -------------------------------------------------------------------
# main
# -------------------------------------------------------------------

def main():
    # 1. Initialize
    gpt_client = GPTClient()
    client = gpt_client.client
    
    # ** Initialize StructuredOutputService **
    structured_service = StructuredOutputService(client)

    # 2. Pull data from Google Sheet
    assistant_ids, assistant_prompts, assistant_titles = get_selected_assistants_ids_prompts()
    user_query = get_user_prompt()
    is_take_image = get_is_take_image()
    num_images = get_number_of_images() if is_take_image else 0
    is_separated = get_is_separated()

    # 3. Capture & upload images once
    image_urls = capture_and_upload_images(num_images)

    # 4. Update instructions if needed
    for assistant_id, new_instructions, title in zip(assistant_ids, assistant_prompts, assistant_titles):
        details = get_assistant_details(client, assistant_id)
        if not details:
            print(f"Could not retrieve details for {title}, skipping update.")
            continue

        current_instructions = (details.instructions or "").strip()
        desired_instructions = new_instructions.strip()
        if current_instructions != desired_instructions:
            print(f"[{assistant_id}] Updating instructions ...")
            update_assistant_instructions(client, assistant_id, desired_instructions)
        else:
            print(f"[{assistant_id}] Instructions already up to date.")

    # 5. Run in parallel (either separate or combined)
    print("\nStarting parallel runs...")
    results = run_parallel_queries(
        gpt_client=gpt_client,
        assistant_ids=assistant_ids,
        user_query=user_query,
        image_urls=image_urls,
        is_separated=is_separated,
        max_wait=300,   # 5 minutes
        max_retries=1
    )
    
    clear_output_range()

    # Example variable to track how many structured outputs we have written
    structured_output_count = 0

    print("\n=== FINAL RESULTS ===")
    if not is_separated:
        # results is {assistant_id: single_string}
        for assistant_id, title in zip(assistant_ids, assistant_titles):
            resp = results.get(assistant_id, "No response found.")
            print(f"\nAssistant: {assistant_id} ({title})")
            print(f"Raw Response:\n{resp}\n")

            # Try parsing structured output
            signal = structured_service.get_trade_signal(resp)
            if signal:
                print("Structured Output:")
                print(signal.dict())

                # Write to Google Sheet, shifting one column per structured output
                write_structured_signal(SPREADSHEET_ID, title, signal, structured_output_count)
                structured_output_count += 1
            else:
                print("No structured output found.")
    else:
        # results is {assistant_id: list_of_strings}, one per image
        for assistant_id, title in zip(assistant_ids, assistant_titles):
            responses = results.get(assistant_id, [])
            print(f"\nAssistant: {assistant_id} ({title})")

            for idx, r in enumerate(responses):
                print(f"Response for image #{idx+1}:\n{r}\n")

                # Try parsing
                signal = structured_service.get_trade_signal(r)
                if signal:
                    print("Structured Output:")
                    print(signal.dict())

                    # Write to Google Sheet
                    write_structured_signal(SPREADSHEET_ID, title, signal, structured_output_count)
                    structured_output_count += 1
                else:
                    print("No structured output found.")
                
                print("--------")

    print("Done.")


if __name__ == "__main__":
    main()