
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
import time
from openai import OpenAI
import sys
import os
# ✅ Add project root to `sys.path` to prioritize your local `config.py`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config import MODEL, API_KEY


class OpenAIService:
    def __init__(self, client, model=MODEL):
        # self.client = client
        self.model = model
        self.client = OpenAI(api_key=API_KEY)

    def wait_for_run(self, run_id: str, thread_id: str) -> str:
        """Wait for a run to complete and return the assistant's response."""
        try:
            while True:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )

                if run_status.status == 'completed':
                    # Retrieve and parse the latest assistant message
                    return self.get_latest_assistant_message(thread_id)

                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    return f"Error: Run failed with status '{run_status.status}'."

                time.sleep(0.25)
        except Exception as e:
            return f"Error while waiting for run: {e}"

    def get_latest_assistant_message(self, thread_id: str) -> str:
        """Retrieve the latest assistant message for the given thread."""
        messages = self.client.beta.threads.messages.list(thread_id=thread_id)

        if messages.data:
            assistant_messages = [
                message for message in messages.data if message.role == "assistant"
            ]

            if assistant_messages:
                latest_message = max(assistant_messages, key=lambda msg: msg.created_at)
                response_content = latest_message.content
                response_text = ''.join(
                    block.text.value for block in response_content if block.type == "text"
                )
                if not response_text.strip():
                    return "ERROR: AI returned an empty response."
                
                return response_text

        return "No assistant response received."

    def send_user_message(self, thread_id: str, content, role: str = "user"):
        """Send a user or system message to the specified thread."""
        # The content can be a string or a structured message
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,  # Now we use the role
            content=content
        )
        
    def create_text_run(self, thread_id: str, assistant_id: str, max_tokens: int) -> str:
        """Create a run for text completion and return run_id."""
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            model = self.model,
            max_completion_tokens=max_tokens
        )
        return run.id
    
    def check_run_status(self, run_id: str, thread_id: str) -> str:
        """
        Check the current status of the given run_id on thread_id.
        Returns 'completed', 'failed', 'cancelled', 'expired', 'in_progress', or 'error'.
        """
        try:
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            return run_status.status
        except Exception as e:
            print(f"Error checking run status for run_id={run_id} in thread_id={thread_id}: {e}")
            return "error"
