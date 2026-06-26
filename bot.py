import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
import config
import database
from core.plugin_manager import load_plugins

# Import standard built-in handlers
from handlers import private_admin, group_moderator, channel_poster, gemini_ai

async def main():
    # Reconfigure stdout/stderr to UTF-8 to prevent emoji logging crashes on Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # Initialize logging (force stdout flushing for live console logs in dashboard)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    
    # Check for BOT_TOKEN
    if not config.BOT_TOKEN:
        print("ERROR: BOT_TOKEN not found in environment or .env file!")
        return

    # Initialize bot (compatible with different aiogram 3 versions)
    try:
        from aiogram.client.default import DefaultBotProperties
        bot = Bot(
            token=config.BOT_TOKEN, 
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    except ImportError:
        # Fallback for older aiogram 3 versions
        bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
        
    dp = Dispatcher()
    
    # Register standard routers
    dp.include_router(private_admin.router)
    dp.include_router(group_moderator.router)
    dp.include_router(channel_poster.router)
    dp.include_router(gemini_ai.router)
    
    # Register dynamic modular plugins (from modules/ folder, e.g. security module)
    load_plugins(dp)
    
    # Initialize SQLite database
    await database.init_db()
    
    logging.info("Bot started successfully and database is initialized!")
    
    # Drop pending updates to prevent processing old messages on restart
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start long polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")