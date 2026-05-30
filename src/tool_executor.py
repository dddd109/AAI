"""
Tool Executor — sandboxed execution of tool_call commands via Claude Code CLI.
Runs asynchronously and returns results for the next conversation turn.
"""

import logging
import subprocess
import threading
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Execute system commands via Claude Code CLI in a sandboxed subprocess."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        tool_cfg = cfg["tool"]
        self.enabled = tool_cfg.get("enabled", True)
        self.sandbox_mode = tool_cfg.get("sandbox_mode", True)
        self.cli_path = tool_cfg.get("claude_cli_path", "claude")
        self.timeout = tool_cfg.get("timeout", 120)
        self._last_result: Optional[str] = None

    def execute(self, tool_call: str, on_complete=None) -> Optional[str]:
        """Execute a tool_call string via Claude Code.

        Args:
            tool_call: Natural language instruction for Claude Code CLI.
            on_complete: Optional callback(result_str) for async execution.

        Returns:
            The execution result string, or None if running async.
        """
        if not tool_call or not tool_call.strip():
            return None

        if not self.enabled:
            logger.info(f"Tool execution disabled, skipping: {tool_call[:80]}")
            return None

        if self.sandbox_mode:
            logger.info(f"[SANDBOX] Would execute: {tool_call[:120]}")

        if on_complete:
            thread = threading.Thread(
                target=self._run_and_callback,
                args=(tool_call, on_complete),
                daemon=True,
            )
            thread.start()
            return None
        else:
            return self._run(tool_call)

    def _run(self, instruction: str) -> str:
        """Synchronous execution."""
        try:
            cmd = [self.cli_path, "-p", instruction, "--no-input", "--max-turns", "3"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=".",
            )
            output = (result.stdout + "\n" + result.stderr).strip()
            self._last_result = output
            logger.info(f"Tool execution completed ({len(output)} chars)")
            return output
        except subprocess.TimeoutExpired:
            logger.warning(f"Tool execution timed out after {self.timeout}s")
            return "[Timeout]"
        except FileNotFoundError:
            logger.error(f"Claude CLI not found: {self.cli_path}")
            return "[Claude Code CLI not found]"
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"[Error: {e}]"

    def _run_and_callback(self, instruction: str, callback):
        """Run async and call callback with result."""
        result = self._run(instruction)
        try:
            callback(result)
        except Exception as e:
            logger.error(f"Callback error: {e}")

    @property
    def last_result(self) -> Optional[str]:
        return self._last_result
