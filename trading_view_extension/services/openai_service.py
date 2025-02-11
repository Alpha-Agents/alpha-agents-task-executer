import sys
import os
import json
import time
from pathlib import Path
from openai import OpenAI
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config import MODEL, API_KEY
import re

class OpenAIService:
    
    def __init__(self, client=None, model=MODEL):
        self.model = model
        self.client = OpenAI(api_key=API_KEY) if client is None else client

    def wait_for_run(self, run_id: str, thread_id: str) -> dict:
        """Wait for a run to complete and return the assistant's response in JSON format."""
        try:
            while True:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )

                if run_status.status == 'completed':
                    # Retrieve and parse the latest assistant message as JSON
                    return self.get_latest_assistant_message(thread_id)

                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    return {"error": f"Run failed with status '{run_status.status}'."}

                time.sleep(0.25)
        except Exception as e:
            return {"error": f"Error while waiting for run: {str(e)}"}

    def get_latest_assistant_message(self, thread_id: str) -> dict:
        """Retrieve the latest assistant message and parse it into JSON format."""
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
                ).strip()

                if not response_text:
                    return {"error": "AI returned an empty response."}

                # Remove markdown formatting if present
                cleaned_text = re.sub(r'```json|```', '', response_text).strip()

                # Fix invalid single quotes and parse JSON
                cleaned_text = cleaned_text.replace("'", '"')  # Convert single quotes to double quotes

                try:
                    return json.loads(cleaned_text)
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON format returned by AI.", "raw_response": cleaned_text}

        return {"error": "No assistant response received."}


    def send_user_message(self, thread_id: str, content, role: str = "user"):
        """Send a user or system message to the specified thread in JSON format."""
        if isinstance(content, dict):  # Convert dictionary to JSON string
            content = json.dumps(content)

        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content
        )

    def create_text_run(self, thread_id: str, assistant_id: str, max_tokens: int) -> str:
        """Create a run for text completion and return run_id."""
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            model=self.model,
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
            return f"Error checking run status: {e}"
