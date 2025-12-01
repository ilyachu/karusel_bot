import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from config import TELEGRAM_BOT_TOKEN, ADMIN_ID
from handlers import common, carousel_flow, admin
from utils.database import init_db
from middlewares.access import AccessMiddleware

# Admin ID for error notifications is now imported from config

from aiogram.types import ErrorEvent

async def error_handler(event: ErrorEvent):
    """
    Global error handler that catches all unhandled exceptions.
    Logs the error and notifies admin.
    """
    exception = event.exception
    update = event.update
    
    logging.error(f"Update {update.update_id if update else 'None'} caused error: {exception}", exc_info=True)
    
    # Try to notify admin
    try:
        bot = update.bot if update and update.bot else None
        if bot:
            error_message = f"🚨 Error in bot:\n\n{type(exception).__name__}: {str(exception)}\n\nUpdate ID: {update.update_id if update else 'N/A'}"
            await bot.send_message(ADMIN_ID, error_message[:4000])  # Telegram message limit
    except Exception as e:
        logging.error(f"Failed to notify admin: {e}")
    
    # Try to respond to user
    try:
        if update and update.message:
            await update.message.answer("😔 Произошла ошибка. Попробуйте снова или используйте /start")
        elif update and update.callback_query:
            await update.callback_query.message.answer("😔 Произошла ошибка. Попробуйте снова или используйте /start")
    except:
        pass
    
    return True

async def main():
    # Configure logging with better format
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('data/bot.log'),
            logging.StreamHandler()
        ]
    )
    
    if not TELEGRAM_BOT_TOKEN:
        logging.error("Error: TELEGRAM_BOT_TOKEN is not set.")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    
    # Initialize Database
    init_db()
    
    # Register error handler
    dp.errors.register(error_handler)

    # Register middleware
    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())

    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(carousel_flow.router)

    logging.info("Bot started...")
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
        print("Bot stopped")

