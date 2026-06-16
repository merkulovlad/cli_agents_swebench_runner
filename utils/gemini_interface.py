import os
import subprocess
from typing import Dict, List

class GeminiCodeInterface:
    """Interface for interacting with the Google Gemini CLI."""

    def __init__(self):
        """Ensure the Gemini CLI is available on the system."""
        try:
            result = subprocess.run(["gemini", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(
                    "Gemini CLI not found. Please ensure 'gemini' is installed and in PATH"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "Gemini CLI not found. Please ensure 'gemini' is installed and in PATH"
            )

    def _build_env(self) -> Dict[str, str]:
        """Build environment for Gemini CLI.

        Supports `api`/`API` as convenience aliases for `GEMINI_API_KEY`.
        If `GOOGLE_API_KEY` is already set, it is left untouched.
        """
        env = os.environ.copy()

        api_key = env.get("api") or env.get("API")
        if api_key and not env.get("GEMINI_API_KEY") and not env.get("GOOGLE_API_KEY"):
            env["GEMINI_API_KEY"] = api_key

        has_gemini_key = bool(env.get("GEMINI_API_KEY"))
        has_google_key = bool(env.get("GOOGLE_API_KEY"))

        if has_gemini_key or has_google_key:
            print("Gemini CLI: using API key from environment")
        else:
            print("Gemini CLI: using default Gemini authentication")

        return env

    def execute_code_cli(self, prompt: str, cwd: str, model: str = None) -> Dict[str, any]:
        """Execute Gemini via CLI and capture the response.

        Args:
            prompt: The prompt to send to Gemini.
            cwd: Working directory to execute in.
            model: Optional model to use.
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(cwd)

            # Build command
            cmd = ["gemini"]
            if model:
                cmd.extend(["--model", model])

            # Execute gemini command with the prompt via stdin
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                env=self._build_env(),
            )

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
        """Extract file changes from Gemini's response (placeholder)."""
        return []
