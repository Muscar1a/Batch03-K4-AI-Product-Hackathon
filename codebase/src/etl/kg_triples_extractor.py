"""
KG Triples Extractor Module (Deep Mining Engine)
Trích xuất Triples & Entities sâu từ 286+ Thread JSON và kênh Discord.
Hỗ trợ:
- Extract Thread & Channel Structure ((Thread) - [HAS_TITLE] -> (Title))
- Domain Entity Extraction (LangGraph, RAG, ReAct, AI Log, Vlearn, MCP, Labs, Checkpoints...)
- Resource URL Mining ((Thread/User) - [SHARES_RESOURCE_URL] -> (URL))
- User Question & Solution Intent Mining
- Ẩn danh hóa người dùng (User_Anon_XXXX)
- Trích dẫn Cấp 2 (Direct Discord Link: https://discord.com/channels/{guild}/{channel}/{msg})
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class Triple(BaseModel):
    subject: str = Field(..., description="Thực thể chủ thể")
    relation: str = Field(..., description="Mối quan hệ")
    object: str = Field(..., description="Thực thể đối tượng")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Metadata & Trích dẫn chứng minh")


class Entity(BaseModel):
    name: str = Field(..., description="Tên thực thể")
    category: str = Field(..., description="Phân loại thực thể (LOGISTICS, TECH_TOOL, CONCEPT, THREAD, USER, RESOURCE)")
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

DOMAIN_KEYWORDS = {
    "LangGraph": "TECH_TOOL", "FastAPI": "TECH_TOOL", "Claude": "TECH_TOOL", "Codex": "TECH_TOOL",
    "Cursor": "TECH_TOOL", "Antigravity": "TECH_TOOL", "Kiro": "TECH_TOOL", "OpenCode": "TECH_TOOL",
    "Phoenix": "TECH_TOOL", "Jira": "TECH_TOOL", "Trello": "TECH_TOOL", "Roboflow": "TECH_TOOL",
    "YOLO": "TECH_TOOL", "ReAct": "CONCEPT", "RAG": "CONCEPT", "MCP": "CONCEPT",
    "NotebookLM": "TECH_TOOL", "Edge AI": "CONCEPT", "Transformer": "CONCEPT",
    "Synthea": "TECH_TOOL", "Vibe Coding": "CONCEPT", "Responsible AI": "CONCEPT",
    "Prompt Injection": "CONCEPT", "AI Log": "LOGISTICS", "Codelabs": "PLATFORM",
    "Vlearn": "PLATFORM", "Checkpoint": "LOGISTICS", "Rubric": "LOGISTICS"
}


def anonymize_user_id(author_info: Dict[str, Any]) -> str:
    """Ẩn danh hóa người dùng để bảo mật thông tin cá nhân."""
    if not isinstance(author_info, dict):
        return "User_Anon_0000"
    raw_id = str(author_info.get("id") or author_info.get("name") or "unknown_user")
    hashed = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:6].upper()
    return f"User_Anon_{hashed}"


def build_citation_proof(msg: Dict[str, Any]) -> Dict[str, Any]:
    """Xây dựng trích dẫn chứng minh Cấp 2 (Direct Discord Link) cho tin nhắn."""
    msg_id = str(msg.get("id", ""))
    channel_id = str(msg.get("channel_id") or msg.get("_channel_id") or "1527920177390293164")
    guild_id = str(msg.get("guild_id") or msg.get("_guild_id") or "1526532830627102781")
    content = msg.get("content", "")
    channel_name = msg.get("_channel_name", "")
    file_name = msg.get("_file_name", "")

    discord_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}" if msg_id else None

    return {
        "message_id": msg_id,
        "file_name": file_name,
        "channel_name": channel_name,
        "proof_snippet": content[:150].replace("\n", " ").strip(),
        "citation_level": "Level2_Direct_Discord_Link",
        "discord_url": discord_url
    }


def extract_triples_from_message(msg: Dict[str, Any]) -> List[Triple]:
    """Trích xuất Triples phong phú từ một tin nhắn."""
    content = msg.get("content", "")
    author_info = msg.get("author", {})
    anon_user = anonymize_user_id(author_info)
    citation_attr = build_citation_proof(msg)
    channel_name = msg.get("_channel_name", "")
    
    triples = []
    
    # 1. Trích xuất Domain Entities xuất hiện trong tin nhắn
    for kw, cat in DOMAIN_KEYWORDS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", content, re.IGNORECASE):
            triples.append(Triple(
                subject=anon_user,
                relation="DISCUSSED_TOPIC",
                object=kw,
                attributes=citation_attr
            ))

    # 2. Trích xuất các liên kết URL/Tài nguyên được chia sẻ
    urls = re.findall(r"https?://[^\s>]+", content)
    for url in urls[:3]: # Giới hạn tối đa 3 link mỗi tin nhắn
        # Làm sạch đuôi link nếu bị dính dấu câu
        clean_url = url.rstrip(".,;)\"']")
        triples.append(Triple(
            subject=anon_user,
            relation="SHARED_RESOURCE_URL",
            object=clean_url,
            attributes=citation_attr
        ))

    # 3. Trích xuất Thắc mắc / Câu hỏi của User
    if "?" in content or re.search(r"cho em hỏi|cho mình hỏi|thắc mắc|lỗi|sao|thế nào|khi nào|ở đâu|giúp", content, re.IGNORECASE):
        cp_match = re.search(r"(cp[1-6]|checkpoint\s*[1-6])", content, re.IGNORECASE)
        if cp_match:
            cp_name = cp_match.group(1).upper().replace("CHECKPOINT ", "CP")
            triples.append(Triple(
                subject=anon_user,
                relation="ASKED_DEADLINE_FOR",
                object=cp_name,
                attributes=citation_attr
            ))
        elif re.search(r"ai\s*log", content, re.IGNORECASE):
            triples.append(Triple(
                subject=anon_user,
                relation="ENCOUNTERED_ISSUE",
                object="AI_Log_Issue",
                attributes=citation_attr
            ))
        elif re.search(r"điểm danh|qr|vlearn|codelabs", content, re.IGNORECASE):
            triples.append(Triple(
                subject=anon_user,
                relation="INQUIRED_ABOUT",
                object="Vlearn_Attendance_Platform",
                attributes=citation_attr
            ))

    # 4. Trích xuất Bài chia sẻ kinh nghiệm / Solution
    if "chia-sẻ" in channel_name.lower() or "bài-học" in channel_name.lower():
        if len(content) > 100 or re.search(r"hướng dẫn|mẹo|tip|solution|cách|quy trình", content, re.IGNORECASE):
            triples.append(Triple(
                subject=anon_user,
                relation="PROVIDED_COMMUNITY_SOLUTION",
                object=f"Guide_{channel_name[:25]}",
                attributes=citation_attr
            ))

    return triples


def extract_thread_triples(file_data: Dict[str, Any], file_name: str) -> List[Triple]:
    """
    Trích xuất Triples cấu trúc từ Metadata của từng Thread Discord (286+ Thread JSON).
    """
    channel_info = file_data.get("channel", {})
    thread_name = channel_info.get("name", "")
    category = channel_info.get("category", "")
    thread_id = str(channel_info.get("id", ""))
    
    if not thread_name:
        return []
        
    thread_entity = f"Thread_{thread_id}" if thread_id else f"Thread_{hashlib.md5(thread_name.encode()).hexdigest()[:6]}"
    
    triples = []
    # Thread Metadata
    triples.append(Triple(
        subject=thread_entity,
        relation="HAS_TITLE",
        object=thread_name,
        attributes={"file_name": file_name, "category": category}
    ))
    
    if category:
        triples.append(Triple(
            subject=thread_entity,
            relation="BELONGS_TO_CATEGORY",
            object=category,
            attributes={"file_name": file_name}
        ))
        
    # Phát hiện các từ khóa chủ đề chính trong Tiêu đề Thread
    for kw, cat in DOMAIN_KEYWORDS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", thread_name, re.IGNORECASE):
            triples.append(Triple(
                subject=thread_entity,
                relation="COVERS_TOPIC",
                object=kw,
                attributes={"file_name": file_name, "category": category}
            ))

    return triples


def extract_triples_from_corpus(messages: List[Dict[str, Any]], raw_files_data: Optional[List[Tuple[Dict[str, Any], str]]] = None, include_ground_truth: bool = True) -> ExtractionResult:
    """
    Trích xuất toàn bộ Triples từ danh sách tin nhắn Discord + Thread Metadata.
    """
    result = ExtractionResult()
    
    if include_ground_truth:
        result.triples.extend(KNOWLEDGE_RULES)

    # 1. Mining Thread Metadata từ raw files
    if raw_files_data:
        for fdata, fname in raw_files_data:
            thread_triples = extract_thread_triples(fdata, fname)
            result.triples.extend(thread_triples)

    # 2. Mining Message Level Triples
    seen = set()
    for msg in messages:
        extracted = extract_triples_from_message(msg)
        for t in extracted:
            msg_id = t.attributes.get("message_id", "")
            key = (t.subject, t.relation, t.object, msg_id)
            if key not in seen:
                seen.add(key)
                result.triples.append(t)

    # 3. Tổng hợp danh sách Entities duy nhất
    entity_dict = {}
    for t in result.triples:
        for ent_name in [t.subject, t.object]:
            if ent_name not in entity_dict:
                category = "LOGISTICS" if ent_name.startswith("CP") else (
                    "USER" if ent_name.startswith("User_Anon_") else (
                        "THREAD" if ent_name.startswith("Thread_") else "TECH_CONCEPT"
                    )
                )
                entity_dict[ent_name] = Entity(name=ent_name, category=category)

    result.entities = list(entity_dict.values())
    return result
