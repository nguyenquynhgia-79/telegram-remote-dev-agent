"""
modules/docker.py
=================
Docker operations module.
Uses docker compose if DOCKER_COMPOSE_PATH is configured.
"""

import logging
from pathlib import Path
from typing import Optional

import config.config as cfg
from utils.executor import ExecutionResult, run_command
from utils.i18n import t

logger = logging.getLogger(__name__)


def _docker_compose_cmd() -> list[str]:
    return ["docker", "compose"]


def _compose_file_args(compose_path: Path | None) -> list[str]:
    if compose_path and compose_path.exists():
        return ["-f", str(compose_path)]
    return []


def _get_cwd(compose_path: Path | None) -> Optional[Path]:
    if compose_path and compose_path.exists():
        return compose_path.parent
    return None


def _format_result(result: ExecutionResult, title: str) -> str:
    """Format an ExecutionResult as a Telegram Markdown message."""
    if result.timed_out:
        status = t("docker_timeout")
    elif result.exception:
        status = f"💥 {result.exception}"
    elif result.success:
        status = t("docker_success")
    else:
        status = t("docker_failed")

    output = result.output or t("exec_no_output")

    return (
        f"{t('docker_title', sub=title)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Status: {status}\n\n"
        f"```\n{output}\n```"
    )


async def docker_up(detach: bool = True) -> str:
    compose_path = cfg.get_active_docker_compose_path()
    if not compose_path:
        return "⚠️ *Docker* — Không tìm thấy `docker-compose.yml` trong dự án hiện tại\\."

    cmd = _docker_compose_cmd() + _compose_file_args(compose_path) + ["up"]
    if detach:
        cmd.append("-d")
    result = await run_command(cmd, cwd=_get_cwd(compose_path), timeout=cfg.DEFAULT_TIMEOUT)
    return _format_result(result, t("docker_sub_up"))


async def docker_down() -> str:
    compose_path = cfg.get_active_docker_compose_path()
    if not compose_path:
        return "⚠️ *Docker* — Không tìm thấy `docker-compose.yml` trong dự án hiện tại\\."

    cmd = _docker_compose_cmd() + _compose_file_args(compose_path) + ["down"]
    result = await run_command(cmd, cwd=_get_cwd(compose_path), timeout=cfg.DEFAULT_TIMEOUT)
    return _format_result(result, t("docker_sub_down"))


async def docker_restart() -> str:
    compose_path = cfg.get_active_docker_compose_path()
    if not compose_path:
        return "⚠️ *Docker* — Không tìm thấy `docker-compose.yml` trong dự án hiện tại\\."

    cmd = _docker_compose_cmd() + _compose_file_args(compose_path) + ["restart"]
    result = await run_command(cmd, cwd=_get_cwd(compose_path), timeout=cfg.DEFAULT_TIMEOUT)
    return _format_result(result, t("docker_sub_restart"))


async def docker_ps() -> str:
    # docker ps có thể chạy toàn cục không cần compose file
    result = await run_command(
        ["docker", "ps", "--format", "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"],
        timeout=30,
    )
    return _format_result(result, t("docker_sub_ps"))


async def docker_logs(tail: int = 50, service: Optional[str] = None) -> str:
    compose_path = cfg.get_active_docker_compose_path()
    if not compose_path:
        return "⚠️ *Docker* — Không tìm thấy `docker-compose.yml` trong dự án hiện tại\\."

    cmd = _docker_compose_cmd() + _compose_file_args(compose_path) + ["logs", f"--tail={tail}"]
    if service:
        cmd.append(service)
    result = await run_command(cmd, cwd=_get_cwd(compose_path), timeout=60)
    return _format_result(result, t("docker_sub_logs", n=tail))
