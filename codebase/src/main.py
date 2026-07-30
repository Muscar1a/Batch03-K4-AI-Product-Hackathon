import os
import discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure bot intents (requires Message Content Intent enabled in Discord Dev Portal)
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Knowledge Base từ nguồn chính thức của BTC (01-de-bai.md, 02-guide.md, 04-rubric.md)
KNOWLEDGE_BASE = {
    "cp1": "📌 **Checkpoint 1 (Canvas)**:\n- Khóa 3: 10:00 Ngày 1 | Khóa 4: 15:00 Ngày 1\n- **Nội dung**: Canvas 7 dòng (hướng, job executor, pain 1 câu, evidence ban đầu, lát cắt 1 câu, automation, willing users).\n- *Nguồn: 04-rubric.md §Phần 3*",
    "cp2": "📌 **Checkpoint 2 (Show thứ bấm được)**:\n- Khóa 3: 12:00 Ngày 1 | Khóa 4: 17:00 Ngày 1\n- **Nội dung**: Flow chính bấm đi hết được (Sketch/Mock) + commit đầu trên Repo.\n- *Nguồn: 04-rubric.md §Phần 3*",
    "cp3": "📌 **Checkpoint 3 (AI thật + Đo lượt 1)**:\n- Khóa 3: 16:00 Ngày 1 | Khóa 4: 10:30 Ngày 2\n- **Nội dung**: ≥1 lời gọi AI thật + Golden set ≥20 cases + bảng kết quả lượt 1.\n- *Nguồn: 04-rubric.md §Phần 3*",
    "cp4": "📌 **Checkpoint 4 (Chốt tiến độ & Spec)**:\n- Khóa 3: 17:30 Ngày 1 | Khóa 4: 12:00 Ngày 2\n- ⏰ **HẠN CỨNG SPEC**: Commit `spec.md` trước **23:59 Ngày 1** (Quality bar chốt cố định từ mốc này).\n- *Nguồn: 01-de-bai.md & 04-rubric.md*",
    "cp5": "📌 **Checkpoint 5 (Validation & Dry run)**:\n- Khóa 3: 09:00 Ngày 2 | Khóa 4: 14:00 Ngày 2\n- **Nội dung**: Log user test ≥5 mẩu có tên + Changelog + Slide final + Dry run 5 phút.\n- *Nguồn: 04-rubric.md §Phần 3*",
    "cp6": "📌 **Checkpoint 6 (Demo chính thức)**:\n- Khóa 3: 10:00 Ngày 2 | Khóa 4: 15:00 Ngày 2\n- **Nội dung**: 5 phút demo + 5 phút Q&A (Thẻ giám khảo chạy 1 case lạ tại chỗ).\n- *Nguồn: 04-rubric.md §Phần 3*",
    "vlearn": "🔗 **Nền tảng Vlearn**: Trang học tập và nộp bài tại https://vlearn.dev và Codelabs https://codelabs.vlearn.dev.",
    "ai-log": "🛠️ **Hướng dẫn AI Log**: Đảm bảo cài đặt `git pre-push hook` theo hướng dẫn trong kênh `#chia-sẻ`. Kiểm tra file `overview.txt` hoặc `transcript.jsonl` trong `.system_generated/logs/`."
}

def process_query(query: str) -> str:
    query_lower = query.lower().strip()
    
    # 1. Lớp ③: Ngoài thẩm quyền / Yêu cầu giải bài tập / Soi code
    out_of_scope_keywords = ["đáp án", "giải hộ", "viết hộ code", "cho xin code", "làm hộ"]
    if any(kw in query_lower for kw in out_of_scope_keywords):
        return (
            "⚠️ **[Từ chối - Ngoài thẩm quyền]**\n"
            "Trợ lý chỉ hỗ trợ tra cứu logistics, deadline và quy định khóa học.\n"
            "Bạn hãy tham khảo slide bài giảng hoặc thảo luận cùng nhóm tại kênh `#hỏi-đáp` nhé!"
        )

    # 2. Lớp ②: Mơ hồ / Thiếu thông tin
    ambiguous_keywords = ["hạn nộp", "deadline", "mấy giờ", "khi nào nộp"]
    has_specific_cp = any(f"cp{i}" in query_lower or f"checkpoint {i}" in query_lower for i in range(1, 7))
    if any(kw in query_lower for kw in ambiguous_keywords) and not has_specific_cp:
        return (
            "❓ **[Cần làm rõ thông tin]**\n"
            "Bạn đang muốn tra cứu mốc deadline cho **Checkpoint mấy** (CP1 -> CP6) và thuộc **Khóa 3** hay **Khóa 4**?\n"
            "👉 *Ví dụ gõ*: `!hoi deadline CP4 khóa 4`"
        )

    # 3. Lớp ①: Tra cứu nguồn sự thật (Grounding Search)
    matched_results = []
    for key, content in KNOWLEDGE_BASE.items():
        if key in query_lower or (key.startswith("cp") and key in query_lower.replace("checkpoint ", "cp")):
            matched_results.append(content)
            
    if matched_results:
        response_text = "🤖 **[Trợ lý Học viên AI - Thông tin chính thức]**\n\n"
        response_text += "\n\n".join(matched_results)
        return response_text

    # 4. Lớp ①: Không có căn cứ (No Ground) -> Chuyển TA
    return (
        "🔍 **[Chưa có căn cứ chính thức]**\n"
        "Hiện tại chưa tìm thấy thông tin chính thức của BTC về câu hỏi này.\n"
        "📩 Đã ghi nhận và gửi thông báo tới các **Lab Coach / TA** (@LabCoach) để hỗ trợ bạn sớm nhất!"
    )

@client.event
async def on_ready():
    print(f"✅ Bot Trợ lý Học viên AI đã sẵn sàng: {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Kích hoạt qua prefix !hoi hoặc mention bot
    if message.content.startswith("!hoi") or (client.user and client.user in message.mentions):
        query = message.content.replace("!hoi", "").strip()
        if client.user:
            query = query.replace(f"<@{client.user.id}>", "").strip()

        if not query:
            await message.channel.send(
                "👋 **Xin chào! Mình là Trợ lý Học viên AI.**\n"
                "Bạn có thể hỏi mốc deadline, quy định CP1-CP6 hoặc Vlearn bằng lệnh: `!hoi <câu hỏi>`\n"
                "📌 *Ví dụ*: `!hoi hạn nộp CP4 khóa 4 khi nào?`"
            )
            return

        response = process_query(query)
        await message.channel.send(response)

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "your_discord_bot_token_here":
        print("ℹ️ Chạy thử nghiệm Logic Bot trong Console (chưa cấu hình DISCORD_TOKEN):")
        test_queries = [
            "Hạn nộp CP4 khi nào?",
            "Cho xin đáp án quiz Lab 2",
            "Mấy giờ nộp bài?",
            "Hướng dẫn setup AI log"
        ]
        for q in test_queries:
            print(f"\n💬 Query: '{q}'")
            print(process_query(q))
        return
        
    client.run(token)

if __name__ == "__main__":
    main()
