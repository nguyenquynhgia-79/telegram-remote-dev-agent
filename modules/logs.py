"""
modules/logs.py
===============
Log viewer module.
"""

import logging
from pathlib import Path

from config.config import LOG_FILE
from utils.i18n import t

logger = logging.getLogger(__name__)


def get_logs(lines: int = 100) -> str:
    """Read the last `lines` lines from the agent log file."""
    if not LOG_FILE.exists():
        return t("log_not_found", path=str(LOG_FILE))

    try:
        with LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        tail = all_lines[-lines:]
        content = "".join(tail).strip() or t("log_empty")

        return (
            f"{t('log_title', shown=min(lines, len(all_lines)), total=len(all_lines))}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"```\n{content}\n```"
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error reading log file")
        return t("log_error", err=str(exc))


def get_log_file_path() -> Path:
    return LOG_FILE
