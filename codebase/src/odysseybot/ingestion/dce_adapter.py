"""Subprocess wrapper for DiscordChatExporter CLI with strict security isolation."""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from odysseybot.config import settings
from odysseybot.domain.models import SyncResult


class DCEAdapterError(Exception):
    """Base exception for DiscordChatExporter wrapper failures."""


class DCEAuthError(DCEAdapterError):
    """Raised when DCE credentials fail (401/403)."""


class DCEAdapter:
    """Encapsulates execution of DiscordChatExporter CLI in an isolated environment."""

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path or settings.DCE_EXPORTER_PATH

    def check_binary(self) -> str:
        path = shutil.which(self.binary_path)
        if not path:
            raise DCEAdapterError(f"DiscordChatExporter binary not found: {self.binary_path}")
        return path

    async def export_channel(
        self,
        channel_id: str,
        output_dir: Path,
        after_timestamp: Optional[str] = None,
        include_threads: bool = True,
    ) -> Path:
        """Executes DCE for a single channel/thread securely without logging credentials."""
        binary = self.check_binary()

        output_path = output_dir / f"{channel_id}.json"
        
        cmd = [
            binary,
            "export",
            "-c", channel_id,
            "-f", "Json",
            "-o", str(output_path),
            "--parallel", str(settings.DCE_MAX_PARALLEL),
            "--media", "false",
            "--reuse-media", "false",
        ]

        if include_threads:
            cmd.extend(["--include-threads", "All"])

        if after_timestamp:
            cmd.extend(["--after", after_timestamp])

        # Construct minimal isolated environment (PATH + DISCORD_TOKEN)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        if settings.DCE_USER_TOKEN:
            env["DISCORD_TOKEN"] = settings.DCE_USER_TOKEN.get_secret_value()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=settings.DCE_TIMEOUT_SECONDS,
            )

            stderr_str = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                # Sanitize secret token from stderr before raising exception
                sanitized_stderr = stderr_str
                if settings.DCE_USER_TOKEN:
                    sanitized_stderr = sanitized_stderr.replace(settings.DCE_USER_TOKEN.get_secret_value(), "***REDACTED***")
                
                if "401" in stderr_str or "Unauthorized" in stderr_str or "403" in stderr_str:
                    raise DCEAuthError("Authentication error during export: HTTP 401/403 Unauthorized")
                raise DCEAdapterError(f"DCE export failed with exit code {process.returncode}: {sanitized_stderr[:200]}")


            return output_path

        except asyncio.TimeoutError:
            try:
                process.kill()
            except Exception:
                pass
            raise DCEAdapterError(f"DCE process timed out after {settings.DCE_TIMEOUT_SECONDS}s")
