# SƠ ĐỒ HỆ THỐNG CHATBOT (LANGGRAPH + KNOWLEDGE GRAPH DB + DYNAMIC MEMORY)

## 0. Sơ Đồ Luồng Cơ Bản (Basic Bot Flow)

```mermaid
graph TD
    classDef stepStyle fill:#0f172a,stroke:#00f2fe,stroke-width:2px,color:#fff;
    classDef memStyle fill:#162447,stroke:#9d4edd,stroke-width:2px,color:#fff;
    classDef dbStyle fill:#162447,stroke:#00f5d4,stroke-width:2px,color:#fff;

    A[💬 1. Tiếp Nhận Câu Hỏi<br/>User Input từ Discord]:::stepStyle --> B[🧠 2. Dynamic Memory Engine<br/>Ghi nhớ thông tin cá nhân: OS, Group]:::memStyle
    B --> C[🕸️ 3. Knowledge Graph DB<br/>Tra cứu câu trả lời & căn cứ trong dữ liệu Discord]:::dbStyle
    C --> D[🤖 4. Answer & Citation<br/>Trả lời học viên kèm trích dẫn nguồn BTC]:::stepStyle
```

---

## 1. Sơ Đồ Kiến Trúc Luồng Nâng Cao (Full Advanced Architecture)


```mermaid
graph TD
    %% Styling
    classDef inputStyle fill:#1e293b,stroke:#00f2fe,stroke-width:2px,color:#fff;
    classDef nodeStyle fill:#0f172a,stroke:#9d4edd,stroke-width:2px,color:#fff;
    classDef dbStyle fill:#162447,stroke:#00f5d4,stroke-width:2px,color:#fff;
    classDef toolStyle fill:#2d1b4e,stroke:#ffb703,stroke-width:2px,color:#fff;
    classDef guardStyle fill:#3d0c1e,stroke:#ff007f,stroke-width:2px,color:#fff;

    User([👤 Học viên gửi câu hỏi / Discord Input]):::inputStyle --> Node1[1. Input & Dynamic Memory Extractor Node]:::nodeStyle

    subgraph Memory_System [🧠 Dynamic Memory Engine]
        MemoryStore[(Dynamic Memory Store<br/>data/memory_store.json)]:::dbStyle
    end

    Node1 -->|1. Trích xuất Fact cá nhân<br/>OS, Group, Issue| MemoryStore
    Node1 --> Router{2. Intent & Guardrail Router}:::nodeStyle

    %% Routing Paths
    Router -->|Tra cứu tri thức / Lỗi| Node3[3. KGDB Multi-Hop Retriever Node]:::nodeStyle
    Router -->|Yêu cầu tác vụ / Tool| Node4[4. Agent Tools & Sub-Agent Dispatcher]:::toolStyle
    Router -->|Phạm quy / Đòi đáp án quiz| NodeRefuse[Refusal Guardrail Node]:::guardStyle
    Router -->|Mơ hồ / Thiếu ngữ cảnh| NodeClarify[Clarification Node - HAX G10]:::guardStyle

    %% Databases & Tools
    subgraph Data_Layer [🕸️ Data & Graph Engine]
        RawData[(Raw Uncleaned Discord Data<br/>discord-crawl + 💬-chung)]:::dbStyle --> Cleaner[Data Cleaner & Triple Mining]:::dbStyle
        Cleaner --> KGDB[(Knowledge Graph DB<br/>NetworkX / SQLite)]:::dbStyle
    end

    subgraph Tools_Layer [🛠️ Agent Toolset]
        WebSearch[web_search_tool]:::toolStyle
        UpdateKB[update_knowledge_base_tool]:::toolStyle
        GitCheck[github_repo_checker_tool]:::toolStyle
    end

    Node3 <-->|Query 2-hop triples| KGDB
    Node4 <-->|Execute external task| Tools_Layer

    %% Synthesis
    Node3 --> Node5[5. Answer Synthesizer & Citation Node]:::nodeStyle
    Node4 --> Node5
    NodeClarify --> Node5
    NodeRefuse --> Node5

    Node5 --> Output([🤖 Response + Source Citation + Memory Updated]):::inputStyle
    Node5 -.->|Cập nhật lịch sử chat| MemoryStore
```

---

## 2. Sơ Đồ Chuyển Trạng Thái LangGraph (State Transition Machine Diagram)

```mermaid
stateDiagram-v2
    [*] --> Idle: Tiếp nhận Message mới từ Discord
    
    state Idle {
        [*] --> ExtractMemory: Phân tích User Profile & User Facts
        ExtractMemory --> ClassifyIntent: Phân loại Intent (Logistics / Bug / Tool / Out-of-Scope)
    }

    ClassifyIntent --> OutOfScope: Intent = OUT_OF_SCOPE (Đòi đáp án/chấm bài)
    ClassifyIntent --> Ambiguous: Intent = AMBIGUOUS (Thiếu mốc CP/Khóa)
    ClassifyIntent --> KGRetrieval: Intent = TECH_BUG / LOGISTICS
    ClassifyIntent --> ExecuteTool: Intent = EXECUTE_TOOL

    state OutOfScope {
        [*] --> FormatRefusal: Sinh câu từ chối lịch sự (HAX G8)
    }

    state Ambiguous {
        [*] --> FormatQuestion: Hỏi lại 1 câu thu hẹp scope (HAX G10)
    }

    state KGRetrieval {
        [*] --> QueryGraph: Tra vấn Đồ thị Tri thức 2-hop
        QueryGraph --> CheckConfidence: Đánh giá độ tin cậy Triples
        CheckConfidence --> FallbackRAG: Confidence < 0.6
        CheckConfidence --> SynthesizeAnswer: Confidence >= 0.6
    }

    state ExecuteTool {
        [*] --> DispatchTool: Gọi Tool (Search / Update / Git Check)
        DispatchTool --> SynthesizeAnswer: Trả kết quả thực thi về Agent
    }

    state FallbackRAG {
        [*] --> VectorSearch: Tìm kiếm văn bản gốc Discord
        VectorSearch --> SynthesizeAnswer
    }

    FormatRefusal --> OutputState
    FormatQuestion --> OutputState
    SynthesizeAnswer --> OutputState

    state OutputState {
        [*] --> UpdateMemoryStore: Lưu Fact mới vào memory_store.json
        UpdateMemoryStore --> SendResponse: Gửi phản hồi kèm Trích dẫn (HAX G2)
    }

    SendResponse --> [*]
```

---

## 3. Sơ Đồ Luồng Dữ Liệu ETL & Triples Mining (Data Pipeline Diagram)

```mermaid
flowchart LR
    subgraph Raw_Files [Dữ liệu Thô Uncleaned]
        F1[💬-chung JSON<br/>2,658 msgs / 3.8MB]
        F2[discord-crawl/*.json<br/>285 files]
    end

    subgraph Cleaning_Stage [Giai đoạn Lọc Nhiễu]
        C1[Lọc tin cụt 'hi', '.', emoji]
        C2[Gom nhóm theo Thread & Reply Chain]
    end

    subgraph Mining_Stage [Trích xuất Triples]
        E1[LLM Triple Mining Prompt]
        E2[Pydantic Validation]
    end

    subgraph Graph_Storage [Lưu trữ Đồ thị]
        G1[(User Entity)]
        G2[(Topic Entity)]
        G3[(Solution Entity)]
        G4[(Tool Entity)]
    end

    F1 & F2 --> C1 --> C2 --> E1 --> E2
    E2 -->|Triple: User - POSTED -> Topic| G1 & G2
    E2 -->|Triple: Topic - HAS_SOLUTION -> Solution| G2 & G3
    E2 -->|Triple: Solution - MENTIONS -> Tool| G3 & G4
```
