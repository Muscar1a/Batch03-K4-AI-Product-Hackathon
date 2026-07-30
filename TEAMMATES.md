# TEAMMATES.md — Danh Sách Thành Viên & Phân Công Nhiệm Vụ (Nhóm 01 - Zone 01)

Dự án: **OdysseyBot — Trợ Lý Logistics & Hỏi Đáp Học Viên AI (Discord Bot)**  
Thuộc: **AI20K Build Phase — Cohort 3 & 4 (Batch03-K4-AI-Product-Hackathon)**

---

## 👥 Phân Công Nhiệm Vụ Chi Tiết (Team Assignments)

### 1. Thành viên 1: Thành An (`01017`) — Data Engine & Triples Mining (Role 1)
- **Thư mục & File Code Phụ Trách**: `codebase/src/etl/` (`discord_cleaner.py`, `kg_triples_extractor.py`), `codebase/src/odysseybot/ingestion/`
- **Nhiệm vụ Kỹ thuật Chuyên sâu**:
  - Viết regex & LLM cleaning pipeline lọc 2.658 tin nhắn rác từ `💬-chung` và 285 file `discord-crawl`.
  - Lập trình module trích xuất Entities & Triples `(Subject, Relation, Object)` bằng Pydantic.
- **Nhiệm vụ Non-Tech Chia Đều (1/3)**:
  - Phụ trách phần §1 & §2 trong `spec.md` (Evidence Mining, Problem Statement, Bảng Impact 3 ứng viên).
  - Phỏng vấn & User Test với 2 người thử ngoài nhóm.

---

### 2. Thành viên 2: Phạm Quốc Thanh (`2A202601407`) — Team Lead & Graph Database & Dynamic Memory (Role 2)
- **Thư mục & File Code Phụ Trách**: `codebase/src/graph_db/` (`graph_store.py`, `memory_store.py`), `codebase/src/odysseybot/knowledge/`
- **Nhiệm vụ Kỹ thuật Chuyên sâu**:
  - Lập trình Knowledge Graph Storage Engine (NetworkX/SQLite) hỗ trợ thuật toán truy vấn đa chặng (2-hop graph traversal).
  - Xây dựng **Dynamic Memory Engine** tự động trích xuất & persistence User Facts dài hạn vào `data/memory_store.json`.
- **Nhiệm vụ Non-Tech Chia Đều (1/3)**:
  - Phụ trách phần §3, §4 & §5 trong `spec.md` (Benchmark, Automation cost-of-error, HAX/PAIR, 4 lớp chỗ khó).
  - Phỏng vấn & User Test với 2 người thử ngoài nhóm.

---

### 3. Thành viên 3: Vũ Quang Nhật (`02038`) — LangGraph Agent Engine & Bot Integration (Role 3)
- **Thư mục & File Code Phụ Trách**: `codebase/src/agent/`, `codebase/src/main.py`, `codebase/src/odysseybot/app.py`, `eval/` (`golden_set.json`)
- **Nhiệm vụ Kỹ thuật Chuyên sâu**:
  - Cài đặt **LangGraph State Machine** (`ChatbotState`, Memory Extractor Node, Router Node, KG Retriever Node, Synthesizer Node).
  - Lập trình **Tool Call Node & Sub-Agent Dispatcher** (Web Search, Update KB, Git check).
  - Tích hợp Discord Bot Python (`codebase/src/main.py`) & script test tự động Golden set.
- **Nhiệm vụ Non-Tech Chia Đều (1/3)**:
  - Phụ trách phần §6, §7 & §9 trong `spec.md` (4 đường đi trải nghiệm, Quality bar, Golden set, Changelog).
  - Soạn Slide 6 trang & hỗ trợ kịch bản Demo.
