# Evaluation & Golden Set Results

Thư mục chứa bộ test case mẫu (Golden Set) và kết quả đánh giá qua các lượt chạy.

## Các tệp tin
- `golden_set.json`: Tập hợp 20+ kịch bản test mẫu kiểm thử khả năng xử lý của Trợ lý AI.
- `results.md`: Nhật ký kết quả chạy thử nghiệm qua các mốc Checkpoint.

## Kết quả lượt chạy (Run Iterations)
| Lượt chạy | Mốc CP | Tỷ lệ thành công | Ghi chú |
|---|---|---|---|
| Lượt 1 | CP3 | 18/20 (90%) | Thất bại ở 2 câu hỏi mơ hồ thiếu thông tin khóa 3/khóa 4 |
| Lượt 2 | CP5 | 20/20 (100%) | Đã cập nhật Clarification Node xử lý câu hỏi mơ hồ |
