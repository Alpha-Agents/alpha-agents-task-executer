import sys
from pathlib import Path
import json
import requests
import logging
from tenacity import retry, wait_exponential, stop_after_attempt, before_sleep
from pydantic import BaseModel, Field, ValidationError
# Ensure parent is in path to access config
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import MODEL_NAME, CONSENSUS_MODEL, OPENROUTER_API_KEY, OPENROUTER_ENDPOINT, MAX_TOKENS

logger = logging.getLogger("openrouter_client")


def log_retry(retry_state):
    logger.warning(f"Retrying OpenRouter API call (attempt {retry_state.attempt_number})...")


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    before_sleep=log_retry
)
def query_openrouter(messages, specified_model=None):
    
    model = specified_model or MODEL_NAME

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": MAX_TOKENS
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }

    response = requests.post(OPENROUTER_ENDPOINT, headers=headers, json=payload, timeout=15)
    response.raise_for_status()

    result = response.json()
    if model == MODEL_NAME:
        cost_usd = (result["usage"]["prompt_tokens"] * 0.000003 + result["usage"]["completion_tokens"] * 0.000015)
        credits = round(cost_usd*1000)
    else:
        cost_usd = (result["usage"]["prompt_tokens"]  * 0.0005 + result["usage"]["completion_tokens"] * 0.0015) / 1000
        credits = round(cost_usd * 1000)
    logger.info(f"{model} Price: {cost_usd}  Credits: {round(cost_usd*1000)} Usage: {result['usage']}")
    content = result.get("choices", [{}])[0].get("message", {}).get("content")

    if not content:
        logger.error(f"Received empty response from OpenRouter: {result}")
        return "AI Error: Empty Response", 0

    if isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                return part.get("text"), credits
        return str(content), credits

    if isinstance(content, str):
        return content, credits

    return str(content),credits


def query_conversation(conversation_history, image_urls, specified_model=None):
    messages = []
    for msg in conversation_history:
        messages.append({
            "role": msg["role"],
            "content": [{"type": "text", "text": msg["content"]}]
        })
    if image_urls:
        messages.append({
            "role": "user",
            "content": [{"type": "image_url", "image_url": {"url": url}} for url in image_urls]
        })

    return query_openrouter(messages, specified_model)


def get_consensus(conversation_history):
    logger.info("Generating consensus based on conversation history.")

    filtered_history = []
    for msg in conversation_history:
        if isinstance(msg["content"], str):
            filtered_history.append({"role": msg["role"], "content": msg["content"]})

    if filtered_history and filtered_history[-1]["role"] == "assistant":
        logger.info("Removing trailing assistant message before consensus generation.")
        filtered_history.pop()

    if not filtered_history or filtered_history[-1]["role"] != "user":
        for msg in reversed(conversation_history):
            if msg["role"] == "user":
                filtered_history.append({"role": "user", "content": msg["content"]})
                break

    messages = []
    for msg in filtered_history:
        messages.append({
            "role": msg["role"],
            "content": [{"type": "text", "text": msg["content"]}]
        })

    return query_openrouter(messages, specified_model=CONSENSUS_MODEL)

class TradeSignal(BaseModel):
    asset: str = Field(..., description="The asset or stock symbol, ex: XYZ")
    action: str = Field(..., description="The trade action: BUY, SELL, WAIT, EXIT (if user is in a trade this is an option)")
    entry_price: float | None = Field(None, description="The entry price if applicable")
    stop_loss: float | None = Field(None, description="Stop loss price if applicable")
    take_profit: float | None = Field(None, description="Take profit price if applicable")
    confidence: float | None = Field(None, description="Confidence level from 0 to 10")
    R2R: float | None = Field(None, description="Risk to reward value")

def get_structured_trade_signal(user_text: str, asset: str, specified_model=None) -> tuple[dict | None, int]:
    """
    Calls OpenRouter to get a trade signal from user input and parses it into the TradeSignal model.
    Returns (parsed_data_dict, credits_used) or (None, 0) if failed.
    """
    messages = [
        {"role": "system", "content": [{"type": "text", "text": "Extract a structured trade signal from the user message. Use the following JSON structure as a template:\n\n" + json.dumps(TradeSignal.model_json_schema(), indent=2)}]},
        {"role": "user", "content": [{"type": "text", "text": user_text}]}
    ]

    content, credits = query_openrouter(messages, specified_model="openai/o3-mini")

    try:
        # Parse raw JSON string first
        parsed_json = json.loads(content)

        # Validate with Pydantic
        signal = TradeSignal(**parsed_json)

        return signal.model_dump(), credits

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse content as JSON: {e}\nContent: {content}")
    except ValidationError as ve:
        logger.error(f"Validation error: {ve}\nContent: {content}")
    except Exception as ex:
        logger.error(f"Unexpected error: {ex}")

    return None, credits
