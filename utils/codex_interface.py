import os
import subprocess
from typing import Dict, List
from utils.status import log_status

class CodexCodeInterface:
    """Interface for interacting with the Codex CLI."""

    def __init__(self):
        """Ensure the Codex CLI is available on the system."""
        try:
            result = subprocess.run(["codex", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    "Codex CLI not found. Please ensure 'codex' is installed and in PATH"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "Codex CLI not found. Please ensure 'codex' is installed and in PATH"
            )

    def _build_env(self) -> Dict[str, str]:
        """Build environment for Codex CLI.

        Supports `api`/`API` as convenience aliases for `OPENAI_API_KEY`.
        """
        env = os.environ.copy()

        api_key = env.get("api") or env.get("API")
        if api_key and not env.get("OPENAI_API_KEY"):
            env["OPENAI_API_KEY"] = api_key

        has_api_key = bool(env.get("OPENAI_API_KEY"))
        has_base_url = bool(env.get("OPENAI_BASE_URL"))

        if has_api_key and has_base_url:
            print("Codex CLI: using API key with custom OPENAI_BASE_URL")
        elif has_api_key:
            print("Codex CLI: using API key with default OpenAI endpoint")
        elif has_base_url:
            print("Codex CLI: using custom OPENAI_BASE_URL without API key override")
        else:
            print("Codex CLI: using default Codex authentication")

        return env

    def execute_code_cli(self, prompt: str, cwd: str, model: str = None) -> Dict[str, any]:
        """Execute Codex via CLI and capture the response."""
        try:
            original_cwd = os.getcwd()
            os.chdir(cwd)
            cmd = ["codex"]
            if model:
                cmd.extend(["--model", model])
            log_status(f"Codex CLI started in {cwd}; waiting for model response")
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=600,
                env=self._build_env(),
            )
            log_status(f"Codex CLI finished with exit code {result.returncode}")
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
        """Extract file changes from Codex's response (placeholder)."""
        return []
