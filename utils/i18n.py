"""
utils/i18n.py
=============
Internationalization (i18n) module.
Hỗ trợ tiếng Việt (mặc định) và tiếng Anh.
Ngôn ngữ được lưu vào config/lang.json (không cần database).
"""

import json
import logging
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

LangCode = Literal["vi", "en"]
_LANG_FILE = Path(__file__).parent.parent / "config" / "lang.json"
_current_lang: LangCode = "vi"  # Mặc định tiếng Việt


# ─────────────────────────────────────────────────────────────
# Ngôn ngữ persistence
# ─────────────────────────────────────────────────────────────

def load_lang() -> None:
    """Đọc ngôn ngữ đã lưu từ file. Gọi khi khởi động."""
    global _current_lang
    try:
        if _LANG_FILE.exists():
            data = json.loads(_LANG_FILE.read_text(encoding="utf-8"))
            lang = data.get("lang", "vi")
            if lang in ("vi", "en"):
                _current_lang = lang
    except Exception:  # noqa: BLE001
        pass  # Giữ mặc định tiếng Việt nếu lỗi


def save_lang(lang: LangCode) -> None:
    """Lưu ngôn ngữ ra file."""
    global _current_lang
    _current_lang = lang
    try:
        _LANG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LANG_FILE.write_text(json.dumps({"lang": lang}), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Không thể lưu cài đặt ngôn ngữ: %s", exc)


def get_lang() -> LangCode:
    """Trả về ngôn ngữ hiện tại."""
    return _current_lang


# ─────────────────────────────────────────────────────────────
# Bảng dịch
# ─────────────────────────────────────────────────────────────

_STRINGS: dict[str, dict[LangCode, str]] = {

    # ── Lệnh chung ───────────────────────────────────────────
    "unauthorized": {
        "vi": "⛔ Không được phép truy cập.",
        "en": "⛔ Unauthorized.",
    },
    "unknown_cmd": {
        "vi": "❓ Lệnh không xác định. Gõ `/help` để xem danh sách lệnh.",
        "en": "❓ Unknown command. Type `/help` to see all available commands.",
    },
    "task_started": {
        "vi": "⏳ {msg}…",
        "en": "⏳ {msg}…",
    },

    # ── /start & /help ────────────────────────────────────────
    "start_text": {
        "vi": (
            "🤖 *Telegram Remote Dev Agent*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Bot đang hoạt động và sẵn sàng\\!\n\n"
            "*Hệ thống*\n"
            "  `/ping` — Kiểm tra bot còn sống\n"
            "  `/status` — CPU, RAM, Disk, Uptime\n"
            "  `/ip` — Địa chỉ IP local và public\n\n"
            "*Git*\n"
            "  `/git status` — Trạng thái working tree\n"
            "  `/git pull` — Pull code mới nhất\n"
            "  `/git push` — Push lên remote\n"
            "  `/git branch` — Danh sách branch\n"
            "  `/git log` — 10 commit gần nhất\n"
            "  `/git checkout <branch>` — Chuyển branch\n\n"
            "*Build*\n"
            "  `/build` — Chạy lệnh build\n"
            "  `/buildcheck` — Build và chẩn đoán lỗi compiler tự động 🔍\n\n"
            "*Docker*\n"
            "  `/docker up` — Khởi động containers\n"
            "  `/docker down` — Dừng containers\n"
            "  `/docker restart` — Khởi động lại\n"
            "  `/docker ps` — Danh sách container đang chạy\n"
            "  `/docker logs` — Xem log container\n\n"
            "*Logs*\n"
            "  `/log` — 100 dòng log gần nhất\n"
            "  `/log 500` — 500 dòng log gần nhất\n\n"
            "*AI Agent*\n"
            "  `/ask <prompt>` — Gửi yêu cầu cho AI\n"
            "  `/troly` — Trợ lý thông minh phân tích dự án & đề xuất 🧠\n\n"
            "*Cài đặt*\n"
            "  `/menu` — Bảng điều khiển nút bấm nhanh (Dashboard) 🎛\n"
            "  `/projects` — Quản lý danh sách & chọn dự án con (alias: `/p`) 🗂\n"
            "  `/lang vi` — Chuyển sang tiếng Việt \ud83c\uddbb\ud83c\uddf3\n"
            "  `/lang en` — Switch to English \ud83c\uddec\ud83c\udde7\n\n"
            "*AI Context*\n"
            "  `/context` — Xem GEMINI.md (bộ nhớ dài hạn của AI)\n"
            "  `/context update` — Tự động cập nhật GEMINI.md từ project\n\n"
            "*Explorer & Terminal*\n"
            "  `/ls [path]` — Liệt kê file và thư mục con\n"
            "  `/cat <file>` — Đọc nội dung code file\n"
            "  `/run <command>` — Chạy lệnh shell tùy ý trong project\n\n"
            "  `/help` — Hiển thị trợ giúp này\n"
        ),
        "en": (
            "🤖 *Telegram Remote Dev Agent*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Bot is online and ready\\!\n\n"
            "*System*\n"
            "  `/ping` — Check if bot is alive\n"
            "  `/status` — CPU, RAM, Disk, Uptime\n"
            "  `/ip` — Local & public IP\n\n"
            "*Git*\n"
            "  `/git status` — Working tree status\n"
            "  `/git pull` — Pull latest\n"
            "  `/git push` — Push commits\n"
            "  `/git branch` — List branches\n"
            "  `/git log` — Last 10 commits\n"
            "  `/git checkout <branch>` — Switch branch\n\n"
            "*Build*\n"
            "  `/build` — Run build command\n"
            "  `/buildcheck` — Build & auto-diagnose compiler errors 🔍\n\n"
            "*Docker*\n"
            "  `/docker up` — Start containers\n"
            "  `/docker down` — Stop containers\n"
            "  `/docker restart` — Restart containers\n"
            "  `/docker ps` — List running containers\n"
            "  `/docker logs` — View container logs\n\n"
            "*Logs*\n"
            "  `/log` — Last 100 log lines\n"
            "  `/log 500` — Last 500 log lines\n\n"
            "*AI Agent*\n"
            "  `/ask <prompt>` — Send prompt to AI agent\n"
            "  `/troly` — Smart assistant analyzing project & suggestions 🧠\n\n"
            "*Settings*\n"
            "  `/menu` — Dashboard menu with buttons 🎛\n"
            "  `/projects` — Manage & select active project (alias: `/p`) 🗂\n"
            "  `/lang vi` — Chuyển sang tiếng Việt \ud83c\uddbb\ud83c\uddf3\n"
            "  `/lang en` — Switch to English \ud83c\uddec\ud83c\udde7\n\n"
            "*AI Context*\n"
            "  `/context` — View GEMINI.md (AI long-term memory)\n"
            "  `/context update` — Auto-update GEMINI.md from project\n\n"
            "*Explorer & Terminal*\n"
            "  `/ls [path]` — List files and subfolders\n"
            "  `/cat <file>` — Read file content\n"
            "  `/run <command>` — Run any shell command in project\n\n"
            "  `/help` — Show this help\n"
        ),
    },

    # ── /lang ─────────────────────────────────────────────────
    "lang_switched_vi": {
        "vi": "🇻🇳 Đã chuyển sang *tiếng Việt*.",
        "en": "🇻🇳 Đã chuyển sang *tiếng Việt*.",
    },
    "lang_switched_en": {
        "vi": "🇬🇧 Switched to *English*.",
        "en": "🇬🇧 Switched to *English*.",
    },
    "lang_already": {
        "vi": "ℹ️ Bot đang dùng ngôn ngữ này rồi.",
        "en": "ℹ️ Bot is already using this language.",
    },
    "lang_invalid": {
        "vi": "⚠️ Ngôn ngữ không hợp lệ. Dùng `/lang vi` hoặc `/lang en`.",
        "en": "⚠️ Invalid language. Use `/lang vi` or `/lang en`.",
    },

    # ── /ping ─────────────────────────────────────────────────
    "ping_response": {
        "vi": "🏓 *Pong\\!* Bot đang hoạt động tốt.",
        "en": "🏓 *Pong\\!* Bot is alive and responding.",
    },

    # ── /status ───────────────────────────────────────────────
    "status_title": {
        "vi": "🖥️ *Trạng thái hệ thống*",
        "en": "🖥️ *System Status*",
    },
    "status_host": {
        "vi": "🏠 *Máy chủ:*",
        "en": "🏠 *Host:*",
    },
    "status_os": {
        "vi": "💻 *Hệ điều hành:*",
        "en": "💻 *OS:*",
    },
    "status_uptime": {
        "vi": "⏱️ *Uptime Agent:*",
        "en": "⏱️ *Agent Uptime:*",
    },
    "status_cpu": {
        "vi": "🔲 *CPU:*",
        "en": "🔲 *CPU:*",
    },
    "status_ram": {
        "vi": "🧠 *RAM:*",
        "en": "🧠 *RAM:*",
    },
    "status_disk": {
        "vi": "💾 *Ổ đĩa:*",
        "en": "💾 *Disk:*",
    },
    "status_error": {
        "vi": "❌ Lỗi khi thu thập trạng thái hệ thống: {err}",
        "en": "❌ Error collecting system status: {err}",
    },

    # ── /ip ───────────────────────────────────────────────────
    "ip_title": {
        "vi": "🌐 *Địa chỉ IP*",
        "en": "🌐 *IP Addresses*",
    },
    "ip_local": {
        "vi": "🏠 *IP nội bộ:*",
        "en": "🏠 *Local IP:*",
    },
    "ip_public": {
        "vi": "🌍 *IP công khai:*",
        "en": "🌍 *Public IP:*",
    },
    "ip_unavailable": {
        "vi": "Không khả dụng (mất kết nối mạng?)",
        "en": "Unavailable (no internet?)",
    },

    # ── Git ───────────────────────────────────────────────────
    "git_title": {
        "vi": "🔧 *Git — {sub}*",
        "en": "🔧 *Git — {sub}*",
    },
    "git_path": {
        "vi": "📁 Thư mục:",
        "en": "📁 Path:",
    },
    "git_success": {
        "vi": "✅ Thành công",
        "en": "✅ Success",
    },
    "git_failed": {
        "vi": "❌ Thất bại",
        "en": "❌ Failed",
    },
    "git_timeout": {
        "vi": "⏱️ Hết thời gian chờ",
        "en": "⏱️ Timed out",
    },
    "git_sub_status":   {"vi": "Status",           "en": "Status"},
    "git_sub_pull":     {"vi": "Pull",              "en": "Pull"},
    "git_sub_push":     {"vi": "Push",              "en": "Push"},
    "git_sub_branch":   {"vi": "Branch",            "en": "Branch"},
    "git_sub_log":      {"vi": "Log (cuối {n})",    "en": "Log (last {n})"},
    "git_sub_checkout": {"vi": "Checkout → {b}",    "en": "Checkout → {b}"},
    "git_checkout_usage": {
        "vi": "⚠️ Cách dùng: `/git checkout <branch>`",
        "en": "⚠️ Usage: `/git checkout <branch>`",
    },
    "git_unknown_sub": {
        "vi": (
            "⚠️ Lệnh git không hợp lệ: `{sub}`\n"
            "Dùng: `status`, `pull`, `push`, `branch`, `log`, `checkout <branch>`"
        ),
        "en": (
            "⚠️ Unknown git subcommand: `{sub}`\n"
            "Use: `status`, `pull`, `push`, `branch`, `log`, `checkout <branch>`"
        ),
    },

    # ── Git background messages ────────────────────────────────
    "git_running_status":   {"vi": "Đang chạy git status",       "en": "Running git status"},
    "git_running_pull":     {"vi": "Đang pull từ remote",         "en": "Pulling from remote"},
    "git_running_push":     {"vi": "Đang push lên remote",        "en": "Pushing to remote"},
    "git_running_branch":   {"vi": "Đang liệt kê branches",       "en": "Listing branches"},
    "git_running_log":      {"vi": "Đang lấy {n} commit gần nhất","en": "Getting last {n} commits"},
    "git_running_checkout": {"vi": "Đang chuyển sang branch `{b}`","en": "Checking out branch `{b}`"},

    # ── Build ─────────────────────────────────────────────────
    "build_title": {
        "vi": "🔨 *Build*",
        "en": "🔨 *Build*",
    },
    "build_command": {
        "vi": "📋 Lệnh:",
        "en": "📋 Command:",
    },
    "build_path": {
        "vi": "📁 Thư mục:",
        "en": "📁 Path:",
    },
    "build_success": {
        "vi": "✅ Build thành công",
        "en": "✅ Build succeeded",
    },
    "build_failed": {
        "vi": "❌ Build thất bại (exit code {code})",
        "en": "❌ Build failed (exit code {code})",
    },
    "build_timeout": {
        "vi": "⏱️ Hết thời gian chờ",
        "en": "⏱️ Timed out",
    },
    "build_no_cmd": {
        "vi": "⚠️ *Build* — Chưa cấu hình `BUILD_COMMAND` trong `.env`.",
        "en": "⚠️ *Build* — No `BUILD_COMMAND` configured in `.env`.",
    },
    "build_starting": {
        "vi": "Build đang bắt đầu",
        "en": "Build started",
    },

    # ── Docker ────────────────────────────────────────────────
    "docker_title": {
        "vi": "🐳 *Docker — {sub}*",
        "en": "🐳 *Docker — {sub}*",
    },
    "docker_success": {
        "vi": "✅ Thành công",
        "en": "✅ Success",
    },
    "docker_failed": {
        "vi": "❌ Thất bại",
        "en": "❌ Failed",
    },
    "docker_timeout": {
        "vi": "⏱️ Hết thời gian chờ",
        "en": "⏱️ Timed out",
    },
    "docker_sub_up":      {"vi": "Up (Khởi động)",        "en": "Up"},
    "docker_sub_down":    {"vi": "Down (Dừng)",            "en": "Down"},
    "docker_sub_restart": {"vi": "Restart (Khởi động lại)","en": "Restart"},
    "docker_sub_ps":      {"vi": "PS (Đang chạy)",         "en": "PS (running containers)"},
    "docker_sub_logs":    {"vi": "Logs (cuối {n} dòng)",   "en": "Logs (last {n} lines)"},
    "docker_running_up":      {"vi": "Đang khởi động containers",      "en": "Starting containers"},
    "docker_running_down":    {"vi": "Đang dừng containers",           "en": "Stopping containers"},
    "docker_running_restart": {"vi": "Đang khởi động lại containers",  "en": "Restarting containers"},
    "docker_running_ps":      {"vi": "Đang liệt kê containers",        "en": "Listing containers"},
    "docker_running_logs":    {"vi": "Đang lấy log container",         "en": "Fetching container logs"},
    "docker_unknown_sub": {
        "vi": (
            "⚠️ Lệnh docker không hợp lệ: `{sub}`\n"
            "Dùng: `up`, `down`, `restart`, `ps`, `logs [số dòng] [service]`"
        ),
        "en": (
            "⚠️ Unknown docker subcommand: `{sub}`\n"
            "Use: `up`, `down`, `restart`, `ps`, `logs [tail] [service]`"
        ),
    },

    # ── Logs ──────────────────────────────────────────────────
    "log_title": {
        "vi": "📋 *Logs* (cuối {shown}/{total} dòng)",
        "en": "📋 *Logs* (last {shown} of {total} lines)",
    },
    "log_not_found": {
        "vi": (
            "📋 *Logs*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ Không tìm thấy file log tại `{path}`.\n"
            "Bot chưa ghi log nào."
        ),
        "en": (
            "📋 *Logs*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ Log file not found at `{path}`.\n"
            "The agent may not have logged anything yet."
        ),
    },
    "log_error": {
        "vi": "❌ Lỗi khi đọc log: {err}",
        "en": "❌ Error reading logs: {err}",
    },
    "log_empty": {
        "vi": "(file log trống)",
        "en": "(log file is empty)",
    },

    # ── AI ────────────────────────────────────────────────────
    "ai_title": {
        "vi": "🤖 *Kết quả AI Agent*",
        "en": "🤖 *AI Agent Result*",
    },
    "ai_cont": {
        "vi": "🤖 *Kết quả AI (tiếp {i}/{total})*",
        "en": "🤖 *AI Output (cont. {i}/{total})*",
    },
    "ai_prompt_label": {
        "vi": "Yêu cầu:",
        "en": "Prompt:",
    },
    "ai_status_success": {
        "vi": "✅ Thành công",
        "en": "✅ Success",
    },
    "ai_status_failed": {
        "vi": "❌ Exit khác 0",
        "en": "❌ Non-zero exit",
    },
    "ai_timeout": {
        "vi": (
            "⏱️ *AI — Hết thời gian*\n"
            "Lệnh AI vượt quá {timeout}s và đã bị dừng.\n"
            "Yêu cầu: `{prompt}`"
        ),
        "en": (
            "⏱️ *AI — Timed Out*\n"
            "The AI command exceeded {timeout}s and was killed.\n"
            "Prompt: `{prompt}`"
        ),
    },
    "ai_not_found": {
        "vi": (
            "💥 *AI — Lỗi*\n"
            "```\n{err}\n```\n"
            "Lệnh `{cmd}` có được cài và có trong PATH không?"
        ),
        "en": (
            "💥 *AI — Error*\n"
            "```\n{err}\n```\n"
            "Is `{cmd}` installed and available on PATH?"
        ),
    },
    "ai_no_cmd": {
        "vi": "⚠️ *AI* — Chưa cấu hình `AI_COMMAND` trong `.env`.",
        "en": "⚠️ *AI* — No `AI_COMMAND` configured in `.env`.",
    },
    "ai_no_prompt": {
        "vi": "⚠️ Cách dùng: `/ask <yêu cầu của bạn>`\n\nVí dụ: `/ask Sửa lỗi đăng nhập`",
        "en": "⚠️ Usage: `/ask <your prompt>`\n\nExample: `/ask Fix the login bug`",
    },
    "ai_running": {
        "vi": "Đang gửi cho AI: _{prompt}_",
        "en": "Sending to AI: _{prompt}_",
    },
    "ai_no_output": {
        "vi": "(không có output)",
        "en": "(no output)",
    },

    # ── Executor chung ────────────────────────────────────────
    "exec_no_output": {
        "vi": "(không có output)",
        "en": "(no output)",
    },
    "exec_exception": {
        "vi": "💥 Lỗi không mong đợi:\n```\n{err}\n```",
        "en": "💥 Unexpected error:\n```\n{err}\n```",
    },
}


# ─────────────────────────────────────────────────────────────
# Hàm dịch chính
# ─────────────────────────────────────────────────────────────

def t(key: str, **kwargs: str | int) -> str:
    """
    Trả về chuỗi dịch cho key theo ngôn ngữ hiện tại.

    Args:
        key:    Tên chuỗi cần dịch.
        **kwargs: Các biến thay thế trong chuỗi (vd: {n}, {err}).

    Returns:
        Chuỗi đã dịch và thay thế biến.
    """
    lang = _current_lang
    entry = _STRINGS.get(key)
    if entry is None:
        logger.warning("i18n: missing key '%s'", key)
        return key
    text = entry.get(lang) or entry.get("vi") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as exc:
            logger.warning("i18n: format error for key '%s': %s", key, exc)
    return text
