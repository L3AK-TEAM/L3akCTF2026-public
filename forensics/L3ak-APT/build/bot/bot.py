import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Enable logging so you can see errors in the console
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = "8616973942:AAG4mQRkTVxob9cebBiplozOIG7qwX3ILh4"
SECRET_WORD = "gime"
PASSWORD = "n04n6allow3dh3r3"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Safe guard against empty messages (like photo captions or stickers handled as text)
    if not update.message or not update.message.text:
        return
        
    user_message = update.message.text.strip().lower()
    username = update.message.from_user.first_name or update.message.from_user.username
    
    if user_message == SECRET_WORD:
        # MarkdownV2 is less prone to breaking with special characters than legacy Markdown
        await update.message.reply_text(
            f" Here's the password: `{PASSWORD}`\n\nUse it to open the zip file.", 
            parse_mode="Markdown"
        )
        print(f"[+] Gave password to: {username}")
    else:
        await update.message.reply_text(" Wrong secret word. Try again.")
        print(f"[-] Wrong attempt from: {username} -> '{user_message}'")

if __name__ == "__main__":
    # Build application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot is running... Send 'gime' to get the password")
    
    # run_polling safely blocks and handles the event loop automatically
    app.run_polling()