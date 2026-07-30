"""
Discord Cleaner Module
Lọc & làm sạch tin nhắn nhiễu (tin nhắn cụt, bot command, tin nhắn rác, tài khoản bot) từ dữ liệu Discord thô.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple


NOISE_PATTERNS = [
    r"^hi+$", r"^hello+$", r"^\.+$", r"^hey+$", r"^ok+$", r"^oki+$", r"^okay$",
    r"^được$", r"^dạ$", r"^cảm ơn$", r"^cảm ơn ạ$", r"^tks$", r"^thanks$", r"^thank u$",
    r"^vâng$", r"^hóng$", r"^\+1$", r"^bot$", r"^tin nhắn này đã bị xóa$", r"^deleted message$"
]

def is_noise_message(msg: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Kiểm tra tin nhắn có phải nhiễu/rác hay không.
    Trả về: (is_noise: bool, reason: str)
    """
    if not isinstance(msg, dict):
        return True, "invalid_format"

    # 1. Lọc bot tài khoản tự động
    author = msg.get("author", {})
    if isinstance(author, dict) and author.get("isBot", False):
        return True, "bot_author"

    content = msg.get("content", "")
    if not content or not content.strip():
        # Kiểm tra xem có attachments hay không, nếu không có chữ lẫn attachment thì là noise
        attachments = msg.get("attachments", [])
        if not attachments:
            return True, "empty_content"
        return False, "attachment_only"

    cleaned = content.strip().lower()

    # 2. Lọc các câu chào hỏi / từ đệm quá ngắn
    for pat in NOISE_PATTERNS:
        if re.match(pat, cleaned):
            return True, "noise_pattern_match"

    # 3. Lọc các câu lệnh bot ngắn (!cmd, /cmd)
    if (cleaned.startswith("!") or cleaned.startswith("/")) and len(cleaned.split()) <= 1:
        return True, "short_bot_command"

    # 4. Lọc tin nhắn chỉ chứa ký tự đặc biệt hoặc quá ngắn (< 3 ký tự) không chứa từ quan trọng
    if len(cleaned) < 3 and not re.search(r"[a-z0-9àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]", cleaned):
        return True, "too_short_symbols"

    return False, "valid"


def clean_discord_messages(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Làm sạch danh sách tin nhắn Discord thô.
    Trả về (danh_sách_tin_sạch, bảng_thống_kê).
    """
    cleaned = []
    stats = {
        "total": len(messages),
        "kept": 0,
        "filtered_bot": 0,
        "filtered_noise": 0,
        "filtered_empty": 0
    }

    for msg in messages:
        is_noise, reason = is_noise_message(msg)
        if is_noise:
            if reason == "bot_author":
                stats["filtered_bot"] += 1
            elif reason == "empty_content":
                stats["filtered_empty"] += 1
            else:
                stats["filtered_noise"] += 1
        else:
            cleaned.append(msg)
            stats["kept"] += 1

    return cleaned, stats


def load_and_clean_json_file(file_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Đọc một file JSON Discord export và trả về danh sách tin nhắn đã làm sạch.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    channel_info = data.get("channel", {})
    raw_messages = data.get("messages", [])

    cleaned_msgs, stats = clean_discord_messages(raw_messages)
    
    metadata = {
        "file_name": file_path.name,
        "channel_name": channel_info.get("name", "Unknown"),
        "category": channel_info.get("category", "General"),
        "stats": stats
    }
    
    # Gắn thêm channel metadata vào từng tin nhắn để phục vụ trích xuất triples
    for m in cleaned_msgs:
        m["_channel_name"] = channel_info.get("name", "")
        m["_category"] = channel_info.get("category", "")
        m["_file_name"] = file_path.name

    return cleaned_msgs, metadata
