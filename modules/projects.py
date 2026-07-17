"""
modules/projects.py
===================
Quản lý danh sách các dự án (multi-project management).

Cung cấp:
- Lấy danh sách các thư mục con trong BASE_PATH.
- Tạo Inline Keyboard để chọn dự án đang làm việc.
- Chuyển đổi dự án hiện tại và nạp cấu hình tương ứng.
"""

import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import config.config as cfg

logger = logging.getLogger(__name__)


def get_project_list() -> list[str]:
    """Trả về danh sách tên các thư mục con trong BASE_PATH (mỗi thư mục con là một project)."""
    if not cfg.BASE_PATH.exists() or not cfg.BASE_PATH.is_dir():
        logger.error("BASE_PATH không tồn tại hoặc không phải thư mục: %s", cfg.BASE_PATH)
        return []
        
    try:
        projects = []
        for path in cfg.BASE_PATH.iterdir():
            # Chỉ coi các thư mục không ẩn, không phải node_modules/venv là project
            if path.is_dir() and not path.name.startswith(".") and path.name not in ("node_modules", "venv", ".venv", "logs", "config"):
                projects.append(path.name)
        return sorted(projects, key=lambda x: x.name.lower() if hasattr(x, 'name') else str(x).lower())
    except Exception as exc:
        logger.exception("Lỗi khi quét danh sách dự án")
        return []


def build_projects_keyboard() -> InlineKeyboardMarkup:
    """Tạo bàn phím Inline chứa danh sách dự án kèm dấu tick cho dự án đang hoạt động."""
    projects = get_project_list()
    active_project = cfg.get_active_project_name()

    buttons = []
    # Bố trí mỗi hàng 2 nút bấm
    row = []
    for proj in projects:
        # Gắn icon check nếu đang là dự án active
        is_active = (proj == active_project)
        label = f"✨ {proj} (Active)" if is_active else proj
        
        row.append(InlineKeyboardButton(label, callback_data=f"selectproj_{proj}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
            
    if row:
        buttons.append(row)

    # Thêm nút hủy chọn (Quay về thư mục gốc)
    if active_project:
        buttons.append([InlineKeyboardButton("❌ Bỏ chọn (Quay về Root)", callback_data="selectproj_clear")])

    return InlineKeyboardMarkup(buttons)


def select_project(project_name: str) -> str:
    """Kích hoạt dự án mới."""
    if project_name == "clear":
        if cfg.set_active_project_name(""):
            return "📁 *Hệ thống* — Đã quay về chế độ thư mục gốc (Root)\\. Một số tính năng Docker/Build có thể tạm khóa\\."
        return "❌ Lỗi khi quay về thư mục gốc\\."
        
    if cfg.set_active_project_name(project_name):
        proj_path = cfg.get_active_project_path()
        
        # Tự động quét xem dự án mới có docker và build command gì
        has_docker = "Có (docker-compose.yml)" if cfg.get_active_docker_compose_path() else "Không"
        build_cmd = cfg.get_active_build_command()
        
        return (
            f"✅ *Đã chuyển dự án làm việc* ✅\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📂 Dự án: *{project_name}*\n"
            f"📁 Đường dẫn: `{proj_path}`\n"
            f"🐳 Docker Compose: `{has_docker}`\n"
            f"🔨 Lệnh Build: `{build_cmd}`\n\n"
            f"ℹ️ _AI và các lệnh Git, Build, Docker từ bây giờ sẽ chạy bên trong thư mục này\\._"
        )
    else:
        return f"❌ Không thể kích hoạt dự án `{project_name}`\\. Vui lòng kiểm tra lại thư mục có tồn tại không\\."
