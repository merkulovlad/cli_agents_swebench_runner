import json
import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code_swe_agent import CodeSWEAgent


def test_save_result_uses_backend_neutral_model_output_key(tmp_path):
    agent = CodeSWEAgent.__new__(CodeSWEAgent)
    agent.results_dir = tmp_path

    result = {
        "success": True,
        "stdout": "raw model output",
        "stderr": "",
        "returncode": 0,
    }

    agent._save_result("django__django-11133", result, "diff --git a/file.py b/file.py")

    saved_files = list(tmp_path.glob("django__django-11133_*.json"))
    with open(saved_files[0]) as f:
        saved = json.load(f)

    observed = {
        "file_count": len(saved_files),
        "model_output": saved.get("model_output"),
        "claude_output": saved.get("claude_output"),
        "extracted_patch": saved.get("extracted_patch"),
    }
    expected = {
        "file_count": 1,
        "model_output": result,
        "claude_output": None,
        "extracted_patch": "diff --git a/file.py b/file.py",
    }

    assert observed == expected


def test_save_predictions_requires_initialized_prediction_file():
    agent = CodeSWEAgent.__new__(CodeSWEAgent)
    agent.pred_file = None

    try:
        agent._save_predictions({"instance_id": "test"})
    except ValueError as exc:
        error = str(exc)
    else:
        error = None

    observed = error
    expected = "Prediction timestamp not initialized. Call run_on_dataset first."

    assert observed == expected


def test_save_predictions_appends_jsonl_record(tmp_path):
    agent = CodeSWEAgent.__new__(CodeSWEAgent)
    agent.pred_file = tmp_path / "predictions.jsonl"

    prediction = {
        "instance_id": "django__django-11133",
        "model": "claude-code",
        "prediction": "patch",
    }

    agent._save_predictions(prediction)

    with open(agent.pred_file) as f:
        saved = [json.loads(line) for line in f]

    observed = saved
    expected = [prediction]

    assert observed == expected


def test_process_instance_returns_setup_error_when_repository_setup_fails():
    agent = CodeSWEAgent.__new__(CodeSWEAgent)
    agent.backend = "claude"
    agent.setup_repository = Mock(return_value=None)

    result = agent.process_instance({"instance_id": "django__django-11133"})

    observed = result
    expected = {
        "instance_id": "django__django-11133",
        "model": "claude-code",
        "prediction": "",
        "error": "Failed to set up repository",
    }

    assert observed == expected


def test_process_instance_returns_execution_error_and_cleans_repo(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    agent = CodeSWEAgent.__new__(CodeSWEAgent)
    agent.backend = "codex"
    agent.model = "codex-model"
    agent.model_alias = "codex-alias"
    agent.setup_repository = Mock(return_value=str(repo_path))
    agent.prompt_formatter = Mock()
    agent.prompt_formatter.format_for_cli.return_value = "prompt"
    agent.interface = Mock()
    agent.interface.execute_code_cli.return_value = {
        "success": False,
        "stdout": "",
        "stderr": "boom",
        "returncode": 1,
    }
    agent._copy_agent_sessions = Mock()

    with patch("code_swe_agent.os.getcwd", return_value="/original"):
        with patch("code_swe_agent.os.chdir") as chdir_mock:
            with patch("code_swe_agent.subprocess.run"):
                result = agent.process_instance({"instance_id": "django__django-11133"})

    observed = {
        "result": result,
        "repo_exists": repo_path.exists(),
        "copy_sessions_call": agent._copy_agent_sessions.call_args.args,
        "chdir_calls": [call.args for call in chdir_mock.call_args_list],
    }
    expected = {
        "result": {
            "instance_id": "django__django-11133",
            "model": "codex-alias",
            "prediction": "",
            "error": "Execution failed: boom",
        },
        "repo_exists": False,
        "copy_sessions_call": ("django__django-11133", str(repo_path)),
        "chdir_calls": [(str(repo_path),), ("/original",), ("/original",)],
    }

    assert observed == expected


def test_process_instance_formats_valid_prediction_and_saves_result(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    agent = CodeSWEAgent.__new__(CodeSWEAgent)
    agent.backend = "claude"
    agent.model = "claude-model"
    agent.model_alias = "sonnet"
    agent.setup_repository = Mock(return_value=str(repo_path))
    agent.prompt_formatter = Mock()
    agent.prompt_formatter.format_for_cli.return_value = "prompt"
    agent.interface = Mock()
    agent.interface.execute_code_cli.return_value = {
        "success": True,
        "stdout": "raw output",
        "stderr": "",
        "returncode": 0,
    }
    agent.patch_extractor = Mock()
    agent.patch_extractor.extract_from_cli_output.return_value = "valid patch"
    agent.patch_extractor.validate_patch.return_value = (True, None)
    agent.patch_extractor.format_for_swebench.return_value = {
        "instance_id": "django__django-11133",
        "model": "sonnet",
        "prediction": "valid patch",
    }
    agent._save_result = Mock()
    agent._copy_agent_sessions = Mock()

    with patch("code_swe_agent.os.getcwd", return_value="/original"):
        with patch("code_swe_agent.os.chdir") as chdir_mock:
            with patch("code_swe_agent.subprocess.run") as run_mock:
                result = agent.process_instance({"instance_id": "django__django-11133"})

    observed = {
        "result": result,
        "prompt_call": agent.prompt_formatter.format_for_cli.call_args.args,
        "execute_call": agent.interface.execute_code_cli.call_args.args,
        "extract_call": agent.patch_extractor.extract_from_cli_output.call_args.args,
        "format_call": agent.patch_extractor.format_for_swebench.call_args.args,
        "save_call": agent._save_result.call_args.args,
        "git_calls": [call.args for call in run_mock.call_args_list],
        "repo_exists": repo_path.exists(),
        "copy_sessions_call": agent._copy_agent_sessions.call_args.args,
        "chdir_calls": [call.args for call in chdir_mock.call_args_list],
    }
    expected = {
        "result": {
            "instance_id": "django__django-11133",
            "model": "sonnet",
            "prediction": "valid patch",
        },
        "prompt_call": ({"instance_id": "django__django-11133"},),
        "execute_call": ("prompt", str(repo_path), "claude-model"),
        "extract_call": ("raw output", str(repo_path)),
        "format_call": ("valid patch", "django__django-11133", "sonnet"),
        "save_call": (
            "django__django-11133",
            {
                "success": True,
                "stdout": "raw output",
                "stderr": "",
                "returncode": 0,
            },
            "valid patch",
        ),
        "git_calls": [
            (["git", "add", "-A"],),
            (["git", "stash"],),
        ],
        "repo_exists": False,
        "copy_sessions_call": ("django__django-11133", str(repo_path)),
        "chdir_calls": [(str(repo_path),), ("/original",)],
    }

    assert observed == expected


def test_copy_agent_sessions_preserves_logs(tmp_path):
    repo_path = tmp_path / "repo"
    sessions_path = repo_path / ".supercode" / "sessions"
    sessions_path.mkdir(parents=True)
    (sessions_path / "trace.jsonl").write_text('{"event": "done"}\n')
    (sessions_path / "transcript.json").write_text('{"result": "ok"}\n')

    agent = CodeSWEAgent.__new__(CodeSWEAgent)
    agent.results_dir = tmp_path / "results"

    agent._copy_agent_sessions("django__django-11133", str(repo_path))

    saved_sessions = agent.results_dir / "django__django-11133" / "sessions"
    assert (saved_sessions / "trace.jsonl").read_text() == '{"event": "done"}\n'
    assert (saved_sessions / "transcript.json").read_text() == '{"result": "ok"}\n'


def test_run_on_instance_finds_matching_instance_and_processes_it():
    agent = CodeSWEAgent.__new__(CodeSWEAgent)
    agent.process_instance = Mock(return_value={"instance_id": "target"})
    dataset = [
        {"instance_id": "first"},
        {"instance_id": "target"},
    ]

    with patch("code_swe_agent.load_dataset", return_value=dataset) as load_dataset_mock:
        result = agent.run_on_instance("target", "dataset-name")

    observed = {
        "result": result,
        "load_dataset_call": load_dataset_mock.call_args.args,
        "process_call": agent.process_instance.call_args.args,
    }
    expected = {
        "result": {"instance_id": "target"},
        "load_dataset_call": ("dataset-name",),
        "process_call": ({"instance_id": "target"},),
    }

    assert observed == expected


def test_run_on_instance_raises_when_instance_is_missing():
    agent = CodeSWEAgent.__new__(CodeSWEAgent)
    dataset = [{"instance_id": "first"}]

    with patch("code_swe_agent.load_dataset", return_value=dataset):
        try:
            agent.run_on_instance("missing", "dataset-name")
        except ValueError as exc:
            error = str(exc)
        else:
            error = None

    observed = error
    expected = "Instance missing not found in dataset"

    assert observed == expected
