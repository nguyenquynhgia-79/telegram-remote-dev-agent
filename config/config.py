"""
config/config.py
================
Central configuration module.
Reads all settings from environment variables (.env file).
No hardcoded values allowed.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level up from this file)
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)  # override=True: đảm bảo .env ghi đè os.environ


def _require(key: str) -> str:
    """Read a required environment variable; raise if missing."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Please configure your .env file."
        )
    return value.strip()


def _optional(key: str, default: str = "") -> str:
    """Read an optional environment variable with a default."""
    return (os.getenv(key) or default).strip()


import json

# ── Telegram ──────────────────────────────────────────────────
BOT_TOKEN: str = _require("BOT_TOKEN")

_USERS_FILE = Path(__file__).parent.parent / "config" / "users.json"

def get_users() -> dict:
    """Read users from users.json. If it doesn't exist, create it with ALLOWED_CHAT_ID from .env as admin."""
    if _USERS_FILE.exists():
        try:
            return json.loads(_USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    # Fallback and initialization
    try:
        legacy_id = int(_require("ALLOWED_CHAT_ID"))
    except Exception:
        legacy_id = 0
        
    default_users = {
        "admins": [legacy_id] if legacy_id else [],
        "viewers": []
    }
    
    try:
        _USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _USERS_FILE.write_text(json.dumps(default_users, indent=4), encoding="utf-8")
    except Exception:
        pass
        
    return default_users

def get_user_role(chat_id: int) -> str:
    """Return 'admin', 'viewer', or None based on chat_id."""
    users = get_users()
    if chat_id in users.get("admins", []):
        return "admin"
    if chat_id in users.get("viewers", []):
        return "viewer"
    return None

# Keep legacy for compatibility in other modules until fully migrated, but mark as deprecated mentally
ALLOWED_CHAT_ID: int = int(_optional("ALLOWED_CHAT_ID", "0"))

# ── Base Directory ────────────────────────────────────────────
# Thư mục gốc chứa nhiều dự án (Ví dụ: D:\ADMIN)
BASE_PATH: Path = Path(_optional("PROJECT_PATH", "."))

# ── Logging ───────────────────────────────────────────────────
LOGS_DIR: Path = Path(__file__).parent.parent / "logs"
LOG_FILE: Path = LOGS_DIR / "agent.log"

# ── Telegram limits ───────────────────────────────────────────
MAX_MESSAGE_LENGTH: int = 4000   # Telegram cap is 4096; we use 4000 for safety

# ── Executor defaults ─────────────────────────────────────────
DEFAULT_TIMEOUT: int = 300       # 5 minutes for long tasks
AI_TIMEOUT: int = 600            # 10 minutes for AI tasks

# ── Memory / Context Tuning ───────────────────────────────────
MEMORY_CONTEXT_N: int = int(_optional("MEMORY_CONTEXT_N", "5"))
MEMORY_MAX_ENTRIES: int = int(_optional("MEMORY_MAX_ENTRIES", "100"))
CONTEXT_TREE_DEPTH: int = int(_optional("CONTEXT_TREE_DEPTH", "2"))

# ── File lưu trạng thái project đang được chọn ─────────────────
_ACTIVE_PROJECT_FILE = Path(__file__).parent.parent / "config" / "active_project.json"


def get_active_project_name() -> str:
    """Lấy tên thư mục dự án đang làm việc."""
    try:
        if _ACTIVE_PROJECT_FILE.exists():
            data = json.loads(_ACTIVE_PROJECT_FILE.read_text(encoding="utf-8"))
            name = data.get("active_project", "")
            if name:
                # Kiểm tra xem thư mục đó có thực sự tồn tại trong BASE_PATH không
                if (BASE_PATH / name).is_dir():
                    return name
    except Exception:
        pass
    return ""


def set_active_project_name(name: str) -> bool:
    """Lưu dự án làm việc mới."""
    if not name:
        try:
            if _ACTIVE_PROJECT_FILE.exists():
                _ACTIVE_PROJECT_FILE.unlink()
            return True
        except Exception:
            return False
            
    target_path = BASE_PATH / name
    if not target_path.is_dir():
        return False
        
    try:
        _ACTIVE_PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ACTIVE_PROJECT_FILE.write_text(json.dumps({"active_project": name}), encoding="utf-8")
        return True
    except Exception:
        return False


def get_active_project_path() -> Path:
    """Trả về đường dẫn tuyệt đối của dự án đang hoạt động."""
    name = get_active_project_name()
    if name:
        return (BASE_PATH / name).resolve()
    return BASE_PATH.resolve()  # Fallback về thư mục gốc nếu chưa chọn project


def get_project_env_value(key: str, default: str = "") -> str:
    """
    Nạp cấu hình từ file .env riêng của dự án đang hoạt động (nếu có).
    Nếu không có, fallback về cấu hình global của bot.
    """
    project_path = get_active_project_path()
    project_env = project_path / ".env"
    
    if project_env.exists():
        try:
            # Đọc thủ công để tránh ghi đè các biến toàn cục của bot
            for line in project_env.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == key:
                        return v.strip().strip('"\'')
        except Exception:
            pass
            
    # Fallback về cấu hình toàn cục trong bot
    return _optional(key, default)


def get_active_build_command() -> str:
    """Lấy lệnh build tương ứng cho dự án hiện tại."""
    return get_project_env_value("BUILD_COMMAND", "npm run build")


def get_active_ai_command() -> str:
    """Lấy lệnh AI tương ứng cho dự án hiện tại."""
    return get_project_env_value("AI_COMMAND", "gemini.cmd --model gemini-3.5-flash --skip-trust")


def get_active_docker_compose_path() -> Path | None:
    """
    Tự động phát hiện docker-compose.yml trong thư mục dự án.
    Không cần cấu hình cứng.
    """
    project_path = get_active_project_path()
    if project_path == BASE_PATH.resolve():
        return None  # Đang ở thư mục gốc, không chạy docker
        
    for name in ("docker-compose.yml", "docker-compose.yaml"):
        compose_file = project_path / name
        if compose_file.exists():
            return compose_file
            
    return None


def validate() -> None:
    """Kiểm tra thư mục gốc."""
    if not BASE_PATH.exists():
        import warnings
        warnings.warn(
            f"BASE_PATH '{BASE_PATH}' does not exist. "
            "Please check the PROJECT_PATH variable in your .env file.",
            stacklevel=2,
        )
