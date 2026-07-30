import pytest
from pathlib import Path
from odysseybot.config import Settings
from odysseybot.domain.models import AskRequest

def test_settings_validation():
    s = Settings(DCE_SYNC_ENABLED=False)
    assert s.DCE_SYNC_ENABLED is False

def test_ask_request_model():
    req = AskRequest(
        user_id="user1",
        guild_id="guild1",
        channel_id="chan1",
        thread_id=None,
        message_id="msg1",
        text="Hạn nộp CP4 khóa 4 khi nào?",
    )
    assert req.user_id == "user1"
    assert req.text == "Hạn nộp CP4 khóa 4 khi nào?"
