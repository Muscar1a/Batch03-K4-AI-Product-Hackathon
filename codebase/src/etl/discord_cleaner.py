"""
Discord Cleaner Module
Lọc & làm sạch tin nhắn nhiễu (tin nhắn cụt, bot command, tin nhắn rác) từ dữ liệu Discord thô.
"""

import re
from typing import List, Dict, Any

def is_noise_message(content: str) -> bool:
    """Kiểm tra tin nhắn có phải nhiễu/rác hay không."""
    if not content or not content.strip():
        return True
    
    cleaned = content.strip().lower()
    
    # 1. Lọc tin nhắn quá ngắn hoặc câu chào ngắn không mang giá trị thông tin
    noise_patterns = [r"^hi$", r"^hello$", r"^\.$", r"^hey$", r"^ok$", r"^được$", r"^dạ$", r"^cảm ơn$"]
    for pat in noise_patterns:
        if re.match(pat, cleaned):
            return True
            
    # 2. Lọc các câu lệnh bot hệ thống ngắn
    if cleaned.startswith("!") and len(cleaned.split()) <= 1:
        return True
        
    return False

def clean_discord_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Làm sạch danh sách tin nhắn Discord thô."""
    cleaned = []
    for msg in messages:
        content = msg.get("content", "")
        if not is_noise_message(content):
            cleaned.append(msg)
    return cleaned
