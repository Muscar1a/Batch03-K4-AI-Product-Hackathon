# Reflection Cá Nhân — Thành viên 2 (Team Lead)

- **Họ và tên**: Phạm Quốc Thanh
- **Mã học viên**: 2A202601407
- **Vai trò trong nhóm**: Team Lead & Full-Stack System Engineer / Graph Database & Dynamic Memory Engineer

---

## 1. Bài học kinh nghiệm thu được
- **Tư duy Kiến trúc Hệ thống Hybrid RAG**: Kết hợp thành công giữa SQLite FTS5 BM25 (truy vấn văn bản toàn vẹn) và Knowledge Graph Database (NetworkX 2-hop traversal) giúp nâng cao độ chính xác tìm kiếm ngữ cảnh lên rõ rệt.
- **Xử lý Thực tế & Edge Cases trong AI Agent**: Thiết kế luồng ReAct Engine 2 vòng (2-Round Synthesis) giúp lọc bỏ suy nghĩ nội bộ của LLM, kiểm soát phân quyền Staff Evidence Gate nghiêm ngặt, và tự động loại bỏ trích dẫn rác khi câu trả lời mang tính phủ định (negative finding).
- **Tối ưu UX/UI Trực Quan cho Discord**: Chuyển đổi thành công trích dẫn URL thô thành native Discord channel pills (`<#channel_id>`) và hỗ trợ tính năng Reply tin nhắn trực tiếp giúp tăng trải nghiệm người dùng cuối.

---

## 2. Tự đánh giá đóng góp

| Hạng mục | Chi tiết thực hiện | Trạng thái |
|---|---|---|
| **System Prompt & ReAct Engine** | Thiết kế và tinh chỉnh `system_prompt` v0 $\rightarrow$ v3, bổ sung nút Clarification Node khi câu hỏi quá mơ hồ, xử lý ReAct 2 vòng mượt mà. | ✅ Complete |
| **Hybrid Retrieval & FTS5 BM25** | Tối ưu `retriever.py` với FTS5 Virtual Table BM25, trích xuất chính xác tin nhắn theo tên tác giả và bổ sung chỉ số tổng số bài đăng vào Context. | ✅ Complete |
| **FastAPI Local Server & CLI** | Xây dựng backend REST API server (`server.py`) tại `http://127.0.0.1:8000/ask` và bộ công cụ CLI (`cli.py`) phục vụ testing & debug tại chỗ. | ✅ Complete |
| **Staff Evidence Gate & UX** | Bắt buộc kiểm tra Role ID chính thức (`PERSONAL_DISCORD_ADMIN_ROLE_IDS`), chuyển đổi citation sang dạng purple pill `<#channel_id>`, tích hợp Discord Message Reply. | ✅ Complete |
| **Tài liệu & Test Suite** | Hoàn thiện phần §3, §4 & §5 trong `spec.md`, cập nhật `docs/diagrams.md` với Mermaid diagrams chuẩn, xây dựng `test_edge_cases.py`. | ✅ Complete |

---

## 3. Bài học về sự cố & Tự rút kinh nghiệm (Reflection)
- **Điểm tốt**:
  - Chủ động xử lý dứt điểm các lỗi phát sinh từ phản hồi người dùng thực tế (như đếm thiếu bài đăng do limit hay trích dẫn lặp ngoặc `))`).
  - Xây dựng sẵn Local FastAPI Endpoint giúp việc test các kịch bản diễn ra cực kỳ nhanh mà không phụ thuộc vào Discord Gateway.
- **Chưa tốt**:
  - File dữ liệu runtime SQLite (`odysseybot.sqlite3`) bị `.gitignore` chặn nên cần hướng dẫn cẩn thận cho đồng đội khi nạp dữ liệu ban đầu.

---

## 4. Kế hoạch phát triển tiếp theo
- Mở rộng thêm tính năng tự động đăng tải Bản tin Hàng ngày (Staff Daily Digest) vào 18:00 hàng ngày.
- Tích hợp thêm các công cụ tra cứu điểm danh QR code tự động qua 