"""
KG Triples Extractor Module
Trích xuất Thực thể (Entities) và Mối quan hệ (Triples: Subject - Relation - Object) từ dữ liệu Discord đã làm sạch.
"""

import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Triple(BaseModel):
    subject: str = Field(..., description="Thực thể chủ thể (Subject Entity)")
    relation: str = Field(..., description="Mối quan hệ (Predicate / Relation)")
    object: str = Field(..., description="Thực thể đối tượng (Object Entity)")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Các thuộc tính bổ sung (Confidence, Source, Channel)")


class Entity(BaseModel):
    name: str = Field(..., description="Tên thực thể")
    category: str = Field(..., description="Phân loại (LOGISTICS, TECH_ISSUE, PLATFORM, USER)")
    attributes: Dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    triples: List[Triple] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)


# Tri thức cố định quy chuẩn từ BTC (Ground Truth Rules)
KNOWLEDGE_RULES = [
    # Deadlines Checkpoint Khóa 3
    Triple(subject="CP1", relation="HAS_DEADLINE_COHORT_3", object="10:00 Ngày 1", attributes={"source": "BTC Grounding"}),
    Triple(subject="CP2", relation="HAS_DEADLINE_COHORT_3", object="12:00 Ngày 1", attributes={"source": "BTC Grounding"}),
    Triple(subject="CP3", relation="HAS_DEADLINE_COHORT_3", object="16:00 Ngày 1", attributes={"source": "BTC Grounding"}),
    Triple(subject="CP4", relation="HAS_DEADLINE_COHORT_3", object="17:30 Ngày 1 (Spec chốt 23:59)", attributes={"source": "BTC Grounding"}),
    Triple(subject="CP5", relation="HAS_DEADLINE_COHORT_3", object="09:00 Ngày 2", attributes={"source": "BTC Grounding"}),
    Triple(subject="CP6", relation="HAS_DEADLINE_COHORT_3", object="10:00 Ngày 2", attributes={"source": "BTC Grounding"}),

    # Deadlines Checkpoint Khóa 4
    Triple(subject="CP1", relation="HAS_DEADLINE_COHORT_4", object="15:00 Ngày 1", attributes={"source": "BTC Grounding"}),
    Triple(subject="CP2", relation="HAS_DEADLINE_COHORT_4", object="17:00 Ngày 1", attributes={"source": "BTC Grounding"}),
    Triple(subject="CP3", relation="HAS_DEADLINE_COHORT_4", object="10:30 Ngày 2", attributes={"source": "BTC Grounding"}),
    Triple(subject="CP4", relation="HAS_DEADLINE_COHORT_4", object="12:00 Ngày 2 (Spec chốt 23:59 Ngày 1)", attributes={"source": "BTC Grounding"}),
    Triple(subject="CP5", relation="HAS_DEADLINE_COHORT_4", object="14:00 Ngày 2", attributes={"source": "BTC Grounding"}),
    Triple(subject="CP6", relation="HAS_DEADLINE_COHORT_4", object="15:00 Ngày 2", attributes={"source": "BTC Grounding"}),

    # Technical Rules
    Triple(subject="AI_Log", relation="REQUIRES_HOOK", object="git pre-push hook", attributes={"source": "BTC Grounding"}),
    Triple(subject="Antigravity_IDE", relation="USES_LOG_PATH", object=".system_generated/logs/overview.txt", attributes={"source": "Discord Community Solution"}),
    Triple(subject="Vlearn", relation="PROVIDES_URL", object="https://vlearn.dev", attributes={"source": "BTC Grounding"}),
    Triple(subject="Codelabs", relation="PROVIDES_URL", object="https://codelabs.vlearn.dev", attributes={"source": "BTC Grounding"}),
]


def extract_triples_from_message(msg: Dict[str, Any]) -> List[Triple]:
    """
    Trích xuất các Triples từ 1 tin nhắn Discord dựa trên Regex Rules.
    """
    content = msg.get("content", "")
    author_info = msg.get("author", {})
    author_name = author_info.get("nickname") or author_info.get("name", "User")
    channel_name = msg.get("_channel_name", "")
    
    triples = []
    
    # 1. Trích xuất thắc mắc về lỗi AI Log
    if re.search(r"lỗi.*ai.*log|ai.*log.*lỗi|fix.*ai.*log|antigravity.*log", content, re.IGNORECASE):
        triples.append(Triple(
            subject=f"User_{author_name}",
            relation="ENCOUNTERED_ISSUE",
            object="AI_Log_Scan_Issue",
            attributes={"channel": channel_name, "snippet": content[:100]}
        ))
        
    # 2. Trích xuất câu hỏi deadline CP
    cp_match = re.search(r"(cp[1-6]|checkpoint\s*[1-6])", content, re.IGNORECASE)
    if cp_match and re.search(r"hạn|deadline|mấy giờ|khi nào", content, re.IGNORECASE):
        cp_name = cp_match.group(1).upper().replace("CHECKPOINT ", "CP")
        triples.append(Triple(
            subject=f"User_{author_name}",
            relation="ASKED_DEADLINE_FOR",
            object=cp_name,
            attributes={"channel": channel_name, "snippet": content[:100]}
        ))
        
    # 3. Trích xuất thắc mắc điểm danh / QR / Vlearn
    if re.search(r"điểm danh|qr|vlearn|codelabs", content, re.IGNORECASE):
        triples.append(Triple(
            subject=f"User_{author_name}",
            relation="INQUIRED_ABOUT",
            object="Vlearn_Attendance_Platform",
            attributes={"channel": channel_name, "snippet": content[:100]}
        ))

    # 4. Trích xuất giải pháp được chia sẻ trong kênh #chia-sẻ
    if "chia-sẻ" in channel_name.lower() or "bài-học" in channel_name.lower():
        if re.search(r"fix|sửa lỗi|hướng dẫn|mẹo|tip|solution", content, re.IGNORECASE):
            triples.append(Triple(
                subject=f"Community_Share_{channel_name[:20]}",
                relation="OFFERS_SOLUTION",
                object="Discord_Community_Tip",
                attributes={"author": author_name, "snippet": content[:150]}
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
            key = (t.subject, t.relation, t.object)
            if key not in seen:
                seen.add(key)
                result.triples.append(t)

    # Thống kê danh sách thực thể duy nhất
    entity_dict = {}
    for t in result.triples:
        for ent_name in [t.subject, t.object]:
            if ent_name not in entity_dict:
                category = "LOGISTICS" if ent_name.startswith("CP") else ("USER" if ent_name.startswith("User_") else "TECH_ISSUE")
                entity_dict[ent_name] = Entity(name=ent_name, category=category)

    result.entities = list(entity_dict.values())
    return result
