import os
import discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure bot intents (requires Message Content Intent enabled in Discord Dev Portal)
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Bot started successfully as: {client.user}")

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Check for prefix or bot mention
    if message.content.startswith("!hoi") or (client.user and client.user in message.mentions):
        query = message.content.replace("!hoi", "").strip()
        if client.user:
            query = query.replace(f"<@{client.user.id}>", "").strip()

        if not query:
            await message.channel.send("❓ Bạn cần hỏi thông tin gì? Ví dụ: `!hoi Hạn nộp CP2 khi nào?`")
            return

        # CP2 Mock Response (Pass CP2 validation criteria)
        response = (
            f"🤖 **[Trợ lý Học viên - Prototype CP2]**\n"
            f"> **Câu hỏi:** {query}\n\n"
            f"📌 **Thông tin phản hồi (Mock):** Đã tiếp nhận câu hỏi của bạn. "
            f"Hạn nộp CP2 là 17:00 Ngày 1. Hãy kiểm tra thông tin trên kênh Discord chính thức!"
        )

        await message.channel.send(response)

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "your_discord_bot_token_here":
        print("❌ Lỗi: Chưa cấu hình DISCORD_TOKEN hợp lệ trong file .env")
        return
    client.run(token)

if __name__ == "__main__":
    main()
