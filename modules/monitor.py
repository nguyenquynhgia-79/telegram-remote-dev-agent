"""
modules/monitor.py
==================
Hệ thống giám sát nền tự động gửi thông báo đẩy (Push Notifications) qua Telegram.

Các cảnh báo hỗ trợ:
- CPU quá tải (> 90%)
- RAM sắp cạn (> 90%)
- Ổ đĩa sắp hết (> 92%)
- Chống spam: Cooldown 30 phút cho mỗi loại cảnh báo.
"""

import asyncio
import logging
import time

import psutil
from telegram.ext import Application

from config.config import ALLOWED_CHAT_ID

logger = logging.getLogger(__name__)

# Ngưỡng cảnh báo (%)
CPU_THRESHOLD = 85.0
RAM_THRESHOLD = 90.0
DISK_THRESHOLD = 92.0

# Thời gian cooldown giữa các cảnh báo cùng loại (giây) - 30 phút
COOLDOWN_TIME = 1800

# Trạng thái thời gian gửi cảnh báo cuối cùng
_last_alerts = {
    "cpu": 0.0,
    "ram": 0.0,
    "disk": 0.0
}


async def _check_and_alert(app: Application) -> None:
    """Kiểm tra tài nguyên và gửi thông báo nếu vượt ngưỡng."""
    now = time.time()
    
    # 1. Kiểm tra CPU
    cpu = psutil.cpu_percent(interval=0.5)
    if cpu > CPU_THRESHOLD:
        if now - _last_alerts["cpu"] > COOLDOWN_TIME:
            msg = f"🔥 *CẢNH BÁO HỆ THỐNG* 🔥\n━━━━━━━━━━━━━━━━━━━━\n🖥️ *CPU đang quá tải:* `{cpu}%`\nHãy kiểm tra xem có tiến trình nào đang chạy ngầm bị treo không\\."
            try:
                await app.bot.send_message(chat_id=ALLOWED_CHAT_ID, text=msg, parse_mode="MarkdownV2")
                _last_alerts["cpu"] = now
                logger.warning("Đã gửi cảnh báo đẩy: CPU quá tải (%s%%)", cpu)
            except Exception as exc:
                logger.error("Không gửi được cảnh báo đẩy CPU: %s", exc)

    # 2. Kiểm tra RAM
    ram = psutil.virtual_memory().percent
    if ram > RAM_THRESHOLD:
        if now - _last_alerts["ram"] > COOLDOWN_TIME:
            msg = f"🔥 *CẢNH BÁO HỆ THỐNG* 🔥\n━━━━━━━━━━━━━━━━━━━━\n🧠 *RAM đang cạn kiệt:* `{ram}%`\nHệ thống có thể bị đơ hoặc chậm\\."
            try:
                await app.bot.send_message(chat_id=ALLOWED_CHAT_ID, text=msg, parse_mode="MarkdownV2")
                _last_alerts["ram"] = now
                logger.warning("Đã gửi cảnh báo đẩy: RAM cạn kiệt (%s%%)", ram)
            except Exception as exc:
                logger.error("Không gửi được cảnh báo đẩy RAM: %s", exc)

    # 3. Kiểm tra Disk
    disk = psutil.disk_usage("/").percent
    if disk > DISK_THRESHOLD:
        if now - _last_alerts["disk"] > COOLDOWN_TIME:
            msg = f"🔥 *CẢNH BÁO HỆ THỐNG* 🔥\n━━━━━━━━━━━━━━━━━━━━\n💾 *Ổ đĩa hệ thống gần đầy:* `{disk}%`\nVui lòng dọn dẹp để tránh lỗi hệ thống\\."
            try:
                await app.bot.send_message(chat_id=ALLOWED_CHAT_ID, text=msg, parse_mode="MarkdownV2")
                _last_alerts["disk"] = now
                logger.warning("Đã gửi cảnh báo đẩy: Ổ đĩa gần đầy (%s%%)", disk)
            except Exception as exc:
                logger.error("Không gửi được cảnh báo đẩy Disk: %s", exc)


async def start_monitor_loop(app: Application) -> None:
    """Vòng lặp giám sát nền chạy ngầm vô hạn."""
    logger.info("Khởi động luồng giám sát tài nguyên nền (mỗi 5 phút)")
    
    # Đợi bot kết nối hoàn toàn
    await asyncio.sleep(10)
    
    while True:
        try:
            await _check_and_alert(app)
        except Exception as exc:
            logger.error("Lỗi trong vòng lặp giám sát: %s", exc)
        
        # Chạy kiểm tra mỗi 30 giây
        await asyncio.sleep(30)
