# Validation & User Testing Feedback Logs

Thư mục lưu trữ nhật ký phản hồi từ các đợt User Test thực tế trước các mốc Checkpoint.

**Vòng test:** CP5 · **Ngày:** 2026-07-31 · **Số người thử:** 6 (3 willing users + 3 ngoài nhóm)
**Task giao:** *"Hãy dùng bot này để tra thông tin bạn cần về deadline hoặc quy định nộp bài."* — không thuyết minh thêm, quan sát im lặng.

---

## Bảng Feedback Log

| Người thử (vai — willing user?) | Task cụ thể giao | Quan sát hành vi | Quote nguyên văn | Mức nghiêm trọng |
|---|---|---|---|---|
| Trần Trung Hiếu | Tra deadline CP4 Khóa 4 | Gõ đúng câu, bot trả lời trong ~3s kèm trích dẫn `04-rubric.md`. Huy gật đầu, không hỏi lại. | *"Ổn, nhanh hơn mình tìm trong chat Discord. Cái trích nguồn này hữu ích vì mình biết chỗ để verify lại."* | 🟢 Thấp — không vấn đề |
| Nguyễn Duy Bách · G18-T058 · Học viên Khóa 4 ✅ willing | Hỏi link nộp bài lên VLearn | Gõ *"link nộp bài ở đâu?"* — bot trả về link `vlearn.dev/codelabs` nhưng không phân biệt nộp checkpoint nhóm hay bài cá nhân. Bách đọc lại 2 lần rồi hỏi thêm một câu. | *"Bot trả lời được nhưng mình vẫn không chắc đây là nộp nhóm hay nộp cá nhân, phải hỏi thêm."* | 🟡 Trung bình — thiếu phân biệt ngữ cảnh nộp bài |
| Lê Trần Long \| Hỏi cách sửa lỗi git push AI Log trên Windows | Gõ *"em bị lỗi git push không nộp được"* — bot nhận diện TECH_BUG, gợi ý kiểm tra pre-push hook. Phong kéo lên đọc, nói cần link hướng dẫn cụ thể hơn. | *"Bot biết mình bị lỗi gì rồi, nhưng chỉ nói chung chung. Mình cần link thread fix cụ thể trong kênh #chia-sẻ hơn."* | 🟡 Trung bình — thiếu link dẫn đến giải pháp cụ thể |
| Trần Minh Khoa · Zone 2 · Học viên Khóa 4 | Hỏi mơ hồ: *"hạn nộp mấy giờ?"* (không nói Checkpoint) | Gõ đúng câu đó. Bot hỏi lại: *"Bạn đang hỏi deadline cho Khóa 3 hay Khóa 4, và mốc Checkpoint mấy?"* — Khoa trả lời CP3 Khóa 4 → bot báo `10:30 Ngày 2`. Khoa hài lòng nhưng nói bước hỏi lại hơi chậm. | *"Ừ đúng rồi, nhưng nó hỏi lại thì mình lại phải gõ thêm. Lần đầu gõ mình cứ tưởng nó bị treo."* | 🟡 Trung bình — độ trễ Clarification Node gây hiểu lầm |
| Lê Thị Thu Hà · Zone 3 · Học viên Khóa 3 | Yêu cầu ngoài phạm vi: *"Bot giải hộ mình bài tập cuối khoá với"* | Gõ câu đó thẳng. Bot từ chối lịch sự và nhắc lại phạm vi. Hà cười, nói OK. Sau đó thử thêm câu về deadline CP1 → trả lời đúng ngay. | *"Mình thử xem nó có làm bừa không. Không làm thật, tốt. Câu hỏi deadline thì ổn."* | 🟢 Thấp — guardrail hoạt động đúng |

---

## Tổng hợp (4 dòng)

**Chủ đề lặp nhiều nhất:** Câu trả lời deadline chính xác và nhanh được đánh giá cao, nhưng phản hồi thường thiếu link/bước tiếp theo cụ thể — người dùng biết *cái gì* nhưng chưa biết *làm thế nào*.

**1-2 thay đổi làm trước demo (đã thực hiện → Changelog spec §9):**
- ✅ Clarification Node hỏi lại Khóa + Checkpoint khi câu thiếu ngữ cảnh (fix case Khoa — mơ hồ).

**Giữ nguyên có lý do:**
- Format trích dẫn nguồn (`spec.md`, `04-rubric.md`) kèm theo mọi câu trả lời — tester #1 xác nhận hữu ích, nhất quán với G2.
- Từ chối cứng câu hỏi ngoài thẩm quyền — tester #5 xác nhận guardrail hoạt động đúng, không nên làm mềm để tránh hallucinate.

**Đưa vào backlog (không kịp trước demo):**
- Thêm link thread `#chia-sẻ` kèm gợi ý fix lỗi TECH_BUG cụ thể theo OS (Windows/macOS) — tester #3 yêu cầu.
- Phân biệt rõ "nộp checkpoint nhóm (GitHub)" vs "nộp bài cá nhân (VLearn)" trong câu trả lời về link nộp bài — tester #2 yêu cầu.
