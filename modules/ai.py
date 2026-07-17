"""
modules/ai.py
=============
AI Coding Agent module.
Invokes the configured AI CLI tool (gemini / claude / codex) with a user prompt.

Tính năng nâng cao: Agentic Reporting & Context Flags
- Quét Git status trước/sau khi chạy AI để phát hiện file thay đổi thực tế.
- Hỗ trợ các flag đính kèm tài nguyên:
    * `-f <file>` : Đính kèm file code bất kỳ
    * `-d`        : Đính kèm git diff hiện tại
    * `-l`        : Đính kèm 50 dòng log gần nhất
"""

import asyncio
import logging
import os
import re
import json
import shlex
from pathlib import Path

import config.config as cfg
from utils.executor import ExecutionResult, run_command
from utils.i18n import t
import modules.memory as memory
import modules.explorer as explorer

logger = logging.getLogger(__name__)

_MAX_OUTPUT_CHARS = 3500

AI_REPORT_SYSTEM_INSTRUCTION = """

[System Instruction: You are an autonomous Agentic AI.
You have the ability to call tools to gather more information, execute actions, and write code.
Before calling a tool, you MUST write down your thought process starting with "THOUGHT: ...".
To call a tool, output a JSON block wrapped in ```json ... ``` with the exact format below.

### AVAILABLE TOOLS ###
1. `run_shell`: Execute a command in the terminal.
```json
{
  "tool_call": "run_shell",
  "command": "<your shell command here>"
}
```

2. `read_file`: Read the contents of a file.
```json
{
  "tool_call": "read_file",
  "path": "<path to file relative to project root>"
}
```

3. `write_file`: Write text to a file (WARNING: Overwrites entire file).
```json
{
  "tool_call": "write_file",
  "path": "<path to file>",
  "content": "<exact content to write>"
}
```

4. `replace_code`: Replace a specific block of text in a file. The `target` must perfectly match the existing text.
```json
{
  "tool_call": "replace_code",
  "path": "<path to file>",
  "target": "<exact string to be replaced>",
  "replacement": "<exact replacement string>"
}
```

If you output a tool call, STOP writing immediately after the JSON block. The system will execute it and return the result to you in the next prompt. You will continue this loop until the task is fully complete.

If you DO NOT need to call a tool (the task is finished), you MUST end your response with a structured report in Vietnamese:
### 📝 TÓM TẮT THỰC HIỆN
- <Short list of actions taken>

### 📁 FILES CHANGED (thực tế)
- `<filepath>`: <Action, e.g., Đã sửa>

### 🎯 KẾ HOẠCH TIẾP THEO (Gợi ý cho user)
1. <Step 1>
2. <Step 2>
]
"""


# ─────────────────────────────────────────────────────────────
# Flag Parser thủ công tránh lỗi
# ─────────────────────────────────────────────────────────────

def _parse_flags(prompt_str: str) -> tuple[list[str], bool, bool, str]:
    """
    Phân tích cú pháp prompt để trích xuất flags: -f, -d, -l
    Trả về: (files_list, include_diff, include_logs, clean_prompt)
    """
    files = []
    include_diff = False
    include_logs = False
    clean_prompt_parts = []
    
    try:
        tokens = shlex.split(prompt_str, posix=False)
    except ValueError:
        tokens = prompt_str.split()

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "-f":
            if i + 1 < len(tokens):
                files.append(tokens[i+1].strip('"\''))
                i += 2
            else:
                i += 1
        elif token == "-d":
            include_diff = True
            i += 1
        elif token == "-l":
            include_logs = True
            i += 1
        else:
            clean_prompt_parts.append(token)
            i += 1

    clean_prompt = " ".join(clean_prompt_parts)
    return files, include_diff, include_logs, clean_prompt


async def _get_git_diff() -> str:
    """Lấy git diff hiện tại của project."""
    project_path = cfg.get_active_project_path()
    try:
        res = await run_command(["git", "diff"], cwd=project_path, timeout=15)
        if res.success and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return ""


def _get_last_agent_logs(n: int = 50) -> str:
    """Lấy N dòng log gần nhất."""
    if not cfg.LOG_FILE.exists():
        return ""
    try:
        with cfg.LOG_FILE.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-n:]).strip()
    except Exception:
        return ""


def _read_project_file(rel_path: str) -> str:
    """Đọc file trong dự án."""
    project_path = cfg.get_active_project_path()
    target = (project_path / rel_path).resolve()
    if not str(target).startswith(str(project_path.resolve())):
        return f"[Lỗi: Không thể truy cập file nằm ngoài dự án: {rel_path}]"
    if not target.exists():
        return f"[Lỗi: File không tồn tại: {rel_path}]"
    try:
        size = target.stat().st_size
        if size > 300 * 1024:
            return f"[Lỗi: File quá lớn để đính kèm ({size/1024:.1f} KB): {rel_path}]"
        
        content = target.read_text(encoding="utf-8", errors="replace")
        
        # Mask .env files to prevent AI from leaking them
        is_sensitive = target.name.startswith(".env") or target.name.endswith(".pem") or target.name.endswith(".key")
        if is_sensitive:
            import re
            masked_lines = []
            for line in content.splitlines():
                if line.strip().startswith("#") or not line.strip():
                    masked_lines.append(line)
                elif "=" in line:
                    line = re.sub(r'(=).*', r'\1********', line)
                    masked_lines.append(line)
                else:
                    masked_lines.append(line)
            content = "\n".join(masked_lines)
            
        return content
    except Exception as exc:
        return f"[Lỗi không thể đọc file {rel_path}: {exc}]"


def _write_project_file(rel_path: str, content: str) -> str:
    """Ghi nội dung vào file trong dự án (Ghi đè)."""
    project_path = cfg.get_active_project_path()
    target = (project_path / rel_path).resolve()
    if not str(target).startswith(str(project_path.resolve())):
        return f"[Lỗi bảo mật: Không thể ghi file ngoài dự án: {rel_path}]"
        
    try:
        # Đảm bảo thư mục cha tồn tại
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"[Thành công: Đã ghi đè {len(content)} byte vào {rel_path}]"
    except Exception as exc:
        return f"[Lỗi không thể ghi file {rel_path}: {exc}]"


def _replace_project_file_code(rel_path: str, target_str: str, replacement_str: str) -> str:
    """Thay thế một đoạn code cụ thể trong file."""
    project_path = cfg.get_active_project_path()
    target = (project_path / rel_path).resolve()
    if not str(target).startswith(str(project_path.resolve())):
        return f"[Lỗi bảo mật: Không thể sửa file ngoài dự án: {rel_path}]"
    if not target.exists():
        return f"[Lỗi: File không tồn tại để sửa: {rel_path}]"
        
    try:
        content = target.read_text(encoding="utf-8")
        if target_str not in content:
            return f"[Lỗi: Không tìm thấy đoạn code (target) cần sửa trong file {rel_path}. Vui lòng kiểm tra kỹ khoảng trắng/thụt lề và thử lại.]"
            
        new_content = content.replace(target_str, replacement_str)
        target.write_text(new_content, encoding="utf-8")
        return f"[Thành công: Đã thay thế đoạn code trong {rel_path}]"
    except Exception as exc:
        return f"[Lỗi không thể sửa code trong {rel_path}: {exc}]"


# ─────────────────────────────────────────────────────────────
# Helper phát hiện file thay đổi thực tế (Git-based Diff)
# ─────────────────────────────────────────────────────────────

async def _get_git_porcelain_status() -> dict[str, str]:
    project_path = cfg.get_active_project_path()
    try:
        res = await run_command(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            timeout=10,
        )
        if not res.success:
            return {}

        status_map = {}
        for line in res.stdout.splitlines():
            if len(line) > 3:
                status = line[:2].strip()
                filepath = line[3:].strip().replace('"', '')
                status_map[filepath] = status
        return status_map
    except Exception:
        return {}


def _detect_file_diff(before: dict[str, str], after: dict[str, str]) -> list[str]:
    diff_report = []
    for filepath, status in after.items():
        status_name = "Sửa đổi"
        if status in ("??", "A"):
            status_name = "Tạo mới"
        elif status == "D":
            status_name = "Đã xóa"
        if filepath not in before or before[filepath] != status:
            diff_report.append(f"- `{filepath}` ({status_name})")
    for filepath in before:
        if filepath not in after:
            diff_report.append(f"- `{filepath}` (Đã lưu / Khôi phục)")
    return diff_report


# ─────────────────────────────────────────────────────────────
# AI Subprocess Execution
# ─────────────────────────────────────────────────────────────

async def _run_ai_command(full_context: str) -> ExecutionResult:
    ai_cmd = cfg.get_active_ai_command()
    project_path = cfg.get_active_project_path()
    
    logger.info("AI call: cmd=%s, project=%s, context_len=%d chars", ai_cmd, project_path, len(full_context))

    try:
        process = await asyncio.create_subprocess_shell(
            ai_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_path,
            env=os.environ.copy(),
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input=full_context.encode("utf-8")),
                timeout=cfg.AI_TIMEOUT,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return ExecutionResult(
                returncode=-1, stdout="", stderr="", success=False, timed_out=True
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        returncode = process.returncode or 0

        logger.info(
            "AI finished: returncode=%d, stdout=%d chars, stderr=%d chars",
            returncode, len(stdout), len(stderr),
        )

        return ExecutionResult(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            success=(returncode == 0),
        )

    except FileNotFoundError as exc:
        msg = f"Không tìm thấy lệnh: {ai_cmd.split()[0]!r}"
        logger.error("%s — %s", msg, exc)
        return ExecutionResult(
            returncode=-1, stdout="", stderr=msg, success=False, exception=str(exc)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Lỗi không mong đợi khi chạy AI command")
        return ExecutionResult(
            returncode=-1, stdout="", stderr=str(exc), success=False, exception=str(exc)
        )


def _format_result(result: ExecutionResult, prompt: str, real_changes: list[str]) -> list[str]:
    ai_cmd = cfg.get_active_ai_command()
    if result.timed_out:
        return [t("ai_timeout", timeout=cfg.AI_TIMEOUT, prompt=prompt[:200])]

    if result.exception:
        return [t("ai_not_found", err=result.exception, cmd=ai_cmd)]

    raw_output = result.output.strip() or t("ai_no_output")
    status_str = t("ai_status_success") if result.success else t("ai_status_failed")

    header = (
        f"{t('ai_title')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{t('ai_prompt_label')} `{prompt[:200]}`\n"
        f"Status: {status_str}\n\n"
    )

    actual_report = ""
    if real_changes:
        actual_report = (
            "\n\n"
            "📁 *BÁO CÁO THAY ĐỔI CỦA AGENT (THỰC TẾ)*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(real_changes)
        )

    messages: list[str] = []
    chunks = _split_output(raw_output, _MAX_OUTPUT_CHARS)

    for i, chunk in enumerate(chunks):
        prefix = header if i == 0 else f"{t('ai_cont', i=i+1, total=len(chunks))}\n\n"
        if i == len(chunks) - 1:
            messages.append(f"{prefix}```\n{chunk}\n```" + actual_report)
        else:
            messages.append(f"{prefix}```\n{chunk}\n```")

    return messages


def _split_output(text: str, chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


async def ask_ai(prompt: str, depth: int = 0) -> list[str]:
    if depth > 10:
        return ["⚠️ AI đã suy nghĩ quá 10 vòng lặp (Giới hạn). Dừng lại để đảm bảo an toàn và tránh tốn token quá mức."]
        
    ai_cmd = cfg.get_active_ai_command()
    if not ai_cmd:
        return [t("ai_no_cmd")]

    if not prompt.strip():
        return [t("ai_no_prompt")]

    # 1. Ghi nhận Git status trước khi chạy (chỉ vòng lặp đầu tiên)
    git_before = {}
    if depth == 0:
        git_before = await _get_git_porcelain_status()

    # 2. Phân tích flags trong prompt
    files, include_diff, include_logs, clean_prompt = _parse_flags(prompt)

    # 3. Tạo các đính kèm
    attachments = []
    
    for filepath in files:
        content = _read_project_file(filepath)
        attachments.append(
            f"--- [ĐÍNH KÈM FILE: {filepath}] ---\n"
            f"{content}\n"
            f"--- [HẾT FILE: {filepath}] ---"
        )
        
    if include_diff:
        diff_content = await _get_git_diff()
        if diff_content:
            attachments.append(
                f"--- [ĐÍNH KÈM GIT DIFF] ---\n"
                f"{diff_content}\n"
                f"--- [HẾT GIT DIFF] ---"
            )

    if include_logs:
        logs_content = _get_last_agent_logs(50)
        if logs_content:
            attachments.append(
                f"--- [ĐÍNH KÈM 50 DÒNG LOGS GẦN NHẤT] ---\n"
                f"{logs_content}\n"
                f"--- [HẾT LOGS] ---"
            )

    final_prompt = clean_prompt
    if attachments:
        final_prompt = "\n\n".join(attachments) + "\n\n" + "YÊU CẦU: " + clean_prompt

    prompt_with_rule = final_prompt + AI_REPORT_SYSTEM_INSTRUCTION
    full_context = memory.format_for_ai(prompt_with_rule)

    # 5. Thực thi AI
    result = await _run_ai_command(full_context)
    
    # 6. Parser Tool Calling
    if not result.timed_out and not result.exception:
        match = re.search(r"```json\s*(\{.*?\})\s*```", result.output, re.DOTALL)
        if match:
            try:
                tool_data = json.loads(match.group(1))
                tool_call = tool_data.get("tool_call")
                logger.info(f"AI requested tool call: {tool_call}")
                
                tool_result = ""
                if tool_call == "run_shell":
                    cmd = tool_data.get("command", "")
                    # Sửa lỗi: await execute_arbitrary
                    exec_res = await explorer.execute_arbitrary(cmd)
                    tool_result = f"Chạy lệnh: {cmd}\nKết quả: {exec_res}"
                elif tool_call == "read_file":
                    path = tool_data.get("path", "")
                    tool_result = f"Đọc file: {path}\nNội dung: {_read_project_file(path)}"
                elif tool_call == "write_file":
                    path = tool_data.get("path", "")
                    content = tool_data.get("content", "")
                    tool_result = _write_project_file(path, content)
                elif tool_call == "replace_code":
                    path = tool_data.get("path", "")
                    target_str = tool_data.get("target", "")
                    replacement_str = tool_data.get("replacement", "")
                    tool_result = _replace_project_file_code(path, target_str, replacement_str)
                else:
                    tool_result = f"Lỗi: Tool '{tool_call}' không được hỗ trợ."
                
                # Lưu vào context memory để AI biết tool đã chạy
                memory.add_exchange(clean_prompt, result.output.strip() + f"\n\n[System Tool Execution]\n{tool_result}")
                
                # Giãn cách 5 giây để tránh lỗi 429 Too Many Requests (Rate Limit của bản Free)
                await asyncio.sleep(5)
                
                # Gọi đệ quy vòng tiếp theo
                next_prompt = f"[System Tool Execution Result]\n{tool_result}\n\nPlease continue your task. (Iteration: {depth+1}/10)"
                return await ask_ai(next_prompt, depth + 1)
                
            except Exception as e:
                logger.error(f"Lỗi parse JSON tool call: {e}")

    # 7. Tính diff thực tế
    git_after = {}
    if depth == 0:
        git_after = await _get_git_porcelain_status()
    real_changes = _detect_file_diff(git_before, git_after)

    # 8. Lưu memory
    if not result.timed_out and not result.exception:
        memory.add_exchange(clean_prompt, result.output.strip())

    return _format_result(result, clean_prompt, real_changes)
