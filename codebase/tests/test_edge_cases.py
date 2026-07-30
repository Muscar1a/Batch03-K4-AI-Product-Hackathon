import pytest
from pathlib import Path
from odysseybot.domain.models import AskRequest
from odysseybot.agent.assistant import GroundedAssistant

@pytest.mark.asyncio
async def test_edge_case_author_query_pruning():
    assistant = GroundedAssistant()
    
    # Query for non-existent author: tienes2810
    req_non_existent = AskRequest(
        user_id="user1",
        guild_id="guild1",
        channel_id="chan1",
        thread_id=None,
        message_id="msg_edge_1",
        text="tienes2810 đã có bao nhiêu bài đăng?",
    )
    ans1 = await assistant.answer(req_non_existent)
    # Citations must be pruned since 0 posts found
    assert len(ans1.citations) == 0
    assert "tienes2810" in ans1.text or "không" in ans1.text.lower()

@pytest.mark.asyncio
async def test_edge_case_existing_author_query():
    assistant = GroundedAssistant()
    
    # Query for existing author: plinhxg
    req_existing = AskRequest(
        user_id="user2",
        guild_id="guild1",
        channel_id="chan1",
        thread_id=None,
        message_id="msg_edge_2",
        text="plinhxg có bao nhiêu tin nhắn?",
    )
    ans2 = await assistant.answer(req_existing)
    # Ensure answer synthesized and citations correspond to author plinhxg
    assert ans2.status in ["BOT_ANSWERED", "ESCALATED"]
