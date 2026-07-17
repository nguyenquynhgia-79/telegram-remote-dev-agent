"""
main.py
=======
Entry point for the Telegram Remote Dev Agent.

Usage::

    python main.py

The bot will start polling for updates and remain running until
interrupted with Ctrl+C.
"""

import asyncio
import logging
import sys
from pathlib import Path

from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# ── Local imports ──────────────────────────────────────────────
from utils.i18n import load_lang
import config.config as cfg
from handlers.commands import (
    cmd_lang,
    cmd_context,
    cmd_ls,
    cmd_cat,
    cmd_run,
    cmd_menu,
    cmd_troly,
    cmd_projects,
    callback_dispatcher,
    cmd_ask,
    cmd_build,
    cmd_buildcheck,
    cmd_docker,
    cmd_git,
    cmd_help,
    cmd_ip,
    cmd_log,
    cmd_ping,
    cmd_start,
    cmd_status,
    cmd_unknown,
)

# ── Monitor Background Import
from modules.monitor import start_monitor_loop


# ─────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """Configure logging to both console and rotating log file."""
    import sys
    # Ép console output sử dụng UTF-8 trên Windows để không bị lỗi charmap encode
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass  # Python cũ không có reconfigure, bỏ qua

    from logging.handlers import RotatingFileHandler

    # Ensure logs directory exists
    cfg.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    fmt = "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            cfg.LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB per file
            backupCount=3,
            encoding="utf-8",
        ),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt=date_fmt,
        handlers=handlers,
    )

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────
# Bot commands menu
# ─────────────────────────────────────────────────────────────

BOT_COMMANDS = [
    BotCommand("start",   "Show welcome & command list"),
    BotCommand("help",    "Show command list"),
    BotCommand("ping",    "Check bot is alive"),
    BotCommand("status",  "CPU, RAM, Disk, Uptime"),
    BotCommand("ip",      "Show local and public IP"),
    BotCommand("git",     "Git operations (status/pull/push/...)"),
    BotCommand("build",   "Chạy lệnh build dự án"),
    BotCommand("buildcheck", "Build và tự động chẩn đoán lỗi bằng AI"),
    BotCommand("docker",  "Docker operations (up/down/ps/...)"),
    BotCommand("log",     "Show last N agent log lines"),
    BotCommand("ask",     "Send prompt to AI coding agent"),
    BotCommand("lang",    "Chuyển ngôn ngữ / Switch language (vi|en)"),
    BotCommand("menu",    "Bảng điều khiển nút bấm nhanh (Dashboard)"),
    BotCommand("troly",   "Trợ lý thông minh phân tích dự án & đề xuất"),
    BotCommand("projects", "Quản lý danh sách & chọn dự án con (alias: /p)"),
    BotCommand("context", "Quản lý GEMINI.md (context AI)"),
    BotCommand("ls",      "Xem danh sách file/folder"),
    BotCommand("cat",     "Đọc nội dung 1 file code"),
    BotCommand("run",     "Chạy lệnh shell tùy ý trong project"),
]


# ─────────────────────────────────────────────────────────────
# Application factory
# ─────────────────────────────────────────────────────────────

def build_application() -> Application:
    """Create and configure the Telegram Application with all handlers."""
    app = Application.builder().token(cfg.BOT_TOKEN).build()

    # ── Language handler
    app.add_handler(CommandHandler("lang", cmd_lang))

    # ── Dashboard Menu & Callback handler
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("troly", cmd_troly))
    app.add_handler(CommandHandler("projects", cmd_projects))
    app.add_handler(CommandHandler("p", cmd_projects))  # Alias gõ nhanh
    app.add_handler(CallbackQueryHandler(callback_dispatcher))

    # ── Context (GEMINI.md) handler
    app.add_handler(CommandHandler("context", cmd_context))

    # ── Explorer & Terminal handlers
    app.add_handler(CommandHandler("ls", cmd_ls))
    app.add_handler(CommandHandler("cat", cmd_cat))
    app.add_handler(CommandHandler("run", cmd_run))

    # ── System handlers
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("ping",   cmd_ping))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("ip",     cmd_ip))

    # ── Git handler (single handler dispatches subcommands)
    app.add_handler(CommandHandler("git", cmd_git))

    # ── Build handler
    app.add_handler(CommandHandler("build", cmd_build))
    app.add_handler(CommandHandler("buildcheck", cmd_buildcheck))

    # ── Docker handler (single handler dispatches subcommands)
    app.add_handler(CommandHandler("docker", cmd_docker))

    # ── Log handler
    app.add_handler(CommandHandler("log", cmd_log))

    # ── AI handler
    app.add_handler(CommandHandler("ask", cmd_ask))

    # ── Catch-all for unknown commands
    app.add_handler(
        MessageHandler(filters.COMMAND, cmd_unknown)
    )

    return app


# ─────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """Runs after the bot starts; sets the command menu in Telegram."""
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger = logging.getLogger(__name__)
    me = await application.bot.get_me()
    logger.info("Bot started: @%s (id=%s)", me.username, me.id)
    logger.info("Allowed chat_id: %s", cfg.ALLOWED_CHAT_ID)
    logger.info("Base path: %s", cfg.BASE_PATH)
    logger.info("Active Project: %s", cfg.get_active_project_name() or "None (Root)")
    logger.info("AI command: %s", cfg.get_active_ai_command())
    
    # Khởi động Task giám sát nền tự động
    asyncio.create_task(start_monitor_loop(application))
    
    # Khởi động Web App Dashboard
    from modules.webapp import start_webapp
    asyncio.create_task(start_webapp())


def main() -> None:
    """Bootstrap and run the bot."""
    setup_logging()
    logger = logging.getLogger(__name__)

    # Tải ngôn ngữ đã lưu trước đó
    load_lang()

    logger.info("=" * 60)
    logger.info("Telegram Remote Dev Agent — Starting up")
    logger.info("=" * 60)

    # Validate config (warns about missing optional dirs)
    try:
        cfg.validate()
    except EnvironmentError as exc:
        logger.critical("Configuration error: %s", exc)
        sys.exit(1)

    app = build_application()
    app.post_init = post_init   # type: ignore[assignment]

    logger.info("Bot is polling for updates. Press Ctrl+C to stop.")

    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,   # Ignore messages sent while bot was offline
    )


if __name__ == "__main__":
    main()
