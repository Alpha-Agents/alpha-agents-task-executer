# services/openrouter_client.py

import sys
from pathlib import Path
import json
sys.path.append(str(Path(__file__).resolve().parent.parent))
import re
import requests
from config import MODEL_NAME, CONSENSUS_MODEL, OPENROUTER_API_KEY, OPENROUTER_ENDPOINT, MAX_TOKENS

def query_openrouter(messages, specified_model = None):

    if specified_model is None:
        model = MODEL_NAME
    else:
        model = specified_model

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": MAX_TOKENS
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }
    response = requests.post(OPENROUTER_ENDPOINT, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    content = result.get("choices", [{}])[0].get("message", {}).get("content")
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                return part.get("text")
        return str(content)
    elif isinstance(content, str):
        return content
    else:
        return str(content)

def query_conversation(conversation_history, image_urls, specified_model=None):
    """
    Builds the conversation payload including the conversation history and image URLs.
    Returns the assistant's text response.
    """
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
    """
    Filters the conversation history to remove image-only messages and the final assistant response,
    ensuring the conversation ends with a user message. Uses the consensus model for the final query.
    """
    print("Generating consensus...")

    filtered_history = []
    # Keep only messages with string content.
    for msg in conversation_history:
        if isinstance(msg["content"], str):
            filtered_history.append({"role": msg["role"], "content": msg["content"]})
    
    # If the conversation ends with an assistant message, remove it.
    if filtered_history and filtered_history[-1]["role"] == "assistant":
        filtered_history.pop()
    
    # Ensure that the conversation ends with a user message.
    if not filtered_history or filtered_history[-1]["role"] != "user":
        # Find the last user message in the original history and append it.
        for msg in reversed(conversation_history):
            if msg["role"] == "user":
                filtered_history.append({"role": "user", "content": msg["content"]})
                break

    # Build the message payload.
    messages = []
    for msg in filtered_history:
        messages.append({
            "role": msg["role"],
            "content": [{"type": "text", "text": msg["content"]}]
        })

    return query_openrouter(messages, specified_model=CONSENSUS_MODEL)