from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from loguru import logger
from pathlib import Path

from botspot.core.bot_manager import BotManager

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

from .routers.settings import router as settings_router
from .router import app, router as main_router

# Initialize bot and dispatcher.
# Settings router goes first so its commands match before the catch-all capture handler.
dp = Dispatcher()
dp.include_router(settings_router)
dp.include_router(main_router)


def main(debug=False) -> None:
    import sys

    # loguru directly — avoid importing calmlib, whose v2 __init__ eagerly imports
    # rich/pymongo (undeclared deps). See notes-ai.
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if debug else "INFO")

    # Initialize Bot instance with a default parse mode
    bot = Bot(
        token=app.config.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Initialize BotManager with default components
    bm = BotManager(
        bot=bot,
        error_handler={"enabled": True},
        ask_user={"enabled": True},
        bot_commands_menu={"enabled": True},
        message_aggregator={"enabled": True},
    )

    # Setup dispatcher with our components
    bm.setup_dispatcher(dp)

    # Start polling
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
