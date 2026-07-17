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

from config.config import get_user_role, ALLOWED_CHAT_ID
from utils.i18n import t
from utils.audit import log_action

logger = logging.getLogger(__name__)

# Intrusion detection tracker: chat_id -> count
_failed_attempts = {}
BLACKLIST_THRESHOLD = 3

def requires_role(role: str = "any") -> Callable:
    """
    Decorator that blocks users based on their role in users.json.
    Roles: 'admin', 'viewer', 'any' (admin or viewer).

    Usage::

        @requires_role("admin")
        async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            ...
    """
    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
            if update.effective_chat is None:
                return

            chat_id = update.effective_chat.id
            username = update.effective_user.username if update.effective_user else "Unknown"
            
            # Identify the command or action
            action = "unknown_action"
            if update.message and update.message.text:
                action = update.message.text
            elif update.callback_query and update.callback_query.data:
                action = f"callback_{update.callback_query.data}"

            # Check blacklist
            if _failed_attempts.get(chat_id, 0) >= BLACKLIST_THRESHOLD:
                return # Silently ignore completely blocked users

            user_role = get_user_role(chat_id)

            if not user_role:
                _failed_attempts[chat_id] = _failed_attempts.get(chat_id, 0) + 1
                logger.warning("Unauthorized access attempt from chat_id=%s (Attempt %d)", chat_id, _failed_attempts[chat_id])
                log_action(chat_id, username, f"BLOCKED: {action}")
                
                if _failed_attempts[chat_id] == BLACKLIST_THRESHOLD:
                    # Notify admin
                    try:
                        await context.bot.send_message(
                            chat_id=ALLOWED_CHAT_ID, 
                            text=f"🚨 *INTRUSION ALERT* 🚨\nID: `{chat_id}` (@{username})\nĐã bị đưa vào Blacklist vì cố gắng truy cập trái phép 3 lần.",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                else:
                    await update.message.reply_text("🚫 Bạn không có quyền truy cập Bot này.")
                return

            if role == "admin" and user_role != "admin":
                log_action(chat_id, username, f"DENIED (Requires admin): {action}")
                logger.warning("Permission denied for chat_id=%s (requires admin)", chat_id)
                await update.message.reply_text("🚫 Bạn cần quyền Admin để chạy lệnh này.")
                return

            # Log successful action
            log_action(chat_id, username, f"ALLOWED: {action}")
            return await handler(update, context, *args, **kwargs)

        return wrapper
    return decorator

# Legacy compatibility
authorized_only = requires_role("admin")

import uuid
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

pending_actions = {}

def requires_2fa(handler: Callable) -> Callable:
    """
    Decorator for high-risk commands. Sends a confirmation inline keyboard.
    Must be stacked after @requires_role.
    """
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        if update.effective_chat is None:
            return

        chat_id = update.effective_chat.id
        
        # Store context
        action_id = str(uuid.uuid4())[:8]
        pending_actions[action_id] = {
            "handler": handler,
            "args": args,
            "kwargs": kwargs,
            "update": update,
            "context": context
        }

        # Ask for confirmation
        keyboard = [
            [
                InlineKeyboardButton("✅ Xác Nhận", callback_data=f"2fa_confirm_{action_id}"),
                InlineKeyboardButton("❌ Hủy", callback_data=f"2fa_cancel_{action_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        command_text = update.message.text if update.message and update.message.text else "hành động này"
        
        # If it's a callback query, we should reply to the message, not the query
        if update.callback_query:
            await update.callback_query.message.reply_text(
                f"⚠️ *XÁC NHẬN BẢO MẬT 2 BƯỚC*\n\nBạn đang chuẩn bị thực thi lệnh nguy hiểm từ menu.\n\nVui lòng xác nhận để tiếp tục.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            await update.callback_query.answer()
        else:
            await update.message.reply_text(
                f"⚠️ *XÁC NHẬN BẢO MẬT 2 BƯỚC*\n\nBạn đang chuẩn bị thực thi:\n`{command_text}`\n\nVui lòng xác nhận để tiếp tục.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        return

    return wrapper
