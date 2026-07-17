"""
utils/auth.py
=============
Authentication guard for the Telegram bot.
Only messages from the ALLOWED_CHAT_ID in .env are processed.
"""

import logging
from functools import wraps
from typing import Callable, Any

from telegram import Update
from telegram.ext import ContextTypes

from config.config import ALLOWED_CHAT_ID
from utils.i18n import t

logger = logging.getLogger(__name__)


def authorized_only(handler: Callable) -> Callable:
    """
    Decorator that blocks any Telegram user who is not the owner.

    Usage::

        @authorized_only
        async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            ...
    """
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        if update.effective_chat is None:
            return

        chat_id = update.effective_chat.id

        if chat_id != ALLOWED_CHAT_ID:
            logger.warning(
                "Unauthorized access attempt from chat_id=%s", chat_id
            )
            await update.message.reply_text(t("unauthorized"))
            return

        return await handler(update, context, *args, **kwargs)

    return wrapper
