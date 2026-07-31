# Reflection Cá Nhân — Thành viên 1

- **Họ và tên**: Nguyễn Thành An
- **Mã học viên**: 2A202601017
- **Vai trò trong nhóm**: Data Engine & Triples Mining Engineer

---

## 1. Bài học kinh nghiệm thu được

- **Đọc data trước, filter sau** — lần đầu tôi viết regex quá chặt, loại mất ~200 tin có giá trị. Phải làm lại sau khi đọc kỹ 50 mẫu đầu tiên.
- **Few-shot prompt quan trọng hơn tưởng**: thêm 3 examples vào prompt extractor giảm parse error từ ~40% xuống ~8%.
- **Đếm được mới là bằng chứng**: muốn viết "nhiều học viên hỏi deadline" vào spec, nhưng phải đếm thật mới ra con số 84/285 threads (29,4%) — con số đó mới thuyết phục được cả nhóm trong 5 phút.

---

## 2. Tự đánh giá đóng góp

| Hạng mục | Chi tiết | Trạng thái |
|---|---|---|
| `discord_cleaner.py` | Làm sạch 6.870 tin nhắn, lọc 1.725 rác/bot (25,11%) | ✅ |
| `kg_triples_extractor.py` | Trích xuất 1.438 Triples & 987 Entities từ 286 threads | ✅ |
| `spec.md §1 & §2` | Evidence mining, problem statement, bảng impact 3 ứng viên | ✅ |
| User Test | Phỏng vấn 2 người ngoài nhóm theo script guide §4.2 | ✅ |

---

## 3. Làm tốt / chưa tốt

**Tốt:** Mining có phương pháp — tiêu chí đếm rõ, giữ 5 quotes nguyên văn, người khác kiểm lại được.

**Chưa tốt:** Pipeline ETL chạy tuần tự, chậm. Các triple chưa có validation tự động — chỉ check tay ~50 triple, không biết tỷ lệ lỗi thật của toàn bộ 1.438.

---

## 4. Nếu làm lại

Kết hợp mining (Đường B) với ít nhất 5 câu phỏng vấn nhanh (Đường A) ngay từ đầu — guide §1.3 nói rõ hai đường bổ sung nhau, tôi chỉ dùng B nên evidence hơi một chiều.
