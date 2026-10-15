"""Entry point for the assistant bot."""

import logging
import sys

from telegram.ext import Application, CommandHandler

from bot import db
from bot.config import config
from bot.handlers import (
    add_note,
    ask,
    currency,
    delete_note,
    error_handler,
    help_command,
    list_notes,
    start,
    weather,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Create and configure the Telegram application."""
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("note", add_note))
    app.add_handler(CommandHandler("notes", list_notes))
    app.add_handler(CommandHandler("delnote", delete_note))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("currency", currency))
    app.add_handler(CommandHandler("ask", ask))

    # Error handler
    app.add_error_handler(error_handler)

    return app


def main() -> None:
    """Run the bot."""
    try:
        config.validate()
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)

    db.init_db()
    logger.info("Database initialized.")

    app = build_application()
    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
