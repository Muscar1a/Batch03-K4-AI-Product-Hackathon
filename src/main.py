import os
import sys

# Ensure root workspace is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try importing discord.py safely
try:
    import discord
    HAS_DISCORD = True
except ImportError:
    HAS_DISCORD = False

from src.agent.graph import app
from src.agent.state import ChatbotState

def process_query_with_agent(query: str, user_id: str = "default_user") -> str:
    """Xử lý câu hỏi thông qua bộ não LangGraph Agent State Machine."""
    initial_state: ChatbotState = {
        "messages": [{"role": "user", "content": query}],
        "user_id": user_id,
        "extracted_user_facts": [],
        "intent": "",
        "target_tool": None,
        "kg_triples": [],
        "retrieved_context": "",
        "final_response": "",
        "citations": []
    }
    
    result_state = app.invoke(initial_state)
    return result_state.get("final_response", "⚠️ Không thể sinh phản hồi.")

def run_discord_bot(token: str):
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"✅ Bot Trợ lý Học viên AI (LangGraph Core) đã sẵn sàng: {client.user}")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        if message.content.startswith("!hoi") or (client.user and client.user in message.mentions):
            query = message.content.replace("!hoi", "").strip()
            if client.user:
                query = query.replace(f"<@{client.user.id}>", "").strip()

            if not query:
                await message.channel.send(
                    "👋 **Xin chào! Mình là Trợ lý Học viên AI (LangGraph State Machine).**\n"
                    "Bạn có thể hỏi mốc deadline, quy định CP1-CP6 hoặc tra cứu bằng lệnh: `!hoi <câu hỏi>`\n"
                    "📌 *Ví dụ*: `!hoi hạn nộp CP4 khóa 4 khi nào?`"
                )
                return

            response = process_query_with_agent(query, user_id=str(message.author.id))
            await message.channel.send(response)

    client.run(token)

def main():
    token = os.getenv("DISCORD_TOKEN")
    
    if HAS_DISCORD and token and token != "your_discord_bot_token_here":
        try:
            run_discord_bot(token)
        except Exception as e:
            if "PrivilegedIntentsRequired" in type(e).__name__ or "PrivilegedIntentsRequired" in str(e):
                print("\n==================================================================")
                print("⚠️ [LỖI DISCORD INTENT] CẦN BẬT MESSAGE CONTENT INTENT TRÊN DISCORD PORTAL")
                print("==================================================================")
                print("📌 Các bước khắc phục (Chỉ mất 30 giây):")
                print("1. Truy cập https://discord.com/developers/applications/")
                print("2. Chọn Bot Application của bạn -> Chọn tab 'Bot' ở thanh menu bên trái.")
                print("3. Cuộn xuống mục 'Privileged Gateway Intents'.")
                print("4. Bật công tắc ON cho nút 'MESSAGE CONTENT INTENT'.")
                print("5. Nhấn 'Save Changes' ở phía dưới trang và chạy lại `python src/main.py`!")
                print("==================================================================\n")
                print("👇 Đang chuyển tạm sang chế độ Console Interactive Demo...")
                for q in [
                    "Mình ở nhóm G14 dùng Windows",
                    "Hạn nộp CP4 khóa 4 khi nào?",
                    "Sửa lỗi git push AI Log giúp mình"
                ]:
                    print(f"\n💬 User Query: '{q}'")
                    print(process_query_with_agent(q, user_id="test_user_01"))
            else:
                raise e
    else:
        print("==================================================================")
        print("ℹ️ [Console Demo Mode] Chạy thử nghiệm LangGraph Agent")
        if not HAS_DISCORD:
            print("💡 Mẹo: Cài đặt `pip install discord.py` để chạy Bot Discord thực tế.")
        print("==================================================================")
        
        test_queries = [
            "Mình ở nhóm G14 dùng Windows",
            "Hạn nộp CP4 khóa 4 khi nào?",
            "Sửa lỗi git push AI Log giúp mình",
            "Cho em xin đáp án bài quiz Lab 2",
            "Mấy giờ nộp bài?",
            "Tìm kiếm trên web tài liệu LangGraph mới nhất"
        ]
        for q in test_queries:
            print(f"\n💬 User Query: '{q}'")
            response = process_query_with_agent(q, user_id="test_user_01")
            print(response)
            print("-" * 60)

if __name__ == "__main__":
    main()
