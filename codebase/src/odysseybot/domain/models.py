"""Data models and interfaces for OdysseyBot Assistant."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional


@dataclass(frozen=True)
class AskRequest:
    user_id: str
    guild_id: str
    channel_id: str
    thread_id: Optional[str]
    message_id: str
    text: str


@dataclass(frozen=True)
class Citation:
    source_type: Literal[
        "STAFF_DISCORD",
        "LEARNER_DISCORD",
        "OFFICIAL_DOCUMENT",
        "TECHNICAL_WEB",
    ]

    title: str
    url: str
    excerpt: str
    authority: str
    source_timestamp: Optional[datetime] = None


@dataclass(frozen=True)
class Answer:
    text: str
    intent: str
    confidence: float
    citations: List[Citation]
    status: str
    escalated: bool
    knowledge_freshness: datetime
    tools_used: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SyncResult:
    run_id: str
    status: str  # 'success', 'failed', 'degraded'
    file_count: int
    message_count: int
    error_message: Optional[str] = None


@dataclass(frozen=True)
class SyncStatus:
    enabled: bool
    last_successful_sync: Optional[datetime]
    is_running: bool
    thread_count: int
    discovery_degraded: bool
