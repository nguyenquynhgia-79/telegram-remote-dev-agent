"""
modules/system.py
=================
System information module.
Provides: /status, /ping, /ip
"""

import logging
import platform
import socket
import time
import urllib.request
from datetime import timedelta
from typing import Optional

import psutil

import config.config as cfg
from utils.i18n import t

logger = logging.getLogger(__name__)

_START_TIME = time.time()


def get_status() -> str:
    """Return a formatted Markdown string with CPU, RAM, Disk, Uptime, Hostname."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=True)

        ram = psutil.virtual_memory()
        ram_used_gb = ram.used / (1024 ** 3)
        ram_total_gb = ram.total / (1024 ** 3)
        ram_percent = ram.percent

        disk = psutil.disk_usage("/")
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)
        disk_percent = disk.percent

        uptime_seconds = int(time.time() - _START_TIME)
        uptime_str = str(timedelta(seconds=uptime_seconds))
        hostname = socket.gethostname()
        os_info = f"{platform.system()} {platform.release()}"
        
        project_name = cfg.get_active_project_name() or "(Thư mục gốc / Root)"
        project_path = cfg.get_active_project_path()

        return (
            f"{t('status_title')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📂 *Dự án:* `{project_name}`\n"
            f"📁 *Đường dẫn:* `{project_path}`\n"
            f"🏠 *Máy chủ:* `{hostname}`\n"
            f"💻 *Hệ điều hành:* `{os_info}`\n"
            f"⏱️ *Uptime Agent:* `{uptime_str}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{t('status_cpu')} `{cpu_percent}%` ({cpu_count} cores)\n"
            f"{t('status_ram')} `{ram_used_gb:.1f} / {ram_total_gb:.1f} GB` ({ram_percent}%)\n"
            f"{t('status_disk')} `{disk_used_gb:.1f} / {disk_total_gb:.1f} GB` ({disk_percent}%)\n"
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error collecting system status")
        return t("status_error", err=str(exc))


def get_ping() -> str:
    """Return a pong response."""
    return t("ping_response")


def get_ip() -> str:
    """Return local and public IP addresses."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip: str = s.getsockname()[0]
    except Exception:  # noqa: BLE001
        local_ip = "Unknown"

    public_ip: Optional[str] = None
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            public_ip = resp.read().decode("utf-8").strip()
    except Exception:  # noqa: BLE001
        public_ip = t("ip_unavailable")

    return (
        f"{t('ip_title')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{t('ip_local')} `{local_ip}`\n"
        f"{t('ip_public')} `{public_ip}`\n"
    )
