import os
import json
import subprocess
from typing import Dict, List, Optional
from dotenv import load_dotenv
from utils.status import log_status

load_dotenv()


class ClaudeCodeInterface:
    """Interface for interacting with Claude Code CLI."""

    def __init__(self):
        """Ensure the Claude CLI is available on the system."""
        try:
            result = subprocess.run([
                "claude", "--version"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    "Claude CLI not found. Please ensure 'claude' is installed and in PATH"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "Claude CLI not found. Please ensure 'claude' is installed and in PATH"
            )

    def _build_env(self) -> Dict[str, str]:
        """Build environment for Claude Code CLI.

        Supports `api`/`API` as convenience aliases for Claude Code's official
        `ANTHROPIC_API_KEY` variable.
        """
        env = os.environ.copy()

        api_key = env.get("api") or env.get("API")
        if api_key and not env.get("ANTHROPIC_API_KEY"):
            env["ANTHROPIC_API_KEY"] = api_key

        has_api_key = bool(env.get("ANTHROPIC_API_KEY"))
        has_base_url = bool(env.get("ANTHROPIC_BASE_URL"))

        if has_api_key and has_base_url:
            print("Claude Code: using API key with custom ANTHROPIC_BASE_URL")
        elif has_api_key:
            print("Claude Code: using API key with default Anthropic endpoint")
        elif has_base_url:
            print("Claude Code: using custom ANTHROPIC_BASE_URL without API key override")
        else:
            print("Claude Code: using default Claude Code authentication")

        return env

    def execute_code_cli(self, prompt: str, cwd: str, model: str = None) -> Dict[str, any]:
        """Execute Claude Code via CLI and capture the response.

        Args:
            prompt: The prompt to send to Claude.
            cwd: Working directory to execute in.
            model: Optional model to use (e.g., 'opus-4.1', 'sonnet-3.7').
        """
        try:
            # Save the current directory
            original_cwd = os.getcwd()

            # Change to the working directory
            os.chdir(cwd)

            # Build command with optional model parameter
            cmd = ["claude", "-p", "--dangerously-skip-permissions"]
            if model:
                cmd.extend(["--model", model])

            # Execute claude command with the prompt via stdin
            log_status(f"Claude Code CLI started in {cwd}; waiting for model response")
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                env=self._build_env(),
            )
            log_status(f"Claude Code CLI finished with exit code {result.returncode}")

            # Restore original directory
            os.chdir(original_cwd)

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            os.chdir(original_cwd)
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out after 10 minutes",
                "returncode": -1,
            }
        except Exception as e:
            os.chdir(original_cwd)
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }

    def extract_file_changes(self, response: str) -> List[Dict[str, str]]:
        """Extract file changes from Claude's response."""
        # This will be implemented by patch_extractor.py
        # For now, return empty list
        return []
