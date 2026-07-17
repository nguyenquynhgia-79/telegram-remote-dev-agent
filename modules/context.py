"""
modules/context.py
==================
Quản lý GEMINI.md — file context dài hạn cho AI.

Lệnh:
  /context        — Xem nội dung GEMINI.md hiện tại
  /context update — Tự động cập nhật GEMINI.md từ project
  /context edit   — Hướng dẫn chỉnh sửa thủ công

Module này quét project và sinh ra context thông minh:
- Cấu trúc thư mục (bỏ qua node_modules, .git, venv...)
- Tech stack tự động detect từ package.json, requirements.txt, pom.xml...
- Git log 10 commit gần nhất
- Danh sách file quan trọng
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import config.config as cfg
from utils.executor import run_command

logger = logging.getLogger(__name__)


def _get_gemini_md_path() -> Path:
    """Trả về đường dẫn file GEMINI.md của dự án đang hoạt động."""
    return cfg.get_active_project_path() / "GEMINI.md"


# Thư mục bỏ qua khi quét
_SKIP_DIRS = {
    "node_modules", ".git", "venv", ".venv", "env",
    "__pycache__", ".next", "dist", "build", "target",
    ".gradle", ".idea", ".vscode", "coverage", ".pytest_cache",
    "vendor", "Pods", ".terraform",
}

def _detect_node(path: Path) -> list[str]:
    """Đọc package.json và trích xuất framework."""
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        techs = ["Node.js"]
        if "react" in deps:      techs.append("React")
        if "next" in deps:       techs.append("Next.js")
        if "vue" in deps:        techs.append("Vue.js")
        if "express" in deps:    techs.append("Express")
        if "fastify" in deps:    techs.append("Fastify")
        if "nestjs" in deps or "@nestjs/core" in deps: techs.append("NestJS")
        if "typescript" in deps: techs.append("TypeScript")
        if "tailwindcss" in deps: techs.append("Tailwind CSS")
        if "prisma" in deps:     techs.append("Prisma")
        if "mongoose" in deps:   techs.append("MongoDB/Mongoose")
        if "sequelize" in deps:  techs.append("Sequelize")
        if "pg" in deps:         techs.append("PostgreSQL")
        if "mysql2" in deps:     techs.append("MySQL")
        return techs
    except Exception:
        return ["Node.js"]


def _detect_python_req(path: Path) -> list[str]:
    """Đọc requirements.txt."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace").lower()
        techs = ["Python"]
        if "django"    in content: techs.append("Django")
        if "flask"     in content: techs.append("Flask")
        if "fastapi"   in content: techs.append("FastAPI")
        if "sqlalchemy" in content: techs.append("SQLAlchemy")
        if "pandas"    in content: techs.append("Pandas")
        if "numpy"     in content: techs.append("NumPy")
        if "torch"     in content: techs.append("PyTorch")
        if "tensorflow" in content: techs.append("TensorFlow")
        return techs
    except Exception:
        return ["Python"]


def _detect_python_pyproject(path: Path) -> list[str]:
    """Đọc pyproject.toml."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace").lower()
        techs = ["Python"]
        for fw in ["django", "flask", "fastapi", "poetry"]:
            if fw in content:
                techs.append(fw.capitalize())
        return techs
    except Exception:
        return ["Python"]


def _detect_java_maven(path: Path) -> list[str]:
    """Đọc pom.xml."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace").lower()
        techs = ["Java", "Maven"]
        if "spring-boot" in content: techs.append("Spring Boot")
        if "spring-web"  in content: techs.append("Spring Web")
        if "hibernate"   in content: techs.append("Hibernate")
        return techs
    except Exception:
        return ["Java", "Maven"]


# File tech stack cần detect
_TECH_FILES = {
    "package.json":        _detect_node,
    "requirements.txt":    _detect_python_req,
    "pyproject.toml":      _detect_python_pyproject,
    "pom.xml":             _detect_java_maven,
    "build.gradle":        lambda p: ["Java/Kotlin", "Gradle"],
    "go.mod":              lambda p: ["Go"],
    "Cargo.toml":          lambda p: ["Rust"],
    "composer.json":       lambda p: ["PHP"],
    "Gemfile":             lambda p: ["Ruby"],
    "docker-compose.yml":  lambda p: ["Docker Compose"],
    "docker-compose.yaml": lambda p: ["Docker Compose"],
    "Dockerfile":          lambda p: ["Docker"],
    ".env.example":        lambda p: [],  # Không phải tech nhưng mark project
}


def _build_tree(root: Path, prefix: str = "", max_depth: int = 4, _depth: int = 0) -> list[str]:
    """
    Sinh cây thư mục đệ quy, bỏ qua các thư mục không quan trọng.

    Args:
        root:      Thư mục gốc.
        prefix:    Tiền tố cho hiển thị.
        max_depth: Độ sâu tối đa.
        _depth:    Độ sâu hiện tại (internal).

    Returns:
        List các dòng text biểu diễn cây.
    """
    if _depth > max_depth:
        return []

    lines = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return []

    entries = [e for e in entries if e.name not in _SKIP_DIRS and not e.name.startswith(".")]
    # Giới hạn hiển thị tối đa 20 entries mỗi thư mục
    show = entries[:20]
    hidden = len(entries) - len(show)

    for i, entry in enumerate(show):
        is_last = (i == len(show) - 1) and hidden == 0
        connector = "└── " if is_last else "├── "
        extension = "│   " if not is_last else "    "

        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            sub = _build_tree(entry, prefix + extension, max_depth, _depth + 1)
            lines.extend(sub)
        else:
            size = entry.stat().st_size
            size_str = f" ({size/1024:.1f}KB)" if size > 10240 else ""
            lines.append(f"{prefix}{connector}{entry.name}{size_str}")

    if hidden > 0:
        lines.append(f"{prefix}└── ... ({hidden} mục khác)")

    return lines


def _detect_tech_stack() -> list[str]:
    """Tự động detect tech stack từ các file marker."""
    techs: list[str] = []
    seen: set[str] = set()
    project_path = cfg.get_active_project_path()

    for filename, detector in _TECH_FILES.items():
        filepath = project_path / filename
        if filepath.exists():
            try:
                found = detector(filepath)
                for tech in found:
                    if tech not in seen:
                        seen.add(tech)
                        techs.append(tech)
            except Exception:
                pass

    return techs if techs else ["(Chưa detect được — hãy thêm thủ công)"]


def _count_project_stats() -> dict[str, int]:
    """Đếm số file theo loại trong project."""
    counts: dict[str, int] = {}
    project_path = cfg.get_active_project_path()
    try:
        for f in project_path.rglob("*"):
            if f.is_file() and not any(skip in f.parts for skip in _SKIP_DIRS):
                ext = f.suffix.lower() or "(no ext)"
                counts[ext] = counts.get(ext, 0) + 1
    except Exception:
        pass
    # Sắp xếp theo số lượng giảm dần, lấy top 10
    return dict(sorted(counts.items(), key=lambda x: -x[1])[:10])


async def _get_recent_commits(n: int = 15) -> str:
    """Lấy N commit gần nhất từ git log."""
    project_path = cfg.get_active_project_path()
    result = await run_command(
        ["git", "log", f"-{n}", "--oneline", "--decorate", "--color=never"],
        cwd=project_path,
        timeout=15,
    )
    if result.success and result.stdout.strip():
        return result.stdout.strip()
    return "(chưa có commit hoặc không phải git repo)"


async def _get_git_branches() -> str:
    """Lấy danh sách branches."""
    project_path = cfg.get_active_project_path()
    result = await run_command(
        ["git", "branch", "-a", "--color=never"],
        cwd=project_path,
        timeout=10,
    )
    if result.success and result.stdout.strip():
        return result.stdout.strip()
    return "(không có branch)"


async def generate_context() -> str:
    """
    Tự động sinh nội dung GEMINI.md từ trạng thái project hiện tại.

    Returns:
        Nội dung markdown đầy đủ.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    project_path = cfg.get_active_project_path()
    project_name = project_path.name

    # Thu thập dữ liệu song song
    commits = await _get_recent_commits()
    branches = await _get_git_branches()
    tech_stack = _detect_tech_stack()
    file_stats = _count_project_stats()

    # Cây thư mục
    tree_lines = _build_tree(project_path, max_depth=cfg.CONTEXT_TREE_DEPTH)
    tree_str = "\n".join(tree_lines) if tree_lines else "(thư mục trống)"

    # Thống kê file
    stats_lines = [f"  - `{ext}`: {count} file" for ext, count in file_stats.items()]
    stats_str = "\n".join(stats_lines) if stats_lines else "  - (không có dữ liệu)"

    # Tech stack
    tech_str = "\n".join(f"- {t}" for t in tech_stack)

    content = f"""# Project Context — {project_name}
> Auto-generated bởi Telegram Remote Dev Agent lúc {now}
> Chỉnh sửa file này để cập nhật thông tin dự án cho AI.

---

## Mô tả dự án
<!-- TODO: Mô tả ngắn gọn mục đích và tính năng chính -->
Dự án **{project_name}** tại `{project_path}`.

---

## Tech Stack (auto-detected)
{tech_str}

---

## Thống kê file
{stats_str}

---

## Cấu trúc thư mục
```
{project_name}/
{tree_str}
```

---

## Git — Branches
```
{branches}
```

---

## Git — 15 commit gần nhất
```
{commits}
```

---

## Ghi chú quan trọng
<!-- TODO: Thêm các quy ước, kiến trúc, hoặc lỗi đã biết -->

### Quy ước code
- <!-- Ví dụ: Dùng async/await, không dùng callback -->
- <!-- Ví dụ: Tên hàm camelCase, tên file kebab-case -->

### Kiến trúc đặc biệt
- <!-- Ví dụ: Auth dùng JWT, token expire 24h -->
- <!-- Ví dụ: Queue xử lý bằng Bull -->

### Lỗi / Hạn chế đã biết
- <!-- Ví dụ: Module X chưa xử lý edge case Y -->

---
*Cập nhật bằng lệnh `/context update` trên Telegram bot*
"""
    return content


async def update_context() -> str:
    """
    Sinh context mới và ghi vào GEMINI.md.

    Returns:
        Thông báo kết quả.
    """
    gemini_md = _get_gemini_md_path()
    try:
        content = await generate_context()
        gemini_md.write_text(content, encoding="utf-8")

        file_size = len(content.encode("utf-8"))
        return (
            f"✅ *GEMINI.md đã cập nhật*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📁 `{gemini_md}`\n"
            f"📊 Kích thước: `{file_size / 1024:.1f} KB`\n\n"
            f"AI sẽ đọc file này mỗi lần bạn dùng `/ask`\\.\n"
            f"Hãy thêm thủ công vào phần *Ghi chú quan trọng* để AI hiểu sâu hơn\\."
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Lỗi khi cập nhật GEMINI.md")
        return f"❌ Lỗi khi cập nhật context: {exc}"


def read_context() -> str:
    """
    Đọc và trả về nội dung GEMINI.md hiện tại.

    Returns:
        Nội dung đã format để gửi qua Telegram.
    """
    gemini_md = _get_gemini_md_path()
    if not gemini_md.exists():
        return (
            f"📄 *GEMINI.md*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ Chưa có file context tại `{gemini_md}`\n\n"
            f"Chạy `/context update` để tự động tạo\\."
        )

    content = gemini_md.read_text(encoding="utf-8", errors="replace")
    size_kb = len(content.encode("utf-8")) / 1024

    return (
        f"📄 *GEMINI.md* (`{size_kb:.1f} KB`)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"```\n{content[:3000]}\n```"
        + ("\n\n_(file bị cắt ngắn — dùng `/log` để xem đầy đủ)_" if len(content) > 3000 else "")
    )
