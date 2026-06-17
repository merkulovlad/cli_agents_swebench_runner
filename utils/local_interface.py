import os
import shlex
import shutil
import subprocess
from typing import Any, Dict, List
from utils.status import log_status


class LocalAgentInterface:
    """Interface for running a user-provided local agent command."""

    def __init__(self, command: str, timeout: int = 600):
        if not command or not command.strip():
            raise RuntimeError(
                "Local agent command is required. Pass --agent-command when using --backend local."
            )

        self.command = shlex.split(command)
        self.timeout = timeout

        executable = self.command[0]
        if shutil.which(executable) is None:
            raise RuntimeError(
                f"Local agent command not found: {executable}. "
                "Ensure it is installed and in PATH."
            )

    def execute_code_cli(self, prompt: str, cwd: str, model: str = None) -> Dict[str, Any]:
        """Run the local agent command with the SWE-bench prompt on stdin."""
        try:
            original_cwd = os.getcwd()
            os.chdir(cwd)

            display_command = " ".join(self.command)
            log_status(f"Local agent started in {cwd}: {display_command}; waiting for response")
            result = subprocess.run(
                self.command,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=os.environ.copy(),
            )
            log_status(f"Local agent finished with exit code {result.returncode}")

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
                "stderr": f"Command timed out after {self.timeout} seconds",
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
        """Local agents are measured by filesystem changes in the checkout."""
        return []
