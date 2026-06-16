import os
import sys
from unittest.mock import ANY, Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.gemini_interface import GeminiCodeInterface


def make_interface():
    return GeminiCodeInterface.__new__(GeminiCodeInterface)


def test_build_env_maps_api_alias_to_gemini_api_key(monkeypatch):
    interface = make_interface()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("API", raising=False)
    monkeypatch.setenv("api", "test-key")

    env = interface._build_env()

    observed = {
        "api": env.get("api"),
        "gemini_api_key": env.get("GEMINI_API_KEY"),
    }
    expected = {
        "api": "test-key",
        "gemini_api_key": "test-key",
    }

    assert observed == expected


def test_build_env_does_not_override_existing_gemini_api_key(monkeypatch):
    interface = make_interface()
    monkeypatch.setenv("api", "alias-key")
    monkeypatch.setenv("GEMINI_API_KEY", "real-key")

    env = interface._build_env()

    observed = {
        "api": env.get("api"),
        "gemini_api_key": env.get("GEMINI_API_KEY"),
    }
    expected = {
        "api": "alias-key",
        "gemini_api_key": "real-key",
    }

    assert observed == expected


def test_build_env_does_not_add_gemini_key_when_google_api_key_exists(monkeypatch):
    interface = make_interface()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("api", "alias-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")

    env = interface._build_env()

    observed = {
        "gemini_api_key": env.get("GEMINI_API_KEY"),
        "google_api_key": env.get("GOOGLE_API_KEY"),
    }
    expected = {
        "gemini_api_key": None,
        "google_api_key": "google-key",
    }

    assert observed == expected


def test_execute_code_cli_passes_env_to_gemini():
    interface = make_interface()
    completed = Mock(returncode=0, stdout="done", stderr="")

    with patch("utils.gemini_interface.subprocess.run", return_value=completed) as run_mock:
        with patch("utils.gemini_interface.os.getcwd", return_value="/original"):
            with patch("utils.gemini_interface.os.chdir"):
                interface.execute_code_cli("fix bug", "/tmp/repo", model="gemini-pro")

    observed = {
        "run_args": run_mock.call_args.args,
        "run_kwargs": run_mock.call_args.kwargs,
    }
    expected = {
        "run_args": (["gemini", "--model", "gemini-pro"],),
        "run_kwargs": {
            "input": "fix bug",
            "capture_output": True,
            "text": True,
            "timeout": 600,
            "env": ANY,
        },
    }

    assert observed == expected
