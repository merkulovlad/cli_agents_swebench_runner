import os
import sys
from unittest.mock import ANY, Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.codex_interface import CodexCodeInterface


def make_interface():
    return CodexCodeInterface.__new__(CodexCodeInterface)


def test_build_env_maps_api_alias_to_openai_api_key(monkeypatch):
    interface = make_interface()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("API", raising=False)
    monkeypatch.setenv("api", "test-key")

    env = interface._build_env()

    observed = {
        "api": env.get("api"),
        "openai_api_key": env.get("OPENAI_API_KEY"),
    }
    expected = {
        "api": "test-key",
        "openai_api_key": "test-key",
    }

    assert observed == expected


def test_build_env_does_not_override_existing_openai_api_key(monkeypatch):
    interface = make_interface()
    monkeypatch.setenv("api", "alias-key")
    monkeypatch.setenv("OPENAI_API_KEY", "real-key")

    env = interface._build_env()

    observed = {
        "api": env.get("api"),
        "openai_api_key": env.get("OPENAI_API_KEY"),
    }
    expected = {
        "api": "alias-key",
        "openai_api_key": "real-key",
    }

    assert observed == expected


def test_execute_code_cli_passes_env_to_codex():
    interface = make_interface()
    completed = Mock(returncode=0, stdout="done", stderr="")

    with patch("utils.codex_interface.subprocess.run", return_value=completed) as run_mock:
        with patch("utils.codex_interface.os.getcwd", return_value="/original"):
            with patch("utils.codex_interface.os.chdir"):
                interface.execute_code_cli("fix bug", "/tmp/repo", model="gpt-5")

    observed = {
        "run_args": run_mock.call_args.args,
        "run_kwargs": run_mock.call_args.kwargs,
    }
    expected = {
        "run_args": (["codex", "--model", "gpt-5"],),
        "run_kwargs": {
            "input": "fix bug",
            "capture_output": True,
            "text": True,
            "timeout": 600,
            "env": ANY,
        },
    }

    assert observed == expected
