import logging
import math
from pathlib import Path
from typing import Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import config.config as cfg
from utils.executor import run_command
from utils.i18n import t

logger = logging.getLogger(__name__)

# Các thư mục không hiển thị mặc định khi /ls
_IGNORE_LS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".next", "dist", "build"}

# Kích thước phân trang (số dòng mỗi trang)
LINES_PER_PAGE = 50

# Cache lưu trữ ánh xạ giữa ID ngắn và đường dẫn file thực tế để tránh giới hạn 64-byte callback_data
_file_cache: dict[str, str] = {}
_cache_counter = 0


def _register_file(rel_path: str) -> str:
    """Đăng ký file vào cache và trả về ID ngắn (ví dụ: f1, f2)."""
    global _cache_counter
    # Tìm xem file đã được đăng ký chưa
    for file_id, path in _file_cache.items():
        if path == rel_path:
            return file_id
            
    _cache_counter += 1
    file_id = f"f{_cache_counter}"
    _file_cache[file_id] = rel_path
    return file_id


def get_file_from_cache(file_id: str) -> Optional[str]:
    """Lấy đường dẫn file từ ID ngắn."""
    return _file_cache.get(file_id)


def list_files(subpath: str = "") -> str:
    """Liệt kê các file/folder trong một subpath của PROJECT_PATH."""
    project_path = cfg.get_active_project_path()
    target_dir = (project_path / subpath).resolve()

    if not str(target_dir).startswith(str(project_path.resolve())):
        return "⚠️ *Explorer* — Không thể truy cập thư mục ngoài dự án\\."

    if not target_dir.exists():
        return f"⚠️ *Explorer* — Thư mục `{subpath}` không tồn tại\\."

    if not target_dir.is_dir():
        return f"⚠️ *Explorer* — `{subpath}` không phải là một thư mục\\."

    try:
        entries = sorted(target_dir.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
        folders = []
        files = []
        
        for entry in entries:
            if entry.name in _IGNORE_LS or entry.name.startswith("."):
                continue
            if entry.is_dir():
                folders.append(f"📁 `{entry.name}/`")
            else:
                size_kb = entry.stat().st_size / 1024
                files.append(f"📄 `{entry.name}` _({size_kb:.1f} KB)_")

        rel_path = target_dir.relative_to(project_path)
        rel_str = f"📁 *Explorer — {rel_path}*" if str(rel_path) != "." else "📁 *Explorer — Root*"
        
        lines = [rel_str, "━━━━━━━━━━━━━━━━━━━━", ""]
        if folders:
            lines.append("*Thư mục:*")
            lines.extend(folders)
            lines.append("")
        if files:
            lines.append("*Files:*")
            lines.extend(files)

        if not folders and not files:
            lines.append("_(Thư mục trống hoặc chỉ chứa file ẩn)_")

        return "\n".join(lines)
    except Exception as exc:
        logger.exception("Lỗi khi list files")
        return f"❌ Lỗi: {exc}"


def read_file_paged(filepath_str: str, page: int = 1) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """
    Đọc và phân trang nội dung file code kèm số dòng và Inline Keyboard.
    
    Args:
        filepath_str: Đường dẫn tương đối của file
        page: Số trang cần đọc (1-indexed)
        
    Returns:
        Tuple: (Nội dung trang Markdown, Bàn phím lật trang nếu có nhiều trang)
    """
    project_path = cfg.get_active_project_path()
    target_file = (project_path / filepath_str).resolve()

    if not str(target_file).startswith(str(project_path.resolve())):
        return "⚠️ *Explorer* — Không thể đọc file ngoài dự án\\.", None

    if not target_file.exists():
        return f"⚠️ *Explorer* — File `{filepath_str}` không tồn tại\\.", None

    if not target_file.is_file():
        return f"⚠️ *Explorer* — `{filepath_str}` không phải file\\.", None

    try:
        size_kb = target_file.stat().st_size / 1024
        if size_kb > 600:
            return f"⚠️ *Explorer* — File quá lớn (`{size_kb:.1f} KB`). Không hỗ trợ đọc file > 600 KB.", None

        # Đọc tất cả các dòng
        with target_file.open("r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        total_lines = len(all_lines)
        if total_lines == 0:
            return f"📄 *Explorer — {target_file.name}* (Rỗng)\n━━━━━━━━━━━━━━━━━━━━\n_(File không có nội dung)_", None

        # Tính tổng số trang
        total_pages = math.ceil(total_lines / LINES_PER_PAGE)
        
        # Đảm bảo số trang hợp lệ
        page = max(1, min(page, total_pages))
        
        # Trích xuất các dòng của trang hiện tại
        start_idx = (page - 1) * LINES_PER_PAGE
        end_idx = min(start_idx + LINES_PER_PAGE, total_lines)
        page_lines = all_lines[start_idx:end_idx]

        # Thêm số dòng vào đầu mỗi dòng code
        formatted_lines = []
        for idx, line in enumerate(page_lines, start=start_idx + 1):
            # Giữ nguyên cấu trúc thụt lề
            formatted_lines.append(f"{idx:3d} | {line.rstrip()}")

        content_block = "\n".join(formatted_lines)
        ext = target_file.suffix.lstrip(".")

        # Tạo tiêu đề trang
        header = (
            f"📄 *Explorer — {target_file.name}* _({size_kb:.1f} KB)_\n"
            f"📖 Trang `{page}/{total_pages}` _(Dòng {start_idx + 1}-{end_idx} trên {total_lines})_\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"```{ext}\n"
            f"{content_block}\n"
            f"```"
        )

        # Tạo nút bấm lật trang nếu có từ 2 trang trở lên
        reply_markup = None
        if total_pages > 1:
            file_id = _register_file(filepath_str)
            buttons = []
            
            # Nút Trang trước
            if page > 1:
                buttons.append(InlineKeyboardButton("◀ Trang trước", callback_data=f"catpage_{file_id}_{page - 1}"))
            
            # Nút Trang sau
            if page < total_pages:
                buttons.append(InlineKeyboardButton("Trang sau ▶", callback_data=f"catpage_{file_id}_{page + 1}"))
                
            reply_markup = InlineKeyboardMarkup([buttons])

        return header, reply_markup
    except Exception as exc:
        logger.exception("Lỗi khi đọc file phân trang")
        return f"❌ Lỗi: {exc}", None


async def execute_arbitrary(cmd_str: str) -> str:
    """Chạy lệnh shell tùy ý trong PROJECT_PATH."""
    project_path = cfg.get_active_project_path()
    logger.info("Chạy lệnh tự do: %s in %s", cmd_str, project_path)
    
    result = await run_command(
        cmd_str,
        cwd=project_path,
        timeout=cfg.DEFAULT_TIMEOUT,
        shell=True,
    )

    status = "✅ Success" if result.success else "❌ Failed"
    if result.timed_out:
        status = "⏱️ Timed out"
    elif result.exception:
        status = f"💥 {result.exception}"

    output = result.output or "(no output)"

    return (
        f"💻 *Terminal Exec*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💻 Lệnh: `{cmd_str}`\n"
        f"Status: {status}\n\n"
        f"```\n{output}\n```"
    )
