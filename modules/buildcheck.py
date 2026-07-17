"""
modules/buildcheck.py
=====================
Tự động chạy build và chẩn đoán lỗi biên dịch (/buildcheck).

Cơ chế:
1. Thực thi BUILD_COMMAND từ .env.
2. Nếu exit code != 0, trích xuất lỗi từ stdout/stderr.
3. Đóng gói lỗi, gửi yêu cầu chẩn đoán đến Gemini 3.5 Flash.
4. Trả về báo cáo phân tích nguyên nhân + giải pháp sửa lỗi cụ thể cho user.
"""

import logging

import config.config as cfg
from utils.executor import run_command
from modules.ai import ask_ai

logger = logging.getLogger(__name__)


async def run_diagnostics() -> str | list[str]:
    """
    Chạy build và chẩn đoán lỗi nếu xảy ra.
    
    Returns:
        Thông báo kết quả đơn lẻ hoặc danh sách tin nhắn từ AI.
    """
    build_cmd = cfg.get_active_build_command()
    project_path = cfg.get_active_project_path()

    if not build_cmd:
        return "⚠️ *Buildcheck* — Chưa cấu hình `BUILD_COMMAND` cho dự án hiện tại."

    logger.info("Chạy Buildcheck: %s in %s", build_cmd, project_path)
    
    # 1. Chạy thử build
    result = await run_command(
        build_cmd,
        cwd=project_path,
        timeout=cfg.DEFAULT_TIMEOUT,
        shell=True,
    )

    if result.success:
        return (
            "🔨 *Buildcheck — Thành công* ✅\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Lệnh: `{build_cmd}`\n"
            "Trạng thái: Trình biên dịch báo thành công! Không phát hiện lỗi."
        )

    # 2. Thu thập log lỗi nếu thất bại
    error_output = result.output.strip()
    # Lấy 1500 ký tự cuối cùng để tránh quá tải token
    log_tail = error_output[-1500:] if len(error_output) > 1500 else error_output

    status_desc = "Bị ngắt (Timeout)" if result.timed_out else f"Lỗi biên dịch (Exit code {result.returncode})"

    logger.warning("Buildcheck phát hiện lỗi: %s. Đang gọi AI chẩn đoán...", status_desc)

    # 3. Tạo prompt gửi cho AI
    diagnostic_prompt = (
        f"Lệnh build '{build_cmd}' đã thất bại với trạng thái '{status_desc}'.\n"
        f"Dưới đây là log lỗi cuối cùng của trình biên dịch:\n"
        f"```\n{log_tail}\n```\n"
        f"Hãy giải thích chi tiết tại sao lỗi này xảy ra và hướng dẫn tôi cách sửa nó (hoặc tự viết code sửa nếu có thể)."
    )

    # 4. Gọi AI phân tích
    ai_responses = await ask_ai(diagnostic_prompt)

    # 5. Gắn tiêu đề báo cáo lỗi lên đầu tin nhắn đầu tiên của AI
    header = (
        f"🔨 *Buildcheck — Phát hiện Lỗi* ❌\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Lệnh: `{build_cmd}`\n"
        f"🔥 Trạng thái: `{status_desc}`\n"
        f"🤖 *Đang phân tích lỗi bằng Gemini 3.5 Flash...*\n\n"
    )

    if isinstance(ai_responses, list) and ai_responses:
        ai_responses[0] = header + ai_responses[0]
        return ai_responses

    return header + "❌ Lỗi: AI không phản hồi chẩn đoán."
