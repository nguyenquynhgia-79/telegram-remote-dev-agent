"""
modules/build.py
================
Build module.
Runs BUILD_COMMAND from .env inside PROJECT_PATH.
"""

import logging

import config.config as cfg
from utils.executor import ExecutionResult, run_command
from utils.i18n import t

logger = logging.getLogger(__name__)


def _format_result(result: ExecutionResult, build_cmd: str) -> str:
    """Format build result as a Telegram Markdown message."""
    if result.timed_out:
        status = t("build_timeout")
    elif result.exception:
        status = f"💥 {result.exception}"
    elif result.success:
        status = t("build_success")
    else:
        status = t("build_failed", code=result.returncode)

    output = result.output or t("exec_no_output")
    project_path = cfg.get_active_project_path()

    return (
        f"{t('build_title')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{t('build_command')} `{build_cmd}`\n"
        f"{t('build_path')} `{project_path}`\n"
        f"Status: {status}\n\n"
        f"```\n{output}\n```"
    )


async def run_build() -> str:
    """Execute the configured BUILD_COMMAND in PROJECT_PATH."""
    build_cmd = cfg.get_active_build_command()
    project_path = cfg.get_active_project_path()
    
    logger.info("Starting build: %s in %s", build_cmd, project_path)

    if not build_cmd:
        return t("build_no_cmd")

    result = await run_command(
        build_cmd,
        cwd=project_path,
        timeout=cfg.DEFAULT_TIMEOUT,
        shell=True,
    )
    return _format_result(result, build_cmd)
