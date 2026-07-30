"""
KG Triples Extractor Module
Trích xuất Thực thể (Entities) và Mối quan hệ (Triples: Subject - Relation - Object) từ dữ liệu Discord đã làm sạch.
Hỗ trợ Ẩn danh hóa Người dùng (User Anonymization) & Chiến lược Trích dẫn Động (Dynamic Citation Strategy):
- Cấp 2 (Direct Discord URL): Nếu tin nhắn mới (≤ 3 ngày).
- Cấp 3 (Anonymized Proof Snippet): Nếu tin nhắn cũ (> 3 ngày) để tránh trôi tin nhắn.
"""

import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Triple(BaseModel):
    subject: str = Field(..., description="Thực thể chủ thể (Subject Entity)")
    relation: str = Field(..., description="Mối quan hệ (Predicate / Relation)")
    object: str = Field(..., description="Thực thể đối tượng (Object Entity)")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Thông tin trích dẫn nguồn (citation_level, message_id, proof_url, proof_snippet)")


class Entity(BaseModel):
    name: str = Field(..., description="Tên thực thể (Ví dụ: CP4, User_Anon_A1B2)")
    category: str = Field(..., description="Phân loại (LOGISTICS, TECH_ISSUE, PLATFORM, USER)")
    attributes: Dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    triples: List[Triple] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)


# Tri thức cố định quy chuẩn từ BTC (Ground Truth Rules)
KNOWLEDGE_RULES = [
    # Deadlines Checkpoint Khóa 3
    Triple(subject="CP1", relation="HAS_DEADLINE_COHORT_3", object="10:00 Ngày 1", attributes={"citation_level": "Grounding", "proof_document": "04-rubric.md §Phần 3"}),
    Triple(subject="CP2", relation="HAS_DEADLINE_COHORT_3", object="12:00 Ngày 1", attributes={"citation_level": "Grounding", "proof_document": "04-rubric.md §Phần 3"}),
    Triple(subject="CP3", relation="HAS_DEADLINE_COHORT_3", object="16:00 Ngày 1", attributes={"citation_level": "Grounding", "proof_document": "04-rubric.md §Phần 3"}),
    Triple(subject="CP4", relation="HAS_DEADLINE_COHORT_3", object="17:30 Ngày 1 (Spec chốt 23:59)", attributes={"citation_level": "Grounding", "proof_document": "01-de-bai.md & 04-rubric.md"}),
    Triple(subject="CP5", relation="HAS_DEADLINE_COHORT_3", object="09:00 Ngày 2", attributes={"citation_level": "Grounding", "proof_document": "04-rubric.md §Phần 3"}),
    Triple(subject="CP6", relation="HAS_DEADLINE_COHORT_3", object="10:00 Ngày 2", attributes={"citation_level": "Grounding", "proof_document": "04-rubric.md §Phần 3"}),

    # Deadlines Checkpoint Khóa 4
    Triple(subject="CP1", relation="HAS_DEADLINE_COHORT_4", object="15:00 Ngày 1", attributes={"citation_level": "Grounding", "proof_document": "04-rubric.md §Phần 3"}),
    Triple(subject="CP2", relation="HAS_DEADLINE_COHORT_4", object="17:00 Ngày 1", attributes={"citation_level": "Grounding", "proof_document": "04-rubric.md §Phần 3"}),
    Triple(subject="CP3", relation="HAS_DEADLINE_COHORT_4", object="10:30 Ngày 2", attributes={"citation_level": "Grounding", "proof_document": "04-rubric.md §Phần 3"}),
    Triple(subject="CP4", relation="HAS_DEADLINE_COHORT_4", object="12:00 Ngày 2 (Spec chốt 23:59 Ngày 1)", attributes={"citation_level": "Grounding", "proof_document": "01-de-bai.md & 04-rubric.md"}),
    Triple(subject="CP5", relation="HAS_DEADLINE_COHORT_4", object="14:00 Ngày 2", attributes={"citation_level": "Grounding", "proof_document": "04-rubric.md §Phần 3"}),
    Triple(subject="CP6", relation="HAS_DEADLINE_COHORT_4", object="15:00 Ngày 2", attributes={"citation_level": "Grounding", "proof_document": "04-rubric.md §Phần 3"}),

    # Technical Rules
    Triple(subject="AI_Log", relation="REQUIRES_HOOK", object="git pre-push hook", attributes={"citation_level": "Grounding", "proof_document": "README.md §Luật chung"}),
    Triple(subject="Antigravity_IDE", relation="USES_LOG_PATH", object=".system_generated/logs/overview.txt", attributes={"citation_level": "Community Solution", "proof_document": "Thread 1530640010825699328"}),
    Triple(subject="Vlearn", relation="PROVIDES_URL", object="https://vlearn.dev", attributes={"citation_level": "Grounding", "proof_document": "README.md"}),
    Triple(subject="Codelabs", relation="PROVIDES_URL", object="https://codelabs.vlearn.dev", attributes={"citation_level": "Grounding", "proof_document": "README.md"}),
]


def anonymize_user_id(author_info: Dict[str, Any]) -> str:
    """
    Ẩn danh hóa người dùng để bảo mật thông tin cá nhân.
    Tạo mã dạng User_Anon_XXXX.
    """
    if not isinstance(author_info, dict):
        return "User_Anon_0000"
    raw_id = str(author_info.get("id") or author_info.get("name") or "unknown_user")
    hashed = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:6].upper()
    return f"User_Anon_{hashed}"


def build_citation_proof(msg: Dict[str, Any], reference_time: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Xây dựng chiến lược trích dẫn chứng minh động:
    - Nếu tin nhắn trong vòng 3 ngày: Chọn Cấp 2 (Link URL Discord trực tiếp)
    - Nếu tin nhắn > 3 ngày (bị trôi xa): Chọn Cấp 3 (Mã ẩn danh + Snippet trích dẫn gốc)
    """
    msg_id = str(msg.get("id", ""))
    channel_id = str(msg.get("channel_id") or msg.get("_channel_id") or "")
    guild_id = str(msg.get("guild_id") or "1526532830627102781")
    content = msg.get("content", "")
    channel_name = msg.get("_channel_name", "")
    file_name = msg.get("_file_name", "")

    # Tính độ tuổi tin nhắn
    ts_str = msg.get("timestamp")
    is_recent = False
    
    if ts_str:
        try:
            # Format: 2026-07-26T01:16:56.497+07:00
            msg_dt = datetime.fromisoformat(ts_str)
            ref_dt = reference_time or datetime.now(timezone.utc)
            if msg_dt.tzinfo is None:
                msg_dt = msg_dt.replace(tzinfo=timezone.utc)
            if ref_dt.tzinfo is None:
                ref_dt = ref_dt.replace(tzinfo=timezone.utc)
                
            age_days = abs((ref_dt - msg_dt).total_seconds()) / 86400.0
            if age_days <= 3.0:
                is_recent = True
        except Exception:
            is_recent = False

    citation_attr = {
        "message_id": msg_id,
        "file_name": file_name,
        "channel_name": channel_name,
        "proof_snippet": content[:120].replace("\n", " ").strip()
    }

    # Chọn cấp độ chứng minh
    if is_recent and channel_id and msg_id:
        citation_attr["citation_level"] = "Level2_Direct_Discord_Link"
        citation_attr["discord_url"] = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
        citation_attr["note"] = "Tin nhắn gần (≤3 ngày) -> Dẫn link Discord trực tiếp"
    else:
        citation_attr["citation_level"] = "Level3_Anonymized_Proof_Snippet"
        citation_attr["discord_url"] = None
        citation_attr["note"] = "Tin nhắn đã lâu (>3 ngày) -> Dùng trích dẫn bằng chứng ẩn danh trong Audit Log"

    return citation_attr


def extract_triples_from_message(msg: Dict[str, Any]) -> List[Triple]:
    """
    Trích xuất Triples từ 1 tin nhắn Discord với chiến lược trích dẫn Cấp 2 hoặc Cấp 3.
    """
    content = msg.get("content", "")
    author_info = msg.get("author", {})
    anon_user = anonymize_user_id(author_info)
    
    citation_attr = build_citation_proof(msg)
    channel_name = msg.get("_channel_name", "")
    
    triples = []
    
    # 1. Trích xuất thắc mắc về lỗi AI Log
    if re.search(r"lỗi.*ai.*log|ai.*log.*lỗi|fix.*ai.*log|antigravity.*log", content, re.IGNORECASE):
        triples.append(Triple(
            subject=anon_user,
            relation="ENCOUNTERED_ISSUE",
            object="AI_Log_Scan_Issue",
            attributes=citation_attr
        ))
        
    # 2. Trích xuất câu hỏi deadline CP
    cp_match = re.search(r"(cp[1-6]|checkpoint\s*[1-6])", content, re.IGNORECASE)
    if cp_match and re.search(r"hạn|deadline|mấy giờ|khi nào", content, re.IGNORECASE):
        cp_name = cp_match.group(1).upper().replace("CHECKPOINT ", "CP")
        triples.append(Triple(
            subject=anon_user,
            relation="ASKED_DEADLINE_FOR",
            object=cp_name,
            attributes=citation_attr
        ))
        
    # 3. Trích xuất thắc mắc điểm danh / QR / Vlearn
    if re.search(r"điểm danh|qr|vlearn|codelabs", content, re.IGNORECASE):
        triples.append(Triple(
            subject=anon_user,
            relation="INQUIRED_ABOUT",
            object="Vlearn_Attendance_Platform",
            attributes=citation_attr
        ))

    # 4. Trích xuất giải pháp được chia sẻ từ cộng đồng
    if "chia-sẻ" in channel_name.lower() or "bài-học" in channel_name.lower():
        if re.search(r"fix|sửa lỗi|hướng dẫn|mẹo|tip|solution", content, re.IGNORECASE):
            triples.append(Triple(
                subject=f"Community_Share_{channel_name[:20]}",
                relation="OFFERS_SOLUTION",
                object="Discord_Community_Tip",
                attributes=citation_attr
            ))

    return triples


def extract_triples_from_corpus(messages: List[Dict[str, Any]], include_ground_truth: bool = True) -> ExtractionResult:
    """
    Trích xuất toàn bộ Triples từ danh sách tin nhắn Discord đã làm sạch.
    """
    result = ExtractionResult()
    
    if include_ground_truth:
        result.triples.extend(KNOWLEDGE_RULES)

    seen = set()
    for msg in messages:
        extracted = extract_triples_from_message(msg)
        for t in extracted:
            key = (t.subject, t.relation, t.object, t.attributes.get("message_id", ""))
            if key not in seen:
                seen.add(key)
                result.triples.append(t)

    # Thống kê danh sách thực thể duy nhất
    entity_dict = {}
    for t in result.triples:
        for ent_name in [t.subject, t.object]:
            if ent_name not in entity_dict:
                category = "LOGISTICS" if ent_name.startswith("CP") else ("USER" if ent_name.startswith("User_Anon_") else "TECH_ISSUE")
                entity_dict[ent_name] = Entity(name=ent_name, category=category)

    result.entities = list(entity_dict.values())
    return result
