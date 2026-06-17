import os
import sys
import subprocess
from unittest.mock import ANY, Mock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.claude_interface import ClaudeCodeInterface


def make_interface():
    return ClaudeCodeInterface.__new__(ClaudeCodeInterface)


def test_init_checks_claude_version():
    with patch("utils.claude_interface.subprocess.run") as run_mock:
        run_mock.return_value = Mock(returncode=0)

        ClaudeCodeInterface()

    observed = {
        "run_args": run_mock.call_args.args,
        "run_kwargs": run_mock.call_args.kwargs,
    }
    expected = {
        "run_args": (["claude", "--version"],),
        "run_kwargs": {
            "capture_output": True,
            "text": True,
        },
    }

    assert observed == expected


def test_init_raises_when_claude_returns_nonzero():
    with patch("utils.claude_interface.subprocess.run") as run_mock:
        run_mock.return_value = Mock(returncode=1)

        with pytest.raises(RuntimeError) as exc_info:
            ClaudeCodeInterface()

    observed = {
        "message": str(exc_info.value),
        "run_args": run_mock.call_args.args,
    }
    expected = {
        "message": "Claude CLI not found. Please ensure 'claude' is installed and in PATH",
        "run_args": (["claude", "--version"],),
    }

    assert observed == expected


def test_init_raises_when_claude_not_found():
    with patch(
        "utils.claude_interface.subprocess.run",
        side_effect=FileNotFoundError,
    ) as run_mock:
        with pytest.raises(RuntimeError) as exc_info:
            ClaudeCodeInterface()

    observed = {
        "message": str(exc_info.value),
        "run_args": run_mock.call_args.args,
    }
    expected = {
        "message": "Claude CLI not found. Please ensure 'claude' is installed and in PATH",
        "run_args": (["claude", "--version"],),
    }

    assert observed == expected


def test_build_env_maps_api_alias_to_anthropic_api_key(monkeypatch):
    interface = make_interface()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("API", raising=False)
    monkeypatch.setenv("api", "test-key")

    env = interface._build_env()

    observed = {
        "api": env.get("api"),
        "anthropic_api_key": env.get("ANTHROPIC_API_KEY"),
    }
    expected = {
        "api": "test-key",
        "anthropic_api_key": "test-key",
    }

    assert observed == expected


def test_build_env_maps_uppercase_api_alias_to_anthropic_api_key(monkeypatch):
    interface = make_interface()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("api", raising=False)
    monkeypatch.setenv("API", "test-key")

    env = interface._build_env()

    observed = {
        "api": env.get("API"),
        "anthropic_api_key": env.get("ANTHROPIC_API_KEY"),
    }
    expected = {
        "api": "test-key",
        "anthropic_api_key": "test-key",
    }

    assert observed == expected


def test_build_env_does_not_override_existing_anthropic_api_key(monkeypatch):
    interface = make_interface()
    monkeypatch.setenv("api", "alias-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-key")

    env = interface._build_env()

    observed = {
        "api": env.get("api"),
        "anthropic_api_key": env.get("ANTHROPIC_API_KEY"),
    }
    expected = {
        "api": "alias-key",
        "anthropic_api_key": "real-key",
    }

    assert observed == expected


def test_execute_code_cli_calls_claude_with_expected_arguments():
    interface = make_interface()
    completed = Mock(returncode=0, stdout="done", stderr="")

    with patch("utils.claude_interface.subprocess.run", return_value=completed) as run_mock:
        with patch("utils.claude_interface.os.getcwd", return_value="/original"):
            with patch("utils.claude_interface.os.chdir") as chdir_mock:
                result = interface.execute_code_cli(
                    "fix bug",
                    "/tmp/repo",
                    model="sonnet",
                )

    observed = {
        "run_args": run_mock.call_args.args,
        "run_kwargs": run_mock.call_args.kwargs,
        "result": result,
        "chdir_calls": [call.args for call in chdir_mock.call_args_list],
    }
    expected = {
        "run_args": (
            ["claude", "-p", "--dangerously-skip-permissions", "--model", "sonnet"],
        ),
        "run_kwargs": {
            "input": "fix bug",
            "capture_output": True,
            "text": True,
            "timeout": 600,
            "env": ANY,
        },
        "result": {
            "success": True,
            "stdout": "done",
            "stderr": "",
            "returncode": 0,
        },
        "chdir_calls": [("/tmp/repo",), ("/original",)],
    }

    assert observed == expected


def test_execute_code_cli_calls_claude_without_model():
    interface = make_interface()
    completed = Mock(returncode=0, stdout="done", stderr="")

    with patch("utils.claude_interface.subprocess.run", return_value=completed) as run_mock:
        with patch("utils.claude_interface.os.getcwd", return_value="/original"):
            with patch("utils.claude_interface.os.chdir"):
                interface.execute_code_cli("fix bug", "/tmp/repo")

    observed = {
        "run_args": run_mock.call_args.args,
        "run_kwargs": run_mock.call_args.kwargs,
    }
    expected = {
        "run_args": (["claude", "-p", "--dangerously-skip-permissions"],),
        "run_kwargs": {
            "input": "fix bug",
            "capture_output": True,
            "text": True,
            "timeout": 600,
            "env": ANY,
        },
    }

    assert observed == expected


def test_execute_code_cli_returns_success_result():
    interface = make_interface()
    completed = Mock(returncode=0, stdout="done", stderr="")

    with patch("utils.claude_interface.subprocess.run", return_value=completed):
        with patch("utils.claude_interface.os.getcwd", return_value="/original"):
            with patch("utils.claude_interface.os.chdir"):
                result = interface.execute_code_cli("fix bug", "/tmp/repo")

    observed = result
    expected = {
        "success": True,
        "stdout": "done",
        "stderr": "",
        "returncode": 0,
    }

    assert observed == expected


def test_execute_code_cli_returns_failure_result_for_nonzero_exit():
    interface = make_interface()
    completed = Mock(returncode=1, stdout="partial", stderr="error")

    with patch("utils.claude_interface.subprocess.run", return_value=completed):
        with patch("utils.claude_interface.os.getcwd", return_value="/original"):
            with patch("utils.claude_interface.os.chdir"):
                result = interface.execute_code_cli("fix bug", "/tmp/repo")

    observed = result
    expected = {
        "success": False,
        "stdout": "partial",
        "stderr": "error",
        "returncode": 1,
    }

    assert observed == expected


def test_execute_code_cli_returns_timeout_result():
    interface = make_interface()

    with patch(
        "utils.claude_interface.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["claude"], timeout=600),
    ):
        with patch("utils.claude_interface.os.getcwd", return_value="/original"):
            with patch("utils.claude_interface.os.chdir"):
                result = interface.execute_code_cli("fix bug", "/tmp/repo")

    observed = result
    expected = {
        "success": False,
        "stdout": "",
        "stderr": "Command timed out after 10 minutes",
        "returncode": -1,
    }

    assert observed == expected


def test_execute_code_cli_restores_original_cwd_after_success():
    interface = make_interface()
    completed = Mock(returncode=0, stdout="done", stderr="")

    with patch("utils.claude_interface.subprocess.run", return_value=completed):
        with patch("utils.claude_interface.os.getcwd", return_value="/original"):
            with patch("utils.claude_interface.os.chdir") as chdir_mock:
                interface.execute_code_cli("fix bug", "/tmp/repo")

    observed = [call.args for call in chdir_mock.call_args_list]
    expected = [("/tmp/repo",), ("/original",)]

    assert observed == expected


def test_execute_code_cli_restores_original_cwd_after_timeout():
    interface = make_interface()

    with patch(
        "utils.claude_interface.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["claude"], timeout=600),
    ):
        with patch("utils.claude_interface.os.getcwd", return_value="/original"):
            with patch("utils.claude_interface.os.chdir") as chdir_mock:
                interface.execute_code_cli("fix bug", "/tmp/repo")

    observed = [call.args for call in chdir_mock.call_args_list]
    expected = [("/tmp/repo",), ("/original",)]

    assert observed == expected


def test_execute_code_cli_returns_exception_result():
    interface = make_interface()

    with patch("utils.claude_interface.subprocess.run", side_effect=ValueError("boom")):
        with patch("utils.claude_interface.os.getcwd", return_value="/original"):
            with patch("utils.claude_interface.os.chdir"):
                result = interface.execute_code_cli("fix bug", "/tmp/repo")

    observed = result
    expected = {
        "success": False,
        "stdout": "",
        "stderr": "boom",
        "returncode": -1,
    }

    assert observed == expected


def test_extract_file_changes_returns_empty_list():
    interface = make_interface()

    observed = interface.extract_file_changes("some response")
    expected = []

    assert observed == expected
