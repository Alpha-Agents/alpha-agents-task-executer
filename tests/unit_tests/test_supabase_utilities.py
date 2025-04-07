import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
# Import the functions under test
from trading_view_extension.database.db_utilities import (
    conversation_exists,
    update_trade_signal,
    get_conversation_by_id,
    add_message,
    add_conversation,
    deduct_user_credits
)

# Patch the global supabase client
@pytest.fixture(autouse=True)
def mock_supabase():
    with patch("trading_view_extension.database.db_utilities.supabase") as mock:
        yield mock


def test_conversation_exists_found(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value.data = [{"job_id": "123"}]
    assert conversation_exists("123") is True


def test_conversation_exists_not_found(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value.data = []
    assert conversation_exists("999") is False


def test_update_trade_signal_updates_if_exists(mock_supabase):
    # conversation exists
    mock_supabase.table().select().eq().limit().execute.return_value.data = [{"job_id": "abc"}]
    update_trade_signal("abc", "BUY")
    mock_supabase.table().update.assert_called_once_with({"trade_signal": "BUY"})


def test_get_conversation_by_id_success(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value.data = [{
        "conversation_history": ["hi", "hello"]
    }]
    result = get_conversation_by_id("abc")
    assert result == ["hi", "hello"]


def test_get_conversation_by_id_failure(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value.data = []
    with pytest.raises(ValueError, match="No conversation found for job_id abc"):
        get_conversation_by_id("abc")


# def test_add_message_success(mock_supabase):
#     mock_supabase.table().select().eq().limit().execute.return_value.data = [{
#         "conversation_history": ["hi"]
#     }]
#     add_message("abc", "new msg")
#     mock_supabase.table().update.assert_called_once()
#     args, kwargs = mock_supabase.table().update.call_args
#     assert "new msg" in kwargs["conversation_history"]


def test_add_message_no_conversation(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value.data = []
    with pytest.raises(ValueError):
        add_message("abc", "msg")


def test_add_conversation_new(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value.data = []
    add_conversation("job123", ["hello"], "test@example.com", "AAPL", "agentX")
    mock_supabase.table().insert.assert_called_once()


def test_add_conversation_already_exists(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value.data = [{"job_id": "job123"}]
    add_conversation("job123", ["hi"], "user@example.com", "TSLA", "agentY")
    mock_supabase.table().insert.assert_not_called()


def test_deduct_user_credits_all_from_extra(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value.data = [{
        "monthly_credits": 100,
        "extra_credits": 50
    }]
    deduct_user_credits("test@example.com", 20)
    mock_supabase.table().update.assert_called_once_with({
        "extra_credits": 30,
        "monthly_credits": 100
    })


def test_deduct_user_credits_split_credits(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value.data = [{
        "monthly_credits": 100,
        "extra_credits": 10
    }]
    deduct_user_credits("test@example.com", 30)
    mock_supabase.table().update.assert_called_once_with({
        "extra_credits": 0,
        "monthly_credits": 80
    })


def test_deduct_user_credits_user_not_found(mock_supabase):
    mock_supabase.table().select().eq().limit().execute.return_value.data = []
    with pytest.raises(ValueError, match="No user found with email: test@example.com"):
        deduct_user_credits("test@example.com", 10)
