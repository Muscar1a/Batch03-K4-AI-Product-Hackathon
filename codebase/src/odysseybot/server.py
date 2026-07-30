"""FastAPI Local Test Server for OdysseyBot local debugging and evaluation."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from odysseybot.domain.models import AskRequest
from odysseybot.agent.assistant import GroundedAssistant

app = FastAPI(title="OdysseyBot Local Test Server")
assistant = GroundedAssistant()


class QueryPayload(BaseModel):
    user_id: str = "test_user_01"
    guild_id: str = "1526532830627102781"
    channel_id: str = "1527920177390293164"
    text: str


class CitationOut(BaseModel):
    source_type: str
    title: str
    url: str
    excerpt: str
    authority: str


class ResponsePayload(BaseModel):
    text: str
    intent: str
    confidence: float
    status: str
    escalated: bool
    citations: List[CitationOut]


@app.get("/")
def health_check():
    return {"status": "ok", "service": "OdysseyBot Local Test Endpoint"}


@app.post("/ask", response_model=ResponsePayload)
async def ask_endpoint(payload: QueryPayload):
    req = AskRequest(
        user_id=payload.user_id,
        guild_id=payload.guild_id,
        channel_id=payload.channel_id,
        thread_id=None,
        message_id="local_test_msg",
        text=payload.text,
    )
    answer = await assistant.answer(req)
    return ResponsePayload(
        text=answer.text,
        intent=answer.intent,
        confidence=answer.confidence,
        status=answer.status,
        escalated=answer.escalated,
        citations=[
            CitationOut(
                source_type=c.source_type,
                title=c.title,
                url=c.url,
                excerpt=c.excerpt,
                authority=c.authority,
            )
            for c in answer.citations
        ],
    )
