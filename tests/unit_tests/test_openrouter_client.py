import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path to allow absolute import resolution
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from trading_view_extension.services.openrouter_client import (
    query_openrouter,
    query_conversation,
    get_consensus,
    get_structured_trade_signal,
    TradeSignal
)

MOCK_RESPONSE_JSON = {
    "choices": [{
        "message": {
            "content": '{"asset": "AAPL", "action": "BUY", "entry_price": 150.0, "stop_loss": 145.0, "take_profit": 160.0, "confidence": 8.5, "R2R": 2.0}'
        }
    }],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 50
    }
}

class TestOpenRouterClient(unittest.TestCase):

    @patch("trading_view_extension.services.openrouter_client.requests.post")
    def test_query_openrouter_returns_expected_content_and_credits(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_RESPONSE_JSON
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": [{"type": "text", "text": "Buy AAPL at 150"}]}]
        content, credits = query_openrouter(messages)

        self.assertIn("AAPL", content)
        self.assertIsInstance(credits, int)

    @patch("trading_view_extension.services.openrouter_client.requests.post")
    def test_get_structured_trade_signal_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_RESPONSE_JSON
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        user_text = "Buy AAPL at 150, stop loss 145, take profit 160"
        data, credits = get_structured_trade_signal(user_text, asset="AAPL")

        self.assertIsInstance(data, dict)
        self.assertEqual(data["asset"], "AAPL")
        self.assertEqual(data["action"], "BUY")
        self.assertEqual(data["entry_price"], 150.0)
        self.assertIsInstance(credits, int)

    @patch("trading_view_extension.services.openrouter_client.requests.post")
    def test_query_conversation_constructs_message_and_calls_api(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_RESPONSE_JSON
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        conversation_history = [
            {"role": "user", "content": "What is your trade signal?"},
            {"role": "assistant", "content": "I'm not sure yet."},
        ]
        image_urls = ["https://example.com/image1.png"]

        content, credits = query_conversation(conversation_history, image_urls)

        self.assertIsInstance(content, str)
        self.assertIn("AAPL", content)
        self.assertIsInstance(credits, int)

    @patch("trading_view_extension.services.openrouter_client.requests.post")
    def test_get_consensus_filters_and_calls_api(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_RESPONSE_JSON
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        convo_history = [
            {"role": "user", "content": "Should I buy Tesla?"},
            {"role": "assistant", "content": "Maybe."},
            {"role": "user", "content": "Tell me why."},
        ]

        content, credits = get_consensus(convo_history)
        self.assertIn("AAPL", content)
        self.assertIsInstance(credits, int)

    def test_trade_signal_model_validation(self):
        valid_data = {
            "asset": "MSFT",
            "action": "BUY",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
            "confidence": 9,
            "R2R": 2.5
        }
        signal = TradeSignal(**valid_data)
        self.assertEqual(signal.asset, "MSFT")
        self.assertEqual(signal.action, "BUY")

if __name__ == '__main__':
    unittest.main()
