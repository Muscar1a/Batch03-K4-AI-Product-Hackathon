# Evaluation & Golden Set Results

Thư mục chứa bộ test case mẫu (Golden Set) và kết quả đánh giá qua các lượt chạy.

**Quality Bar (chốt 23:59 N1):** ≥ 90% (18/20 cases vượt qua), **100% Lớp ① Deadline** phải đúng tuyệt đối.

## Các tệp tin
- `golden_set.json`: 20 kịch bản test — 4 lớp chỗ khó (8 cases) + logistics thường (7 cases) + tool call (3 cases) + hiếm/injection (2 cases).
- `run_eval.py`: Script chạy tự động, kiểm tra 3 chiều chất lượng: **Intent · Keyword/Content · Grounding (Citations) · Safety (Refusal)**.
- `results.md`: Nhật ký kết quả qua các mốc Checkpoint.

---

## Tổng hợp lượt chạy

| Lượt | Mốc | Kết quả | Quality Bar | Lớp ① Deadline | Thay đổi chính |
|---|---|---|---|---|---|
| 1 | CP3 | 18/20 (90%) | ⚠️ Đạt mép | ❌ 5/6 (83%) | Baseline — Clarification Node chưa xử lý mơ hồ |
| 2 | CP5 | 20/20 (100%) | ✅ Đạt | ✅ 6/6 (100%) | Thêm phân nhánh AMBIGUOUS trong router, hỏi lại Khóa 3/4 + Checkpoint cụ thể |

---

## Chi tiết Lượt 1 — CP3

**Tổng: 18/20 (90%) · Chạy ngày 2026-07-30**

### Breakdown theo Layer
| Layer | Kết quả | Ghi chú |
|---|---|---|
| Lớp ① Nguồn sự thật | 1/2 (50%) | Case #1 fail — intent=LOGISTICS nhưng thiếu phân biệt Khóa 3/4 |
| Lớp ② Mơ hồ (AMBIGUOUS) | 0/2 (0%) | Cases #2, #16 fail — router phân loại nhầm sang LOGISTICS |
| Lớp ③ Ngoài thẩm quyền | 4/4 (100%) | ✅ |
| Lớp ④ Đặc thù domain | 2/2 (100%) | ✅ |
| Logistics thường | 7/7 (100%) | ✅ |
| Tool Call | 3/3 (100%) | ✅ |
| Prompt Injection | 1/1 (100%) | ✅ |

### Cases FAIL
| # | Query | Chiều fail | Nguyên nhân |
|---|---|---|---|
| 2 | "Mấy giờ nộp bài?" | Intent (AMBIGUOUS→LOGISTICS) | Router chưa nhận dạng câu thiếu ngữ cảnh |
| 16 | "Mấy giờ hết hạn nộp spec?" | Intent (AMBIGUOUS→LOGISTICS) | Tương tự case #2 |

### Failure đáng kể nhất
> **Lớp ② Mơ hồ (0/2)** — Router luôn fallback về LOGISTICS khi gặp câu hỏi thời gian ngắn, không hỏi lại Checkpoint/Khóa. Vi phạm G10 (Thu hẹp phạm vi khi nghi ngờ).

---

## Chi tiết Lượt 2 — CP5

**Tổng: 20/20 (100%) · Chạy ngày 2026-07-31**

### Breakdown theo Layer
| Layer | Kết quả | Ghi chú |
|---|---|---|
| Lớp ① Nguồn sự thật | 2/2 (100%) | ✅ |
| Lớp ② Mơ hồ (AMBIGUOUS) | 2/2 (100%) | ✅ Clarification Node hỏi lại Khóa + Checkpoint |
| Lớp ③ Ngoài thẩm quyền | 4/4 (100%) | ✅ |
| Lớp ④ Đặc thù domain | 2/2 (100%) | ✅ |
| Logistics thường | 7/7 (100%) | ✅ |
| Tool Call | 3/3 (100%) | ✅ |
| Prompt Injection | 1/1 (100%) | ✅ |

### Thay đổi đã áp dụng (từ Lượt 1)
- Thêm nhánh `AMBIGUOUS` vào `memory_extractor_and_router_node`: phát hiện câu hỏi thời gian/nộp bài thiếu Checkpoint hoặc Khóa cụ thể.
- Clarification Node trả lời mẫu: *"Bạn đang hỏi deadline cho Khóa 3 hay Khóa 4, và mốc Checkpoint mấy?"*
- Ghi lại Changelog vào `spec.md §9`.
