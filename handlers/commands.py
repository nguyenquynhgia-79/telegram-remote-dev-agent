"""
handlers/commands.py
====================
Telegram command handlers.
Each handler is decorated with @authorized_only to enforce access control.
Long-running tasks are launched as background asyncio tasks so the bot
remains responsive.
"""

import asyncio
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import config.config as cfg
from config.config import MAX_MESSAGE_LENGTH
from modules import ai, build, docker, git, logs, system
import modules.context as modules_context
import modules.memory as modules_memory
import modules.explorer as modules_explorer
import modules.assistant as modules_assistant
import modules.buildcheck as modules_buildcheck
import modules.projects as modules_projects
from utils.auth import authorized_only
from utils.i18n import t, get_lang, save_lang

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

async def _send_long(update: Update, text: str) -> None:
    """
    Send a message that may exceed Telegram's 4096-char limit.
    Splits the text into chunks and sends each separately.
    Works for both Messages and CallbackQueries.
    """
    if not text:
        msg = update.effective_message
        if msg:
            await msg.reply_text("(empty response)")
        return

    msg = update.effective_message
    if not msg:
        return

    for i in range(0, len(text), MAX_MESSAGE_LENGTH):
        chunk = text[i:i + MAX_MESSAGE_LENGTH]
        try:
            await msg.reply_text(chunk, parse_mode="Markdown")
        except Exception:  # noqa: BLE001
            await msg.reply_text(chunk)


async def _background_task(
    update: Update,
    coro_factory,
    start_msg: str,
) -> None:
    """
    Run an async coroutine in the background.
    Sends a 'started' message immediately, then sends the result when done.
    Works for both Messages and CallbackQueries.
    """
    msg = update.effective_message
    if not msg:
        return

    await msg.reply_text(
        t("task_started", msg=start_msg),
        parse_mode="Markdown",
    )

    async def _run():
        try:
            result = await coro_factory()
            if isinstance(result, list):
                for part in result:
                    await _send_long(update, part)
            else:
                await _send_long(update, result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Background task error")
            await msg.reply_text(
                t("exec_exception", err=str(exc)),
                parse_mode="Markdown",
            )

    asyncio.create_task(_run())


# ─────────────────────────────────────────────────────────────
# System Commands
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — Thông điệp chào mừng với danh sách lệnh."""
    await update.message.reply_text(t("start_text"), parse_mode="MarkdownV2")


@authorized_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — Alias của /start."""
    await cmd_start(update, context)


@authorized_only
async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ping — Kiểm tra bot còn sống."""
    await update.message.reply_text(t("ping_response"), parse_mode="Markdown")


@authorized_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status — Tổng quan tài nguyên hệ thống."""
    await update.message.reply_text(system.get_status(), parse_mode="Markdown")


@authorized_only
async def cmd_ip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ip — Hiển thị IP local và public."""
    await update.message.reply_text(system.get_ip(), parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────
# Language Command
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /lang <vi|en> — Chuyển đổi ngôn ngữ bot.
    Ví dụ: /lang en  hoặc  /lang vi
    """
    args = context.args or []
    if not args:
        # Hiển thị ngôn ngữ hiện tại
        current = get_lang()
        flag = "🇻🇳 Tiếng Việt" if current == "vi" else "🇬🇧 English"
        hint_vi = "Dùng `/lang en` để chuyển sang tiếng Anh" if current == "vi" else "Use `/lang vi` to switch to Vietnamese"
        await update.message.reply_text(
            f"🌐 Ngôn ngữ hiện tại / Current language: *{flag}*\n{hint_vi}",
            parse_mode="Markdown",
        )
        return

    lang_input = args[0].lower().strip()

    if lang_input not in ("vi", "en"):
        await update.message.reply_text(t("lang_invalid"), parse_mode="Markdown")
        return

    if lang_input == get_lang():
        await update.message.reply_text(t("lang_already"), parse_mode="Markdown")
        return

    save_lang(lang_input)  # type: ignore[arg-type]

    if lang_input == "vi":
        await update.message.reply_text(t("lang_switched_vi"), parse_mode="Markdown")
    else:
        await update.message.reply_text(t("lang_switched_en"), parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────
# Git Commands
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_git(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/git <subcommand> [args] — Điều phối đến hàm git tương ứng."""
    args = context.args or []
    subcommand = args[0].lower() if args else "status"

    if subcommand == "status":
        await _background_task(update, git.git_status, t("git_running_status"))

    elif subcommand == "pull":
        await _background_task(update, git.git_pull, t("git_running_pull"))

    elif subcommand == "push":
        await _background_task(update, git.git_push, t("git_running_push"))

    elif subcommand == "branch":
        await _background_task(update, git.git_branch, t("git_running_branch"))

    elif subcommand == "log":
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        await _background_task(
            update,
            lambda n=n: git.git_log(n),
            t("git_running_log", n=n),
        )

    elif subcommand == "checkout":
        if len(args) < 2:
            await update.message.reply_text(t("git_checkout_usage"), parse_mode="Markdown")
            return
        branch = args[1]
        await _background_task(
            update,
            lambda b=branch: git.git_checkout(b),
            t("git_running_checkout", b=branch),
        )

    else:
        await update.message.reply_text(
            t("git_unknown_sub", sub=subcommand),
            parse_mode="Markdown",
        )


# ─────────────────────────────────────────────────────────────
# Build Commands
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_build(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/build — Chạy lệnh build đã cấu hình."""
    await _background_task(update, build.run_build, t("build_starting"))


@authorized_only
async def cmd_buildcheck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/buildcheck — Tự động chạy build và chẩn đoán lỗi bằng AI."""
    await _background_task(
        update,
        lambda: modules_buildcheck.run_diagnostics(),
        "Đang chạy build và phân tích lỗi tự động",
    )


# ─────────────────────────────────────────────────────────────
# Docker Commands
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_docker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/docker <subcommand> — Điều phối đến hàm docker tương ứng."""
    args = context.args or []
    subcommand = args[0].lower() if args else "ps"

    if subcommand == "up":
        await _background_task(update, docker.docker_up, t("docker_running_up"))

    elif subcommand == "down":
        await _background_task(update, docker.docker_down, t("docker_running_down"))

    elif subcommand == "restart":
        await _background_task(update, docker.docker_restart, t("docker_running_restart"))

    elif subcommand == "ps":
        await _background_task(update, docker.docker_ps, t("docker_running_ps"))

    elif subcommand == "logs":
        tail = int(args[1]) if len(args) > 1 and args[1].isdigit() else 50
        service = args[2] if len(args) > 2 else None
        await _background_task(
            update,
            lambda tail=tail, service=service: docker.docker_logs(tail, service),
            t("docker_running_logs"),
        )

    else:
        await update.message.reply_text(
            t("docker_unknown_sub", sub=subcommand),
            parse_mode="Markdown",
        )


# ─────────────────────────────────────────────────────────────
# Log Commands
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/log [N] — Hiển thị N dòng log gần nhất (mặc định 100)."""
    args = context.args or []
    lines = int(args[0]) if args and args[0].isdigit() else 100
    content = logs.get_logs(lines)
    await _send_long(update, content)


# ─────────────────────────────────────────────────────────────
# AI Commands
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ask <prompt> — Gửi prompt đến AI coding agent."""
    prompt = " ".join(context.args or []).strip()

    if not prompt:
        await update.message.reply_text(t("ai_no_prompt"), parse_mode="Markdown")
        return

    await _background_task(
        update,
        lambda p=prompt: ai.ask_ai(p),
        t("ai_running", prompt=prompt[:80]),
    )


# ─────────────────────────────────────────────────────────────
# Context Commands
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /context          — Xem GEMINI.md hiện tại
    /context update   — Tự động cập nhật GEMINI.md từ project
    """
    args = context.args or []
    subcommand = args[0].lower() if args else "show"

    if subcommand == "update":
        await _background_task(
            update,
            lambda: modules_context.update_context(),
            "Đang quét project và cập nhật GEMINI.md",
        )
    elif subcommand in ("show", "view", ""):
        content_text = modules_context.read_context()
        await _send_long(update, content_text)
    else:
        await update.message.reply_text(
            "⚠️ Dùng: `/context` hoặc `/context update`",
            parse_mode="Markdown",
        )


# ─────────────────────────────────────────────────────────────
# Memory Commands
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /memory          — Xem 5 lần hội thoại gần nhất
    /memory 10       — Xem 10 lần gần nhất
    /memory stats    — Thống kê
    /memory clear    — Xoá toàn bộ lịch sử
    """
    args = context.args or []
    subcommand = args[0].lower() if args else "show"

    if subcommand == "clear":
        result = modules_memory.clear_history()
        await update.message.reply_text(result, parse_mode="Markdown")

    elif subcommand == "stats":
        result = modules_memory.get_stats()
        await update.message.reply_text(result, parse_mode="Markdown")

    elif subcommand.isdigit():
        n = int(subcommand)
        result = modules_memory.format_for_telegram(n)
        await _send_long(update, result)

    else:  # show (default)
        result = modules_memory.format_for_telegram(5)
        await _send_long(update, result)


# ─────────────────────────────────────────────────────────────
# Dashboard Menu & Callback Query Handlers
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/menu — Hiển thị dashboard bằng nút bấm Inline Keyboard."""
    # Bố trí nút bấm theo hàng
    keyboard = [
        [
            InlineKeyboardButton("🖥 Status", callback_data="dash_status"),
            InlineKeyboardButton("🌐 IP Addr", callback_data="dash_ip"),
            InlineKeyboardButton("🏓 Ping", callback_data="dash_ping")
        ],
        [
            InlineKeyboardButton("📂 Git Status", callback_data="dash_git_status"),
            InlineKeyboardButton("🌳 Branches", callback_data="dash_git_branch"),
            InlineKeyboardButton("🪵 Last Log", callback_data="dash_git_log")
        ],
        [
            InlineKeyboardButton("📥 Git Pull", callback_data="dash_git_pull"),
            InlineKeyboardButton("🔨 Run Build", callback_data="dash_build")
        ],
        [
            InlineKeyboardButton("🐳 Docker PS", callback_data="dash_docker_ps"),
            InlineKeyboardButton("🐳 Docker Up", callback_data="dash_docker_up"),
            InlineKeyboardButton("🐳 Docker Down", callback_data="dash_docker_down")
        ],
        [
            InlineKeyboardButton("🧠 AI Context Update", callback_data="dash_context_update"),
            InlineKeyboardButton("📋 View Logs", callback_data="dash_log")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎛 *GQN Bot Dashboard Menu*\n"
        "Nhấn vào các nút bên dưới để điều khiển máy tính nhanh:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def callback_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Điều phối các sự kiện click nút bấm (callback queries)."""
    query = update.callback_query
    
    # Chỉ chủ nhân mới được sử dụng nút bấm
    if query.message.chat_id != cfg.ALLOWED_CHAT_ID:
        await query.answer("⛔ Unauthorized.")
        return

    action = query.data
    logger.info("Button Clicked: %s (chat_id=%s)", action, query.message.chat_id)

    # 1. Trả lời Telegram ngay để tránh nút bấm bị quay tròn (loading)
    await query.answer("⌛ Đang xử lý yêu cầu...")

    # 2. Điều hướng xử lý
    if action == "dash_status":
        await query.message.reply_text(system.get_status(), parse_mode="Markdown")
    elif action == "dash_ip":
        await query.message.reply_text(system.get_ip(), parse_mode="Markdown")
    elif action == "dash_ping":
        await query.message.reply_text(system.get_ping(), parse_mode="Markdown")
        
    elif action == "dash_git_status":
        await _background_task(query, git.git_status, t("git_running_status"))
    elif action == "dash_git_branch":
        await _background_task(query, git.git_branch, t("git_running_branch"))
    elif action == "dash_git_log":
        await _background_task(query, lambda: git.git_log(10), t("git_running_log", n=10))
    elif action == "dash_git_pull":
        await _background_task(query, git.git_pull, t("git_running_pull"))
        
    elif action == "dash_build":
        await _background_task(query, build.run_build, t("build_starting"))
        
    elif action == "dash_docker_ps":
        await _background_task(query, docker.docker_ps, t("docker_running_ps"))
    elif action == "dash_docker_up":
        await _background_task(query, docker.docker_up, t("docker_running_up"))
    elif action == "dash_docker_down":
        await _background_task(query, docker.docker_down, t("docker_running_down"))
        
    elif action == "dash_context_update":
        await _background_task(query, lambda: modules_context.update_context(), "Đang quét project và cập nhật GEMINI.md")
    elif action == "dash_log":
        content = logs.get_logs(100)
        await _send_long(query, content)
        
    elif action.startswith("selectproj_"):
        # Format: selectproj_<tên_project> hoặc selectproj_clear
        project_name = action.split("_", 1)[1]
        result_text = modules_projects.select_project(project_name)
        # Edit tin nhắn menu cũ để thông báo kết quả chọn
        await query.edit_message_text(
            text=result_text,
            parse_mode="Markdown"
        )
        
    elif action.startswith("catpage_"):
        # Format: catpage_<file_id>_<page_num>
        parts = action.split("_")
        if len(parts) == 3:
            file_id = parts[1]
            page_num = int(parts[2])
            filepath = modules_explorer.get_file_from_cache(file_id)
            if filepath:
                # Đọc trang mới
                content_text, reply_markup = modules_explorer.read_file_paged(filepath, page_num)
                # Thay thế tin nhắn cũ bằng trang mới để tạo cảm giác mượt mà không rác chat
                try:
                    await query.edit_message_text(
                        text=content_text,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                except Exception:
                    # Nếu lỗi (ví dụ nội dung không đổi), gửi tin nhắn mới
                    await query.message.reply_text(
                        text=content_text,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
            else:
                await query.message.reply_text("⚠️ Lỗi: Không tìm thấy file trong cache session.")


# ─────────────────────────────────────────────────────────────
# Assistant Commands
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_troly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/troly — Trợ lý chủ động phân tích dự án và đưa gợi ý."""
    # Gửi tin nhắn tạm thời trong lúc quét hệ thống
    msg = update.effective_message
    if not msg:
        return
        
    await _background_task(
        update,
        lambda: modules_assistant.generate_assistant_report(),
        "Trợ lý đang phân tích dự án",
    )


# ─────────────────────────────────────────────────────────────
# Explorer & Terminal Commands
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/projects — Quản lý và chuyển đổi nhanh giữa các dự án."""
    msg = update.effective_message
    if not msg:
        return
        
    keyboard = modules_projects.build_projects_keyboard()
    active_name = cfg.get_active_project_name() or "Chưa chọn (Đang ở Root)"
    
    await msg.reply_text(
        f"🗂 *Quản lý danh sách dự án*\n"
        f"Thư mục gốc: `{cfg.BASE_PATH}`\n"
        f"Dự án hoạt động hiện tại: *{active_name}*\n\n"
        f"Chọn một dự án bên dưới để kích hoạt:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@authorized_only
async def cmd_ls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ls [subpath] — Liệt kê file và thư mục."""
    args = context.args or []
    subpath = args[0] if args else ""
    result = modules_explorer.list_files(subpath)
    await _send_long(update, result)


@authorized_only
async def cmd_cat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cat <filepath> — Xem nội dung file phân trang."""
    args = context.args or []
    if not args:
        await update.message.reply_text("⚠️ Cách dùng: `/cat <đường_dẫn_file_trong_dự_án>`", parse_mode="Markdown")
        return
    filepath = args[0]
    result_text, reply_markup = modules_explorer.read_file_paged(filepath, 1)
    
    msg = update.effective_message
    if msg:
        await msg.reply_text(
            result_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


@authorized_only
async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/run <command> — Chạy lệnh shell tùy ý trong dự án."""
    cmd_str = " ".join(context.args or []).strip()
    if not cmd_str:
        await update.message.reply_text("⚠️ Cách dùng: `/run <lệnh shell>`\n\nVí dụ: `/run npm test`", parse_mode="Markdown")
        return
    
    await _background_task(
        update,
        lambda: modules_explorer.execute_arbitrary(cmd_str),
        f"Chạy lệnh: `{cmd_str}`",
    )


# ─────────────────────────────────────────────────────────────
# Unknown Command Handler
# ─────────────────────────────────────────────────────────────

@authorized_only
async def cmd_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bắt tất cả lệnh không xác định."""
    await update.message.reply_text(t("unknown_cmd"), parse_mode="Markdown")
