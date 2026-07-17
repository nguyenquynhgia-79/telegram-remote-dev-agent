"""
utils/executor.py
=================
Safe async command executor with timeout, stdout/stderr capture,
and exception handling. Never blocks the asyncio event loop.
"""

import asyncio
import logging
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Holds the complete result of a shell command execution."""
    returncode: int
    stdout: str
    stderr: str
    success: bool
    timed_out: bool = False
    exception: Optional[str] = None

    @property
    def output(self) -> str:
        """Combined stdout + stderr for display purposes."""
        parts = []
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(f"[stderr]\n{self.stderr.strip()}")
        return "\n".join(parts) if parts else "(no output)"

    @property
    def status_emoji(self) -> str:
        """Visual status indicator."""
        if self.timed_out:
            return "⏱️"
        if self.exception:
            return "💥"
        return "✅" if self.success else "❌"


async def run_command(
    command: str | list[str],
    *,
    cwd: Optional[Path] = None,
    timeout: int = 300,
    shell: bool = False,
) -> ExecutionResult:
    """
    Execute a shell command asynchronously.

    Args:
        command: Command string or list of arguments.
        cwd:     Working directory (defaults to current dir).
        timeout: Seconds before killing the process.
        shell:   Run through system shell (needed for some Windows commands).

    Returns:
        ExecutionResult with returncode, stdout, stderr, and status flags.
    """
    # Normalize to list for asyncio.create_subprocess_exec
    if isinstance(command, str):
        try:
            args = shlex.split(command, posix=False)
        except ValueError:
            args = command.split()
    else:
        args = list(command)

    log_cmd = command if isinstance(command, str) else " ".join(args)
    logger.info("Executing: %s (cwd=%s, timeout=%ds)", log_cmd, cwd, timeout)

    try:
        if shell:
            # Use create_subprocess_shell for commands that need shell features
            process = await asyncio.create_subprocess_shell(
                command if isinstance(command, str) else " ".join(args),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            logger.warning("Command timed out after %ds: %s", timeout, log_cmd)
            return ExecutionResult(
                returncode=-1,
                stdout="",
                stderr="",
                success=False,
                timed_out=True,
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        returncode = process.returncode or 0
        success = returncode == 0

        logger.info(
            "Command finished: returncode=%d, stdout_len=%d, stderr_len=%d",
            returncode, len(stdout), len(stderr),
        )
        return ExecutionResult(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            success=success,
        )

    except FileNotFoundError as exc:
        msg = f"Command not found: {args[0]!r}. Is it installed and on PATH?"
        logger.error("%s — %s", msg, exc)
        return ExecutionResult(
            returncode=-1,
            stdout="",
            stderr=msg,
            success=False,
            exception=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error running command: %s", log_cmd)
        return ExecutionResult(
            returncode=-1,
            stdout="",
            stderr=str(exc),
            success=False,
            exception=str(exc),
        )
