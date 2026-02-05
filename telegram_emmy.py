import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from emmy_core import get_emmy_brain # <-- PAKE OTAK YANG SAMA

# Load Agent
agent = get_emmy_brain()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Bikin ID beda biar gak nyampur sama chat Discord
    thread_id = f"telegram_{user_id}_emmy_local"
    config = {"configurable": {"thread_id": thread_id}}

    await update.message.reply_text("⏳ *Typing...*", parse_mode="Markdown")

    # Panggil Otak
    # Note: Telegram udah async native, jadi ga perlu to_thread sebenernya, 
    # tapi buat heavy task amanin aja.
    response = await asyncio.to_thread(
        agent.invoke,
        {"messages": [{"role": "user", "content": user_text}]},
        config
    )
    
    bot_reply = response['messages'][-1].content
    await update.message.reply_text(bot_reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("🚀 Emmy Telegram Online!")
    app.run_polling()