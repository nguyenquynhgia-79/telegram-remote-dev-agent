"""
modules/memory.py
=================
Lưu trữ lịch sử hội thoại giữa user và AI.

File lưu: logs/history.json
Format mỗi entry: {id, timestamp, prompt, response, ai_command}

Khi gửi prompt mới, lịch sử sẽ được đính kèm vào stdin của AI CLI:
    [Lịch sử hội thoại]
    User: ...
    AI:   ...
    ──────────────
    [Yêu cầu hiện tại]
    User: <prompt mới>

Lệnh:
    /memory          — Xem 5 lần hội thoại gần nhất
    /memory 10       — Xem 10 lần gần nhất
    /memory clear    — Xoá toàn bộ lịch sử
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import config.config as cfg

logger = logging.getLogger(__name__)

HISTORY_FILE: Path = cfg.LOGS_DIR / "history.json"

# Đọc giới hạn từ config (.env) thay vì hardcode
MAX_HISTORY_ENTRIES: int = cfg.MEMORY_MAX_ENTRIES
MAX_CONTEXT_EXCHANGES: int = cfg.MEMORY_CONTEXT_N
MAX_RESPONSE_STORE_CHARS: int = 1500  # Giảm từ 2000 → 1500 để tiết kiệm token


# ─────────────────────────────────────────────────────────────
# Đọc / Ghi file
# ─────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    """Đọc toàn bộ history từ file JSON."""
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Không đọc được history: %s", exc)
    return []


def _save(entries: list[dict]) -> None:
    """Ghi history ra file JSON."""
    try:
        cfg.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Không ghi được history: %s", exc)


# ─────────────────────────────────────────────────────────────
# API công khai
# ─────────────────────────────────────────────────────────────

def add_exchange(prompt: str, response: str) -> None:
    """
    Lưu một cặp (prompt, response) vào history.

    Args:
        prompt:   Yêu cầu của người dùng.
        response: Câu trả lời của AI (stdout + stderr).
    """
    entries = _load()

    # Cắt response nếu quá dài để tránh file phình to
    stored_response = response[:MAX_RESPONSE_STORE_CHARS]
    if len(response) > MAX_RESPONSE_STORE_CHARS:
        stored_response += f"\n... (cắt ngắn, tổng {len(response)} ký tự)"

    ai_cmd = cfg.get_active_ai_command()

    entry = {
        "id":         len(entries) + 1,
        "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prompt":     prompt,
        "response":   stored_response,
        "ai_command": ai_cmd,
    }
    entries.append(entry)

    # Giữ tối đa MAX_HISTORY_ENTRIES entries
    if len(entries) > MAX_HISTORY_ENTRIES:
        entries = entries[-MAX_HISTORY_ENTRIES:]
        # Reset lại ID
        for i, e in enumerate(entries, 1):
            e["id"] = i

    _save(entries)
    logger.info("History: đã lưu exchange #%d", entry["id"])


def get_recent(n: int = MAX_CONTEXT_EXCHANGES) -> list[dict]:
    """
    Trả về N exchanges gần nhất.

    Args:
        n: Số exchanges cần lấy.

    Returns:
        List các dict {id, timestamp, prompt, response}.
    """
    entries = _load()
    return entries[-n:] if entries else []


def format_for_ai(prompt: str, context_n: int = MAX_CONTEXT_EXCHANGES) -> str:
    """
    Tạo nội dung đầy đủ để gửi vào stdin của AI CLI.
    Bao gồm lịch sử hội thoại + yêu cầu hiện tại.

    Format:
        [Lịch sử hội thoại - X lần gần nhất]
        ──────────────
        [#1 - 2026-07-17 02:30]
        User: ...
        AI:   ...
        ──────────────
        ...
        [Yêu cầu hiện tại]
        User: <prompt>

    Args:
        prompt:    Yêu cầu mới của người dùng.
        context_n: Số exchanges lịch sử đưa vào context.

    Returns:
        Chuỗi đầy đủ để pipe vào stdin của AI CLI.
    """
    history = get_recent(context_n)

    if not history:
        # Không có lịch sử → gửi thẳng prompt
        return prompt

    # Xây dựng phần lịch sử
    lines = [
        f"[Lịch sử hội thoại — {len(history)} lần gần nhất]",
        "Dưới đây là các yêu cầu và trả lời trước đó trong dự án này.",
        "Hãy dựa vào ngữ cảnh này để trả lời yêu cầu hiện tại.",
        "",
    ]

    for entry in history:
        lines.append(f"{'─' * 40}")
        lines.append(f"[#{entry['id']} — {entry['timestamp']}]")
        lines.append(f"User: {entry['prompt']}")
        lines.append(f"AI:   {entry['response']}")
        lines.append("")

    lines.append("─" * 40)
    lines.append("[Yêu cầu hiện tại]")
    lines.append(f"User: {prompt}")

    return "\n".join(lines)


def clear_history() -> str:
    """
    Xoá toàn bộ lịch sử hội thoại.

    Returns:
        Thông báo kết quả.
    """
    entries = _load()
    count = len(entries)

    if count == 0:
        return "ℹ️ *Memory* — Lịch sử đang trống, không có gì để xoá."

    try:
        HISTORY_FILE.write_text("[]", encoding="utf-8")
        logger.info("History: đã xoá %d entries", count)
        return f"🗑️ *Memory* — Đã xoá *{count}* lần hội thoại."
    except Exception as exc:  # noqa: BLE001
        logger.error("Không xoá được history: %s", exc)
        return f"❌ Lỗi khi xoá history: {exc}"


def format_for_telegram(n: int = 5) -> str:
    """
    Format lịch sử để hiển thị trên Telegram.

    Args:
        n: Số exchanges gần nhất cần hiển thị.

    Returns:
        Chuỗi Markdown cho Telegram.
    """
    entries = _load()

    if not entries:
        return (
            "🧠 *Memory — Lịch sử hội thoại*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "_(Chưa có hội thoại nào. Dùng `/ask` để bắt đầu.)_"
        )

    recent = entries[-n:]
    total = len(entries)

    lines = [
        f"🧠 *Memory — {len(recent)} / {total} hội thoại gần nhất*",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for entry in recent:
        prompt_short = entry["prompt"][:120]
        if len(entry["prompt"]) > 120:
            prompt_short += "..."

        response_short = entry["response"][:200]
        if len(entry["response"]) > 200:
            response_short += "..."

        lines.append(
            f"*#{entry['id']}* — `{entry['timestamp']}`\n"
            f"👤 *User:* {prompt_short}\n"
            f"🤖 *AI:* {response_short}\n"
        )

    lines.append(f"_Dùng `/memory clear` để xoá | `/memory 10` để xem nhiều hơn_")
    return "\n".join(lines)


def get_stats() -> str:
    """Trả về thống kê ngắn gọn về history."""
    entries = _load()
    if not entries:
        return "_(Chưa có hội thoại nào)_"

    first = entries[0]["timestamp"]
    last  = entries[-1]["timestamp"]
    size_kb = HISTORY_FILE.stat().st_size / 1024 if HISTORY_FILE.exists() else 0

    return (
        f"📊 *Thống kê Memory*\n"
        f"  Tổng số hội thoại: *{len(entries)}*\n"
        f"  Từ: `{first}`\n"
        f"  Đến: `{last}`\n"
        f"  Kích thước file: `{size_kb:.1f} KB`"
    )
