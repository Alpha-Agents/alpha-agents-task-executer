import openai
from openai import OpenAI, AssistantEventHandler
from typing_extensions import override
from typing import List, Dict

class ImageAnalysisEventHandler(AssistantEventHandler):
    """
    Collects the streaming text from the assistant and stores it
    in self.final_text so that we can return it later.
    """
    def __init__(self):
        super().__init__()
        self._accumulated_text = ""

    @override
    def on_text_delta(self, delta, snapshot):
        # Append partial text tokens to a string buffer
        self._accumulated_text += delta.value

    def get_final_text(self):
        return self._accumulated_text


def analyze_images(
    assistant_id: str,
    image_urls: List[str],
    openai_api_key: str
) -> List[Dict[str, str]]:
    """
    Analyzes a list of images using an Assistant with vision capabilities.
    Returns a list of { "image_url": ..., "analysis": ... } dictionaries.
    """

    # 1) Set up the client
    openai.api_key = openai_api_key
    client = OpenAI(api_key = openai_api_key)

    # 2) Create a brand new Thread
    thread = client.beta.threads.create()

    # 3) Prepare a container for the results
    results = []

    # 4) Iterate over each image
    for idx, url in enumerate(image_urls, start=1):
        # Add the user message referencing the image
        user_message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=[
                {
                    "type": "text",
                    "text": f"Please describe image #{idx} in detail."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": url,
                        "detail": "auto"  # can be "high", "low", or "auto"
                    }
                }
            ]
        )

        # 5) Create an event handler to gather the final text from the assistant
        event_handler = ImageAnalysisEventHandler()

        # 6) Create a Run to get the Assistant's response, streaming behind the scenes
        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=assistant_id,
            event_handler=event_handler
        ) as run_stream:
            # Wait for the run to finish
            run_stream.until_done()

        # 7) Get the final assembled text from the event handler
        final_analysis = event_handler.get_final_text()

        # 8) Append to results
        results.append({
            "image_url": url,
            "analysis": final_analysis.strip()
        })

    return results