# KẾ HOẠCH KỸ THUẬT CHI TIẾT — NHIỆM VỤ 3 (TASK 3)
## LangGraph Agent Engine, Tool Execution, Discord Integration & Golden Set Evaluation

> 📌 **Phạm vi kế hoạch**: Tập trung 100% vào **Kỹ thuật (Technical Design & Code Implementation)** cho Thành viên 3. Bỏ qua các nội dung Non-Tech (Slide, Spec §6/7/9).

---

## 1. BẢNG THUẬT NGỮ & KHÁI NIỆM KỸ THUẬT (TECHNICAL GLOSSARY)

| Thuật ngữ / Key Word | Giải thích ngắn gọn & Dễ hiểu |
|---|---|
| **LangGraph State Machine** | Bộ khung quản lý hội thoại dưới dạng "Máy trạng thái". Mỗi lượt chat đi qua các Nút (Node) xử lý dữ liệu và Chuyển hướng (Edge) theo logic điều kiện. |
| **ChatbotState** | Một Dictionary tập trung chứa toàn bộ dữ liệu của lượt chat hiện tại (tin nhắn, user_id, intent, ngữ cảnh KG trích xuất được, kết quả gọi tool, đáp án cuối). |
| **Node (Nút xử lý)** | Một hàm Python nhận `ChatbotState`, thực hiện xử lý (ví dụ: phân loại intent, trích xuất fact, tra cứu graph DB) và trả về dữ liệu cập nhật state. |
| **Conditional Edge (Nhánh rẽ điều kiện)** | Logic rẽ nhánh giữa các Node. Ví dụ: Nếu `intent == "TECH_BUG"` thì rẽ sang Node Tra cứu Graph DB, nếu `intent == "EXECUTE_TOOL"` thì rẽ sang Tool Node. |
| **Memory Extractor Node** | Nút chuyên phân tích câu thoại của User để "rút ra" các Facts cá nhân (như Hệ điều hành Windows/Mac, Nhóm G14, Lỗi AI Log) và lưu dài hạn vào Knowledge Graph DB. |
| **KG Retriever Node (2-Hop Traversal)** | Nút truy vấn dữ liệu đồ thị qua 2 chặng liên kết (ví dụ: `User -> Lỗi AI Log -> Solution -> File hướng dẫn`) để lấy câu trả lời chính xác nhất. |
| **Answer Synthesizer & Grounding** | Nút tổng hợp câu trả lời cuối cùng từ thông tin KG/Tool, ép LLM phải trích dẫn rõ nguồn gốc tài liệu (Grounding theo chuẩn HAX G2), kiên quyết từ chối nếu không có căn cứ. |
| **Tool Execution & Sub-Agent Dispatcher** | Nút thực thi các công cụ ngoại vi (Web Search, Git Check, API) khi KGDB chưa có sẵn câu trả lời. |
| **Golden Set Evaluation** | Bộ 20 kịch bản câu hỏi mẫu đi kèm đáp án mong muốn + Script test tự động đo độ chính xác (Quality Bar ≥ 90%). |

---

## 2. KIẾN TRÚC KỸ THUẬT & LUỒNG DỮ LIỆU (AGENT ARCHITECTURE)

```mermaid
graph TD
    User([Discord User / Console Input]) --> MainPy[src/main.py - Discord Async Event Loop]
    MainPy --> StateInit[Init ChatbotState]
    
    subgraph LangGraph Core State Machine (src/agent/)
        StateInit --> ExtractorNode[1. Memory Extractor & Router Node]
        ExtractorNode -->|Save Dynamic Facts| MemoryEngine[(Memory Store / KGDB)]
        
        ExtractorNode --> RoutingRule{Check Intent}
        
        RoutingRule -->|LOGISTICS / TECH_BUG| KGNode[2. KG Retriever Node]
        RoutingRule -->|EXECUTE_TOOL| ToolNode[3. Tool Execution Node]
        RoutingRule -->|AMBIGUOUS| ClarifyNode[4. Clarification Node]
        RoutingRule -->|OUT_OF_SCOPE| RefuseNode[5. Scope Guardrail Node]
        
        KGNode -->|Fetch 2-hop Context| GraphEngine[(Knowledge Graph Store)]
        ToolNode -->|Run Search / API| Tools[External Tools: Web Search, Git, Vlearn]
        
        KGNode --> Synthesizer[6. Answer Synthesizer Node]
        ToolNode --> Synthesizer
        ClarifyNode --> Synthesizer
        RefuseNode --> Synthesizer
    end
    
    Synthesizer --> MainPyOutput[Return Final Response + Citations]
    MainPyOutput --> User
```

---

## 3. DANH SÁCH FILE KỸ THUẬT CẦN TRIỂN KHAI

| File Path | Vai trò & Trách nhiệm Kỹ thuật |
|---|---|
| `src/agent/state.py` | Định nghĩa kiểu dữ liệu `ChatbotState` (TypedDict) chuẩn hóa luồng thông tin. |
| `src/agent/tools.py` | Định nghĩa danh sách các công cụ (@tool) cho Agent: Web Search, Git Repo Checker, Vlearn API. |
| `src/agent/nodes.py` | Lập trình 6 hàm Node xử lý core logic: Memory Extract, Routing, KG Traversal, Tool Exec, Clarification, Synthesis. |
| `src/agent/graph.py` | Khởi tạo `StateGraph`, nối các Nodes và Conditional Edges, compile ra `app` runnable. |
| `src/main.py` | Tích hợp Discord Bot Python (`discord.py`), xử lý sự kiện `on_message` async và CLI fallback test mode. |
| `eval/golden_set.json` | Chứa 20 test cases phân theo 4 lớp rủi ro & câu hỏi logistics. |
| `eval/run_eval.py` | Script Python chạy tự động 20 cases, so sánh kết quả và tính accuracy score. |

---

## 4. CÁC BƯỚC THỰC HIỆN TUẦN TỰ (STEP-BY-STEP IMPLEMENTATION PLAN)

### BƯỚC 1: Xây Dựng Data Contract & State (`src/agent/state.py`)
- Khởi tạo file `src/agent/state.py`.
- Định nghĩa struct `UserFact` và `ChatbotState` bằng `TypedDict`.

```python
from typing import TypedDict, List, Dict, Any, Optional

class UserFact(TypedDict):
    fact_type: str  # OS, GROUP, ISSUE, PREFERENCE
    value: str
    timestamp: str

class ChatbotState(TypedDict):
    messages: List[Dict[str, str]]
    user_id: str
    extracted_user_facts: List[UserFact]
    intent: str  # LOGISTICS, TECH_BUG, EXECUTE_TOOL, AMBIGUOUS, OUT_OF_SCOPE
    target_tool: Optional[str]
    kg_triples: List[Dict[str, Any]]
    retrieved_context: str
    final_response: str
    citations: List[str]
```

---

### BƯỚC 2: Định Nghĩa Các Công Cụ Ngoại Vi (`src/agent/tools.py`)
- Lập trình các công cụ bổ trợ bằng `@tool` decorator của LangChain:
  1. `web_search_tool(query: str)`: Tra cứu thông tin cập nhật ngoài internet khi KG chưa có.
  2. `github_repo_checker_tool(repo_url: str)`: Kiểm tra tình trạng commit AI Log trên GitHub.
  3. `vlearn_api_tool(student_id: str)`: Kiểm tra trạng thái điểm danh QR / Codelabs.
  4. `update_knowledge_base_tool(topic: str, content: str)`: Cho phép admin bổ sung thông tin quy định mới.

---

### BƯỚC 3: Lập Trình Bộ Các Node Core Logic (`src/agent/nodes.py`)
Lập trình 6 Node chính:
1. `memory_extractor_and_router_node`:
   - Phân tích câu thoại bằng Regex / LLM Parser.
   - Phát hiện fact cá nhân (VD: "mình dùng Windows", "nhóm G14") $\rightarrow$ lưu vào `extracted_user_facts`.
   - Phân loại `intent` của câu hỏi.
2. `kg_retriever_node`:
   - Kết hợp `user_id` context (từ memory) và từ khóa câu hỏi.
   - Gọi `graph_store.search()` để lấy quan hệ 2-hop (Ví dụ: `Windows -> AI Log Error -> Sửa qua overview.txt`).
3. `tool_execution_node`:
   - Chạy công cụ được chọn trong `target_tool` và cập nhật `retrieved_context`.
4. `clarification_node`:
   - Xử lý khi `intent == "AMBIGUOUS"`. Đưa ra câu hỏi gợi ý HAX G10 ("Bạn đang hỏi mốc CP mấy và thuộc Khóa 3 hay Khóa 4?").
5. `guardrail_refusal_node`:
   - Xử lý khi `intent == "OUT_OF_SCOPE"`. Từ chối giải bài tập / soi code theo chuẩn HAX G8.
6. `answer_synthesizer_node`:
   - Tổng hợp `retrieved_context` + Quy định BTC.
   - Tạo `final_response` kèm danh sách `citations` (Ví dụ: `[Nguồn: 04-rubric.md §Phần 3]`).

---

### BƯỚC 4: Biên Dịch State Graph (`src/agent/graph.py`)
- Nhập các Nodes từ `nodes.py`.
- Tạo `workflow = StateGraph(ChatbotState)`.
- Đăng ký các Nodes: `workflow.add_node(...)`.
- Thêm `conditional_edges` xuất phát từ `router` node để rẽ nhánh chuẩn xác.
- Gọi `app = workflow.compile()`.

---

### BƯỚC 5: Tích Hợp Discord Bot & Async Handler (`src/main.py`)
- Cập nhật [src/main.py](file:///D:/AI%20Thuc%20Chien/K3-hackathon-odysseybot-E402/src/main.py):
  - Khởi tạo Discord `Client(intents=intents)`.
  - Trong `on_message(message)`:
    - Bỏ qua tin nhắn của chính Bot.
    - Lọc lệnh `!hoi <query>` hoặc `@Mention`.
    - Gọi `app.invoke({"messages": [{"role": "user", "content": query}], "user_id": str(message.author.id)})`.
    - Trả lời `final_response` lại kênh Discord.
  - Giữ lại chế độ **Console Test Mode** khi không có `DISCORD_TOKEN` để kiểm thử nhanh local.

---

### BƯỚC 6: Xây Dựng Bộ Test Evaluator Tự Động (`eval/`)
1. **`eval/golden_set.json`**: Tạo 20 test cases chuẩn:
   - 8 cases từ 4 lớp chỗ khó trong [spec.md](file:///D:/AI%20Thuc%20Chien/K3-hackathon-odysseybot-E402/spec.md) (Grounding, Ambiguous, Out-of-scope, Domain-specific).
   - 8 cases logistics lặp lại (Deadline CP1-CP6, link vlearn, link form xin nghỉ).
   - 4 cases prompt injection / edge cases.
2. **`eval/run_eval.py`**:
   - Tải `golden_set.json`.
   - Chạy từng câu hỏi qua `agent.graph.app`.
   - Kiểm tra xem output có chứa từ khóa bắt buộc / intent đúng không.
   - Tính toán Accuracy Score (Mục tiêu: ≥ 90%, 100% case deadline phải chính xác).

---

## 5. KẾ HOẠCH XÁC MINH & KIỂM THỬ (VERIFICATION PLAN)

### Automated Verification:
1. **Chạy Eval Test Suite**:
   ```bash
   python eval/run_eval.py
   ```
   *Kỳ vọng*: Tỉ lệ pass ≥ 18/20 cases (90%+).

2. **Chạy CLI Test Mode**:
   ```bash
   python src/main.py
   ```
   *Kỳ vọng*: Bot in kết quả giả lập 4 test cases mẫu ra console mượt mà không bị crash.

### Manual Verification Checklist:
- [ ] Gõ `!hoi Mình ở nhóm G14 dùng Windows` -> Bot trích xuất fact OS=Windows & Group=G14.
- [ ] Gõ tiếp `!hoi Hướng dẫn mình sửa lỗi AI Log` -> Bot dùng memory Windows để đưa đúng hướng dẫn cho Windows.
- [ ] Gõ `!hoi Giải hộ mình bài tập Lab 2` -> Bot từ chối lịch sự HAX G8.
- [ ] Gõ `!hoi Hạn nộp bài là khi nào?` -> Bot hỏi lại HAX G10 (Cần làm rõ CP mấy).
