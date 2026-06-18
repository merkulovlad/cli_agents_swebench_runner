import os
import subprocess
import sys
from unittest.mock import ANY, Mock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.local_interface import LocalAgentInterface


def test_init_requires_command():
    with pytest.raises(RuntimeError) as exc_info:
        LocalAgentInterface("")

    assert str(exc_info.value) == (
        "Local agent command is required. Pass --agent-command when using --backend local."
    )


def test_init_checks_executable_in_path():
    with patch("utils.local_interface.shutil.which", return_value=None):
        with pytest.raises(RuntimeError) as exc_info:
            LocalAgentInterface("supercode --flag")

    assert str(exc_info.value) == (
        "Local agent command not found: supercode. Ensure it is installed and in PATH."
    )


def test_execute_code_cli_runs_headless_command_in_repo():
    completed = Mock(returncode=0, stdout="done", stderr="")

    with patch("utils.local_interface.shutil.which", return_value="/bin/supercode"):
        interface = LocalAgentInterface("supercode --mode swe", timeout=123)

    with patch("utils.local_interface.subprocess.run", return_value=completed) as run_mock:
        result = interface.execute_code_cli("fix bug", "/tmp/repo")

    observed = {
        "run_args": run_mock.call_args.args,
        "run_kwargs": run_mock.call_args.kwargs,
        "result": result,
    }
    expected = {
        "run_args": (
            ["supercode", "--mode", "swe", "-p", "fix bug", "-skip-permissions"],
        ),
        "run_kwargs": {
            "cwd": "/tmp/repo",
            "capture_output": True,
            "text": True,
            "timeout": 123,
            "env": ANY,
        },
        "result": {
            "success": True,
            "stdout": "done",
            "stderr": "",
            "returncode": 0,
        },
    }

    assert observed == expected


def test_execute_code_cli_reports_timeout():
    with patch("utils.local_interface.shutil.which", return_value="/bin/supercode"):
        interface = LocalAgentInterface("supercode", timeout=42)

    timeout = subprocess.TimeoutExpired(
        ["supercode", "-p", "fix bug", "-skip-permissions"], 42
    )
    with patch("utils.local_interface.subprocess.run", side_effect=timeout):
        result = interface.execute_code_cli("fix bug", "/tmp/repo")

    assert result == {
        "success": False,
        "stdout": "",
        "stderr": "Command timed out after 42 seconds",
        "returncode": -1,
    }
