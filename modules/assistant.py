"""
modules/assistant.py
====================
Trợ lý chủ động (/troly) cho Telegram Bot.

Nhiệm vụ:
- Chào hỏi thân thiện theo thời gian (Sáng/Trưa/Chiều/Tối).
- Quét nhanh tình trạng dự án: Git branch, số file thay đổi chưa commit, tình trạng Docker, tài nguyên hệ thống.
- Chủ động đưa ra 3 gợi ý hành động cụ thể cho lập trình viên thay vì đợi lệnh.
"""

import datetime
import logging
from pathlib import Path

import psutil

import datetime
import logging
from pathlib import Path

import psutil

import config.config as cfg
from utils.executor import run_command
from utils.i18n import t

logger = logging.getLogger(__name__)


def _get_greeting() -> str:
    """Trả về lời chào phù hợp với giờ hiện tại."""
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "🌅 Chào buổi sáng! Hy vọng bạn có một ngày làm việc tràn đầy năng lượng."
    elif 12 <= hour < 18:
        return "☀️ Chào buổi chiều! Công việc hôm nay thế nào rồi?"
    elif 18 <= hour < 22:
        return "🌌 Chào buổi tối! Bạn vẫn đang code chứ?"
    else:
        return "🦉 Đã khuya rồi, chúc bạn code vui vẻ hoặc ngủ ngon nhé!"


async def _get_git_summary() -> dict:
    """Lấy tóm tắt nhanh về Git status."""
    summary = {"branch": "unknown", "dirty_files": 0, "last_commit": "None"}
    project_path = cfg.get_active_project_path()
    
    # Nếu chưa chọn dự án con (đang ở Root), bỏ qua git status dự án
    if project_path == cfg.BASE_PATH.resolve():
        return summary

    try:
        # Branch
        res_branch = await run_command(["git", "branch", "--show-current"], cwd=project_path, timeout=5)
        if res_branch.success:
            summary["branch"] = res_branch.stdout.strip()

        # Dirty files
        res_status = await run_command(["git", "status", "--porcelain"], cwd=project_path, timeout=5)
        if res_status.success:
            summary["dirty_files"] = len(res_status.stdout.splitlines())

        # Last commit
        res_log = await run_command(["git", "log", "-1", "--oneline"], cwd=project_path, timeout=5)
        if res_log.success:
            summary["last_commit"] = res_log.stdout.strip()
    except Exception:
        pass
    return summary


async def _get_docker_summary() -> str:
    """Lấy tóm tắt về Docker containers."""
    try:
        res = await run_command(["docker", "ps", "-q"], timeout=5)
        if res.success:
            count = len(res.stdout.splitlines())
            return f"🐳 `{count}` container đang chạy"
    except Exception:
        pass
    return "🐳 Docker không chạy hoặc lỗi"


def _get_system_warnings() -> list[str]:
    """Phát hiện các cảnh báo tài nguyên hệ thống."""
    warnings = []
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent

    if cpu > 80:
        warnings.append(f"⚠️ CPU đang cao: `{cpu}%`")
    if ram > 85:
        warnings.append(f"⚠️ RAM sắp hết: `{ram}%`")
    if disk > 90:
        warnings.append(f"⚠️ Ổ đĩa sắp đầy: `{disk}%`")
    return warnings


async def generate_assistant_report() -> str:
    """
    Sinh báo cáo trợ lý chủ động.
    
    Returns:
        Markdown string.
    """
    greeting = _get_greeting()
    git_info = await _get_git_summary()
    docker_info = await _get_docker_summary()
    sys_warnings = _get_system_warnings()

    project_name = cfg.get_active_project_name()
    project_path = cfg.get_active_project_path()

    # Xây dựng các gợi ý hành động thông minh
    suggestions = []
    
    if not project_name:
        # Nếu chưa chọn dự án con
        project_title = "(Chưa chọn dự án - Đang ở thư mục gốc)"
        suggestions.append("🗂 Bạn chưa chọn dự án làm việc. Hãy gõ lệnh `/projects` hoặc `/p` để kích hoạt một dự án con.")
    else:
        project_title = f"{project_name}"
        
        # - Gợi ý dựa trên Git
        if git_info["dirty_files"] > 0:
            suggestions.append(f"➕ Bạn đang có *{git_info['dirty_files']}* file chưa commit. Hãy dùng `/git status` hoặc `/ask -d \"Review các thay đổi này\"`.")
        else:
            suggestions.append("✅ Git working tree sạch sẽ. Sẵn sàng viết tính năng mới!")

        # - Gợi ý dựa trên Docker
        compose_path = cfg.get_active_docker_compose_path()
        if compose_path and "0 container" in docker_info:
            suggestions.append("🐳 Dự án này hỗ trợ Docker nhưng các container đang tắt. Dùng `/docker up` để khởi chạy.")

        # - Lệnh nhanh
        suggestions.append("🛠️ Bạn có thể gõ `/ls` để xem cấu trúc file hoặc `/projects` để đổi dự án.")

    # Format nội dung
    warnings_str = ""
    if sys_warnings:
        warnings_str = "\n🔥 *CẢNH BÁO HỆ THỐNG:*\n" + "\n".join(sys_warnings) + "\n━━━━━━━━━━━━━━━━━━━━\n"

    suggestions_str = "\n".join([f"{i}. {s}" for i, s in enumerate(suggestions, 1)])

    git_sec = ""
    if project_name:
        git_sec = (
            f"🌳 *Branch hiện tại:* `{git_info['branch']}`\n"
            f"📝 *Commit cuối:* `{git_info['last_commit']}`\n"
        )

    return (
        f"{greeting}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📂 *Dự án:* `{project_title}`\n"
        f"📁 *Đường dẫn:* `{project_path}`\n"
        f"{git_sec}"
        f"{docker_info}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{warnings_str}"
        f"🧠 *GỢI Ý HÀNH ĐỘNG DÀNH CHO BẠN:*\n"
        f"{suggestions_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 _Hôm nay bạn cần tôi giúp gì nào? Hãy chat trực tiếp hoặc dùng /ask nhé!_"
    )
