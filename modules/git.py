"""
modules/git.py
==============
Git operations module.
All commands run inside PROJECT_PATH from .env.
"""

import logging
from pathlib import Path

import config.config as cfg
from utils.executor import ExecutionResult, run_command
from utils.i18n import t

logger = logging.getLogger(__name__)


async def _git(
    *args: str,
    cwd: Path | None = None,
    timeout: int = cfg.DEFAULT_TIMEOUT,
) -> ExecutionResult:
    """Helper: run a git subcommand in the project directory."""
    if cwd is None:
        cwd = cfg.get_active_project_path()
    return await run_command(["git", *args], cwd=cwd, timeout=timeout)


def _format_result(result: ExecutionResult, title: str) -> str:
    """Format an ExecutionResult as a Telegram Markdown message."""
    if result.timed_out:
        status = t("git_timeout")
    elif result.exception:
        status = f"💥 {result.exception}"
    elif result.success:
        status = t("git_success")
    else:
        status = t("git_failed")

    output = result.output or t("exec_no_output")
    project_path = cfg.get_active_project_path()

    return (
        f"{t('git_title', sub=title)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{t('git_path')} `{project_path}`\n"
        f"Status: {status}\n\n"
        f"```\n{output}\n```"
    )


async def git_status() -> str:
    result = await _git("status")
    return _format_result(result, t("git_sub_status"))


async def git_pull() -> str:
    result = await _git("pull", timeout=120)
    return _format_result(result, t("git_sub_pull"))


async def git_push() -> str:
    result = await _git("push", timeout=120)
    return _format_result(result, t("git_sub_push"))


async def git_branch() -> str:
    result = await _git("branch", "-a")
    return _format_result(result, t("git_sub_branch"))


async def git_log(n: int = 10) -> str:
    result = await _git("log", f"-{n}", "--oneline", "--decorate", "--color=never")
    return _format_result(result, t("git_sub_log", n=n))


async def git_checkout(branch: str) -> str:
    result = await _git("checkout", branch)
    return _format_result(result, t("git_sub_checkout", b=branch))
