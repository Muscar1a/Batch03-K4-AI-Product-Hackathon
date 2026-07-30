# SƠ ĐỒ HỆ THỐNG CHATBOT ODYSSEYBOT (LANGGRAPH STATEGRAPH + FTS5 + GRAPHSTORE)

## 0. Sơ Đồ Luồng Cơ Bản (Basic Bot Flow)

```mermaid
graph TD
    classDef stepStyle fill:#0f172a,stroke:#00f2fe,stroke-width:2px,color:#fff;
    classDef memStyle fill:#162447,stroke:#9d4edd,stroke-width:2px,color:#fff;
    classDef dbStyle fill:#162447,stroke:#00f5d4,stroke-width:2px,color:#fff;

    A[💬 1. Tiếp Nhận Câu Hỏi<br/>User Input từ Discord / !hoi / Slash Command]:::stepStyle --> B[🧠 2. LangGraph Intent Classifier<br/>Phân loại: LOGISTICS / TECHNICAL / CLARIFICATION]:::memStyle
    B --> C[🕸️ 3. Hybrid Retriever Engine<br/>FTS5 BM25 + NetworkX GraphStore + Official Docs]:::dbStyle
    C --> D[🤖 4. Cohesive Answer & Citation<br/>Tổng hợp mượt mà + Phân định Quyền hạn BTC vs Học viên]:::stepStyle
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

    User([👤 Học viên Discord / Command]):::inputStyle --> Node1[1. classify_intent Node]:::nodeStyle

    subgraph LangGraph_Engine [🤖 LangGraph StateGraph Architecture]
        Node1 -->|Check Scope / Term Length| Router{Intent & Clarification Check}:::nodeStyle
        
        Router -->|Mơ hồ / < 3 từ chung chung| NodeClarify[Clarification Node<br/>Yêu cầu nêu rõ thắc mắc]:::guardStyle
        Router -->|Hợp lệ: LOGISTICS / TECHNICAL| Node2[2. retrieve_claims Node]:::nodeStyle
        
        Node2 --> Node3[3. verify_evidence Node]:::nodeStyle
        Node3 -->|Có Nguồn BTC / TA| AnswerStatus1[Status: BOT_ANSWERED<br/>Escalated: False]:::nodeStyle
        Node3 -->|Chỉ có Nguồn Học viên / Khômg Nguồn| AnswerStatus2[Status: ESCALATED<br/>Escalated: True]:::guardStyle
        
        AnswerStatus1 --> Node4[4. synthesize_answer Node]:::nodeStyle
        AnswerStatus2 --> Node4
        NodeClarify --> Node4

        Node4 --> Node5[5. log_interaction Node]:::nodeStyle
    end

    subgraph Knowledge_Layer [🕸️ Hybrid Knowledge Engine]
        FTS5[(SQLite FTS5 BM25 Virtual Table<br/>fts_source_messages)]:::dbStyle
        KGDB[(NetworkX Knowledge Graph DB<br/>data/graph_store.json)]:::dbStyle
        Docs[(Tài liệu chính thức khóa học<br/>01-de-bai.md, spec.md...)]:::dbStyle
    end

    subgraph Ingestion_Sidecar [🔄 Atomic Ingestion Pipeline]
        DCE[DiscordChatExporter CLI]:::toolStyle --> PartialDir[Staging Directory .partial]:::toolStyle
        PartialDir --> Importer[ArtifactImporter<br/>Atomic Transaction & FTS Trigger]:::dbStyle
        Importer --> ReadyDir[Ready & Imported Dirs]:::dbStyle
    end

    Node2 <-->|1. FTS5 BM25 MATCH| FTS5
    Node2 <-->|2. Multi-hop 2-hop Context| KGDB
    Node2 <-->|3. Strict 2-term Heading Match| Docs

    Node5 --> Output([🤖 Response + Native Discord Channel Mentions <#channel_id>]):::inputStyle
    Node5 -.->|Lưu Provenance & History| InteractionDB[(SQLite Database<br/>bot_messages & interactions)]:::dbStyle
```

---

## 2. Sơ Đồ Chuyển Trạng Thái LangGraph StateGraph (State Machine Diagram)

```mermaid
stateDiagram-v2
    [*] --> ClassifyIntent: Tiếp nhận AskRequest từ Discord (!hoi / Slash)

    state ClassifyIntent {
        [*] --> CheckBroadTerms: Kiểm tra độ dài & Từ khóa chung chung
        CheckBroadTerms --> IntentClarification: Is Broad / Vague (< 3 từ)
        CheckBroadTerms --> IntentValid: Is Logistics / Technical
    }

    IntentClarification --> SynthesizeAnswer: Gợi ý học viên đặt câu hỏi cụ thể hơn

    state IntentValid {
        [*] --> RetrieveClaims: Tra cứu FTS5 + GraphStore + Official Docs
        RetrieveClaims --> VerifyEvidence: Phân tích Nguồn Chứng Cứ (Evidence Gate)
    }

    state VerifyEvidence {
        [*] --> CheckStaffAuthority: Kiểm tra Role ID & Staff Flag
        CheckStaffAuthority --> BotAnswered: Có Nguồn BTC / TA (is_staff = 1)
        CheckStaffAuthority --> Escalated: Chỉ có Nguồn Học viên (is_staff = 0) / Không nguồn
    }

    BotAnswered --> SynthesizeAnswer: Cohesive Synthesis (Giọng văn khẳng định)
    Escalated --> SynthesizeAnswer: Community Advice Synthesis (Trích dẫn kèm phân định nguồn)

    state SynthesizeAnswer {
        [*] --> GeminiGen: Sinh câu trả lời với Gemini (Temp = 0.0)
        GeminiGen --> CleanFormat: Loại bỏ Link thô & In đậm Tiêu đề
    }

    SynthesizeAnswer --> LogInteraction: Ghi nhận Provenance vào bot_messages & interactions
    LogInteraction --> SendDiscordResponse: Gửi phản hồi kèm Native Discord Channel Pills <#channel_id>
    SendDiscordResponse --> [*]
```

---

## 3. Sơ Đồ Quy Trình Thu Thập & Đồng Bộ Dữ Liệu Nguyên Tử (Atomic Ingestion ETL)

```mermaid
flowchart LR
    subgraph DCE_Sidecar [DiscordChatExporter Sidecar]
        Scheduler[17:30 Daily Sync Task] --> DCECmd[Execute Isolated Subprocess<br/>PATH + DISCORD_TOKEN minimal env]
    end

    subgraph Atomic_Staging [Atomic Batch Staging]
        DCECmd --> Staging[.partial Staging Directory]
        Staging --> Validation{Validate Export Integrity}
        Validation -->|File hỏng / Invalid JSON| FailFast[Fail-Fast Rollback & Redact Token Stderr]
        Validation -->|File hợp lệ| BatchCommit[Atomic Transaction Commit]
    end

    subgraph Database_Sync [Database & FTS5 Synchronization]
        BatchCommit --> SourceMsgs[(source_messages Table)]
        SourceMsgs -->|SQLite Trigger AI/AD/AU| FTS5[(fts_source_messages Virtual Table)]
        BatchCommit --> DirectoryRename[Atomic Directory Move: .partial -> ready -> imported]
    end
```
