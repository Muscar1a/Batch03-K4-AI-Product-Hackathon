"""Durable, user-scoped conversation facts for the prototype bot."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


class MemoryStoreCorruptionError(ValueError):
    """Raised when persisted user memory cannot be safely loaded."""


FACT_TYPES = {"OS", "GROUP", "STUCK_ISSUE", "PREFERENCE"}


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", value.strip())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class MemoryStore:
    SCHEMA_VERSION = "1.0"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self.users: dict[str, dict[str, list[dict[str, object]]]] = {}
        if self.path.exists():
            self.load()

    def load(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("memory store root must be an object")
            if payload.get("schema_version") != self.SCHEMA_VERSION or not isinstance(payload.get("users"), dict):
                raise ValueError("unsupported schema or missing users object")
            users: dict[str, dict[str, list[dict[str, object]]]] = {}
            for user_id, record in payload["users"].items():
                if not isinstance(user_id, str) or not isinstance(record, Mapping) or not isinstance(record.get("facts"), list):
                    raise ValueError("invalid user record")
                facts = []
                for fact in record["facts"]:
                    normalized = self._canonical_fact(fact, require_timestamps=True)
                    facts.append(normalized)
                users[user_id] = {"facts": facts}
            self.users = users
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise MemoryStoreCorruptionError(f"cannot load memory store {self.path}: {exc}") from exc

    @staticmethod
    def _canonical_fact(fact: Mapping[str, object], require_timestamps: bool = False) -> dict[str, object]:
        if not isinstance(fact, Mapping):
            raise ValueError("fact must be an object")
        fact_type = _normalize(str(fact.get("fact_type", ""))).upper()
        value = fact.get("value")
        if fact_type not in FACT_TYPES:
            raise ValueError(f"unsupported fact_type: {fact_type}")
        if not isinstance(value, str) or not _normalize(value):
            raise ValueError("fact value must be a non-empty string")
        created_at = fact.get("created_at", fact.get("timestamp"))
        updated_at = fact.get("updated_at", created_at)
        if require_timestamps and not isinstance(created_at, str):
            raise ValueError("fact is missing created_at")
        confidence = fact.get("confidence", 1.0)
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be a number between 0 and 1")
        if not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1:
            raise ValueError("confidence must be a number between 0 and 1")
        return {
            "fact_type": fact_type,
            "value": _normalize(value),
            "created_at": created_at or _now(),
            "updated_at": updated_at or _now(),
            "source": _normalize(str(fact.get("source", "user_message"))) or "user_message",
            "confidence": float(confidence),
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": self.SCHEMA_VERSION, "users": self.users}
        fd, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def add_fact(self, user_id: str, fact: Mapping[str, object]) -> bool:
        user_id = _normalize(user_id)
        if not user_id:
            raise ValueError("user_id must be non-empty")
        normalized = self._canonical_fact(fact)
        key = (normalized["fact_type"], normalized["value"].casefold())
        with self._lock:
            record = self.users.setdefault(user_id, {"facts": []})
            for existing in record["facts"]:
                if (existing["fact_type"], existing["value"].casefold()) == key:
                    existing["updated_at"] = _now()
                    if normalized["confidence"] >= existing["confidence"]:
                        existing["source"] = normalized["source"]
                        existing["confidence"] = normalized["confidence"]
                    self.save()
                    return False
            record["facts"].append(normalized)
            self.save()
            return True

    def extract_facts(self, text: str) -> list[dict[str, object]]:
        text = _normalize(text)
        if not text:
            return []
        facts: list[dict[str, object]] = []
        os_match = re.search(r"\b(windows|macos|mac|ubuntu|linux)\b", text, re.IGNORECASE)
        if os_match:
            os_name = os_match.group(1).lower()
            facts.append({"fact_type": "OS", "value": "macOS" if os_name in {"mac", "macos"} else os_name.title()})
        group_match = re.search(r"(?:nh[oó]m\s*)?\bG?\s*(\d{1,3})\b", text, re.IGNORECASE)
        if group_match and (re.search(r"\bG\s*\d", text, re.IGNORECASE) or re.search(r"nh[oó]m\s*\d", text, re.IGNORECASE)):
            facts.append({"fact_type": "GROUP", "value": f"G{group_match.group(1)}"})
        issue_match = re.search(r"(?:b[iị] lỗi|gặp lỗi|đang kẹt|không .{1,50}? được)\s*[:\-]?\s*([^.!?\n]{1,120})", text, re.IGNORECASE)
        if issue_match:
            issue = _normalize(issue_match.group(1)).strip(" ,;:")
            if issue and not issue.casefold() in {"lỗi", "error"}:
                facts.append({"fact_type": "STUCK_ISSUE", "value": issue})
        return facts

    def remember_from_text(self, user_id: str, text: str) -> list[dict[str, object]]:
        facts = self.extract_facts(text)
        for fact in facts:
            self.add_fact(user_id, fact)
        return facts

    def get_facts(self, user_id: str, fact_type: str | None = None) -> list[dict[str, object]]:
        record = self.users.get(_normalize(user_id), {"facts": []})
        facts = record["facts"]
        if fact_type is not None:
            fact_type = _normalize(fact_type).upper()
            if fact_type not in FACT_TYPES:
                raise ValueError(f"unsupported fact_type: {fact_type}")
            facts = [fact for fact in facts if fact["fact_type"] == fact_type]
        return [dict(fact) for fact in facts]

    def remove_fact(self, user_id: str, fact_type: str, value: str) -> bool:
        user_id = _normalize(user_id)
        fact_type = _normalize(fact_type).upper()
        value = _normalize(value).casefold()
        with self._lock:
            record = self.users.get(user_id)
            if not record:
                return False
            before = len(record["facts"])
            record["facts"] = [
                fact for fact in record["facts"] if not (fact["fact_type"] == fact_type and fact["value"].casefold() == value)
            ]
            changed = len(record["facts"]) != before
            if changed:
                self.save()
            return changed

    def clear_user(self, user_id: str) -> bool:
        with self._lock:
            changed = _normalize(user_id) in self.users
            if changed:
                del self.users[_normalize(user_id)]
                self.save()
            return changed
