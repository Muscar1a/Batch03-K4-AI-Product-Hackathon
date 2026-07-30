# TEAMMATES.md — Danh Sách & Phân Công Nhiệm Vụ Thành Viên Nhóm 01 (Zone 01)

Dự án: **OdysseyBot — Trợ Lý Logistics & Hỏi Đáp Học Viên AI (Discord Bot)**  
Thuộc: **AI20K Build Phase — Cohort 3 & 4 (Batch03-K4-AI-Product-Hackathon)**

---

## 👥 Danh Sách Thành Viên & Vai Trò (Team Composition)

### 1. Phạm Quốc Thanh (`2A202601407`) — Team Lead & Full-Stack System Engineer (Role 2)
- **Phân vùng Kỹ thuật**: `codebase/src/odysseybot/agent/`, `codebase/src/odysseybot/app.py`, `codebase/src/odysseybot/server.py`, `codebase/src/odysseybot/config.py`
- **Nhiệm vụ Kỹ thuật**:
  - **Tối ưu Prompt & Kiến trúc Hệ thống**: Thiết kế và tinh chỉnh `system_prompt` qua các phiên bản (v0 $\rightarrow$ v3), xây dựng quy tắc routing ngắn gọn, boundary xác nhận yes_no, và quy tắc gọi tool song song (parallel tool execution).
  - **FastAPI Live Server & ReAct Engine**: Xây dựng backend server (`server.py`), xử lý ReAct 2 vòng (2-Round ReAct Synthesis) lọc bỏ suy nghĩ nội bộ của LLM, quản lý cơ sở dữ liệu và State Graph.
  - **Giao diện Web B2C & Metrics**: Phát triển giao diện NEO Research Agent (Resonant UI 2027 Pitch Black theme, Lucide SVG vector objects, ReactMarkdown synthesis renderer, hộp suy luận Agent Thinking, chỉ số TTFT & Latency).
  - **Knowledge Graph Database & Dynamic Memory Engine** (`graph_db/` & `memory_store.py`): Lập trình Knowledge Graph Engine (NetworkX/SQLite) hỗ trợ thuật toán truy vấn đa chặng (2-hop graph traversal), tự động trích xuất và lưu trữ User Facts dài hạn.
- **Nhiệm vụ Non-Tech (1/3)**: Phụ trách các mục §3, §4 & §5 trong `spec.md` (Benchmark, Automation cost-of-error, HAX/PAIR, 4 lớp chỗ khó), phỏng vấn và User Test với người dùng thử nghiệm.

---

### 2. Thành An (`01017`) — Tool & Integration Specialist (Role 1)
- **Phân vùng Kỹ thuật**: `codebase/src/odysseybot/ingestion/`, `codebase/src/odysseybot/adapters/`, `artifacts/tools.yaml`, `tools/`
- **Nhiệm vụ Kỹ thuật**:
  - **Chuẩn hóa Tool Declarations**: Viết mô tả tiếng Việt chi tiết cho toàn bộ công cụ trong `artifacts/tools.yaml` (mapping tên $\rightarrow$ handle X/Twitter, định dạng ngày tháng, giới hạn từ khóa).
  - **Phát triển Công cụ Mới**: Phát triển `reddit_search` tool (`tools/reddit_search/`) và weather OpenWeatherMap API tool (`tools/weather/`).
  - **Data Engine & Triples Mining** (`ingestion/`, `dce_adapter.py`, `archive_sync.py`): Xây dựng pipeline lọc dữ liệu nhiễu từ các file Discord crawl, lập trình module trích xuất Entities & Triples nguyên tử (`Subject, Relation, Object`).
  - **Tài liệu & Hướng dẫn Môi trường**: Viết `TOOL-SETUP.md` và hỗ trợ cấu hình môi trường chạy provider API.
- **Nhiệm vụ Non-Tech (1/3)**: Phụ trách các mục §1 & §2 trong `spec.md` (Evidence Mining, Problem Statement, Bảng Impact 3 ứng viên), hỗ trợ User Test nhóm.

---

### 3. Vũ Quang Nhật (`02038`) — Evaluation Suite & Benchmark Engineer (Role 3)
- **Phân vùng Kỹ thuật**: `eval/`, `data/eval_group.json`, `run_eval.py`, `codebase/tests/`
- **Nhiệm vụ Kỹ thuật**:
  - **Thiết kế Bộ Test Case Đánh giá Nhóm**: Xây dựng toàn bộ 10 test case chuyên sâu trong `data/eval_group.json` (5 kịch bản single-turn + 5 kịch bản multi-turn).
  - **Đánh giá & Kiểm thử Benchmark**: Thực thi bộ đánh giá v3-group (`run_eval.py`), xác minh độ chính xác routing 100% (10/10 PASS), phân tích log failure và đối soát kết quả.
  - **LangGraph Agent Engine & Bot Integration**: Kiểm thử LangGraph State Machine, tích hợp Discord Bot Python runner (`app.py`), xây dựng bộ test tự động Golden set (`test_edge_cases.py`).
- **Nhiệm vụ Non-Tech (1/3)**: Phụ trách các mục §6, §7 & §9 trong `spec.md` (4 đường đi trải nghiệm, Quality bar, Golden set, Changelog), soạn slide 6 trang và hỗ trợ kịch bản demo.
