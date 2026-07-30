# Prototype Codebase

Thư mục chứa toàn bộ mã nguồn prototype của dự án Trợ lý Học viên AI.

## Cấu trúc thư mục
- `src/main.py`: Discord Bot & CLI Interface chính.
- `src/config.py`: Cấu hình môi trường.
- `src/agent/`: Bộ não LangGraph State Machine (`state.py`, `nodes.py`, `tools.py`, `graph.py`).
- `src/etl/`: Pipeline làm sạch dữ liệu Discord & trích xuất đố thị tri thức (`discord_cleaner.py`, `kg_triples_extractor.py`).
- `src/graph_db/`: Engine lưu trữ Knowledge Graph DB & Bộ nhớ động (`graph_store.py`, `memory_store.py`).

## Trạng thái các phần (Working / Mock)
| Hợp phần | Trạng thái | Ghi chú |
|---|---|---|
| **Discord Interface & Command Handler** | `Working` | Chạy trực tiếp CLI test hoặc Discord Bot thật khi có DISCORD_TOKEN |
| **Logic Phân loại 4 Lớp Thách Thức** | `Working` | Phân loại chính xác câu hỏi mơ hồ, câu hỏi ngoài thẩm quyền và tra cứu grounding |
| **LangGraph State Machine** | `Working` | Tự động fallback nếu môi trường chưa cài gói `langgraph` |
| **Knowledge Graph Storage Engine** | `Working` | Truy vấn NetworkX / In-memory Triple store |
| **ETL Discord Cleaner & Triples Extractor** | `Working` | Lọc tin rác & extract quan hệ |
| **Sub-Agent Tools (Web Search, Git Check, VLearn API)** | `Mock` | Giả lập response từ các dịch vụ bên thứ ba |
