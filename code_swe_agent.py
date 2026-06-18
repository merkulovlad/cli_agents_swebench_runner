#!/usr/bin/env python3
"""
SWE-bench agent capable of using Claude Code or Codex backends.
"""

import argparse
import json
import os
import sys
import subprocess
import tempfile
import shutil
import time
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from datasets import load_dataset
from tqdm import tqdm
import jsonlines

from utils.claude_interface import ClaudeCodeInterface
from utils.codex_interface import CodexCodeInterface
from utils.gemini_interface import GeminiCodeInterface
from utils.local_interface import LocalAgentInterface
from utils.prompt_formatter import PromptFormatter
from utils.patch_extractor import PatchExtractor
from utils.model_registry import get_model_name
from utils.dataset_registry import resolve_dataset_name
from utils.status import log_status


DEFAULT_BACKEND = os.environ.get("CODE_SWE_BACKEND", "claude")


class CodeSWEAgent:
    """Main agent for running SWE-bench using different code models."""

    def __init__(self, prompt_template: Optional[str] = None,
                 model: Optional[str] = None,
                 backend: str = DEFAULT_BACKEND,
                 agent_command: Optional[str] = None,
                 agent_timeout: int = 600):
        self.backend = (backend or DEFAULT_BACKEND).lower()
        if self.backend == "codex":
            self.interface = CodexCodeInterface()
        elif self.backend == "gemini":
            self.interface = GeminiCodeInterface()
        elif self.backend == "local":
            self.interface = LocalAgentInterface(agent_command, agent_timeout)
        else:
            self.backend = "claude"
            self.interface = ClaudeCodeInterface()

        self.prompt_formatter = PromptFormatter(prompt_template)
        self.patch_extractor = PatchExtractor()
        self.base_dir = Path.cwd()
        self.results_dir = self.base_dir / "results"
        self.predictions_dir = self.base_dir / "predictions"

        # Resolve model name from alias
        self.model = get_model_name(model, self.backend) if model and self.backend != "local" else model
        self.model_alias = model  # Keep original alias for logging

        # Create directories if they don't exist
        self.results_dir.mkdir(exist_ok=True)
        self.predictions_dir.mkdir(exist_ok=True)
        self.pred_timestamp: Optional[str] = None
        self.pred_file: Optional[Path] = None

    def setup_repository(self, instance: Dict) -> Optional[str]:
        """Set up a repository for testing."""
        instance_id = instance["instance_id"]
        repo_name = instance["repo"]
        base_commit = instance["base_commit"]

        # Create temporary directory for this instance (cross-platform)
        temp_dir = Path(tempfile.gettempdir()) / f"swe_bench_{instance_id}"

        try:
            # Remove if exists
            if temp_dir.exists():
                log_status(f"{instance_id}: removing previous temp checkout at {temp_dir}")
                shutil.rmtree(temp_dir)

            # Save current directory
            original_dir = Path.cwd()
            
            # Clone repository
            log_status(f"{instance_id}: cloning {repo_name} to {temp_dir}")
            clone_url = f"https://github.com/{repo_name}.git"
            
            result = subprocess.run(
                ["git", "clone", clone_url, str(temp_dir)],
                capture_output=True,
                text=True,
                cwd=str(original_dir)  # Ensure we're in a valid directory
            )
            
            if result.returncode != 0:
                log_status(f"{instance_id}: failed to clone repository: {result.stderr}")
                return None
                
            # Checkout base commit
            os.chdir(temp_dir)
            log_status(f"{instance_id}: checking out base commit {base_commit[:12]}")
            result = subprocess.run(
                ["git", "checkout", base_commit],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                log_status(f"{instance_id}: failed to checkout commit: {result.stderr}")
                os.chdir(str(original_dir))  # Return to original directory
                return None

            os.chdir(str(original_dir))  # Return to original directory
            return str(temp_dir)
            
        except Exception as e:
            log_status(f"{instance_id}: error setting up repository: {e}")
            # Try to return to original directory if possible
            try:
                os.chdir(str(original_dir))
            except Exception as chdir_error:
                log_status(f"{instance_id}: warning: failed to return to original directory: {chdir_error}")
            return None
            
    def process_instance(self, instance: Dict) -> Dict:
        """Process a single SWE-bench instance."""
        instance_id = instance["instance_id"]
        log_status(f"Processing {instance_id}")

        original_dir = os.getcwd()

        log_status(f"{instance_id}: preparing repository")
        repo_path = self.setup_repository(instance)
        if not repo_path:
            return {
                "instance_id": instance_id,
                "model": f"{self.backend}-code",
                "prediction": "",
                "error": "Failed to set up repository",
            }

        task_started = time.perf_counter()
        try:
            log_status(f"{instance_id}: formatting prompt")
            prompt = self.prompt_formatter.format_for_cli(instance)

            os.chdir(repo_path)
            log_status(f"{instance_id}: resetting workspace before model run")
            subprocess.run(["git", "add", "-A"], capture_output=True)
            subprocess.run(["git", "stash"], capture_output=True)

            model_info = f" with model {self.model_alias}" if self.model else ""
            log_status(f"{instance_id}: sending prompt to {self.backend.title()} Code{model_info}")
            result = self.interface.execute_code_cli(prompt, repo_path, self.model)

            if not result["success"]:
                log_status(f"{instance_id}: {self.backend.title()} Code execution failed: {result['stderr']}")
                os.chdir(original_dir)
                return {
                    "instance_id": instance_id,
                    "model": self.model_alias or f"{self.backend}-code",
                    "prediction": "",
                    "error": f"Execution failed: {result['stderr']}",
                    "task_time_seconds": time.perf_counter() - task_started,
                }

            log_status(f"{instance_id}: model response received; extracting patch")
            patch = self.patch_extractor.extract_from_cli_output(result["stdout"], repo_path)

            is_valid, error = self.patch_extractor.validate_patch(patch)
            if not is_valid:
                log_status(f"{instance_id}: invalid patch: {error}")
                patch = ""
            else:
                log_status(f"{instance_id}: patch extracted successfully ({len(patch)} chars)")

            prediction = self.patch_extractor.format_for_swebench(
                patch, instance_id, self.model_alias or f"{self.backend}-code"
            )
            task_time = time.perf_counter() - task_started
            prediction["task_time_seconds"] = task_time

            self._save_result(instance_id, result, patch, task_time)
            log_status(f"{instance_id}: prediction saved")

            return prediction

        except Exception as e:
            import traceback
            print(f"Error processing instance: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return {
                "instance_id": instance_id,
                "model": self.model_alias or f"{self.backend}-code",
                "prediction": "",
                "error": str(e),
                "task_time_seconds": time.perf_counter() - task_started,
            }
        finally:
            try:
                os.chdir(original_dir)
            except Exception as e:
                log_status(f"{instance_id}: warning: could not restore directory: {e}")

            if repo_path and os.path.exists(repo_path):
                self._copy_agent_sessions(instance_id, repo_path)
                log_status(f"{instance_id}: cleaning up temp checkout")
                shutil.rmtree(repo_path)

    def _copy_agent_sessions(self, instance_id: str, repo_path: str) -> None:
        """Preserve session logs from hidden agent directories before cleanup."""
        session_dirs = [
            path for path in Path(repo_path).glob(".*/sessions")
            if path.is_dir()
        ]
        if not session_dirs:
            return

        destination = self.results_dir / instance_id / "sessions"
        destination.mkdir(parents=True, exist_ok=True)
        for session_dir in session_dirs:
            shutil.copytree(session_dir, destination, dirs_exist_ok=True)
        log_status(f"{instance_id}: copied agent sessions to {destination}")

    def _save_result(
        self, instance_id: str, result: Dict, patch: str,
        task_time_seconds: Optional[float] = None,
    ):
        """Save detailed results for debugging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"{instance_id}_{timestamp}.json"
        
        with open(result_file, 'w') as f:
            json.dump({
                "instance_id": instance_id,
                "timestamp": timestamp,
                "task_time_seconds": task_time_seconds,
                "model_output": result,
                "extracted_patch": patch
            }, f, indent=2)
            
    def run_on_dataset(self, dataset_name: str, split: str = "test",
                      limit: Optional[int] = None) -> List[Dict]:
        """Run on a full dataset."""
        dataset_name = resolve_dataset_name(dataset_name)
        log_status(f"Loading dataset {dataset_name} split={split}")
        dataset = load_dataset(dataset_name, split=split)
        log_status(f"Loaded {len(dataset)} instances from {dataset_name}")
        
        if limit:
            selected = min(limit, len(dataset))
            log_status(f"Selecting first {selected} instances")
            dataset = dataset.select(range(selected))
            
        self.pred_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.pred_file = self.predictions_dir / f"predictions_{self.pred_timestamp}.jsonl"
        if self.pred_file.exists():
            self.pred_file.unlink()
        json_file = self.predictions_dir / f"predictions_{self.pred_timestamp}.json"
        if json_file.exists():
            json_file.unlink()

        predictions: List[Dict] = []

        total = len(dataset)
        log_status(f"Writing incremental predictions to {self.pred_file}")
        for index, instance in enumerate(tqdm(dataset, desc="Processing instances"), start=1):
            log_status(f"Starting instance {index}/{total}: {instance['instance_id']}")
            prediction = self.process_instance(instance)
            predictions.append(prediction)

            # Save prediction incrementally
            self._save_predictions(prediction)
            log_status(f"Finished instance {index}/{total}: {instance['instance_id']}")

        with open(json_file, 'w') as f:
            json.dump(predictions, f, indent=2)

        log_status(f"Saved predictions to {self.pred_file}")
        return predictions
    
    def run_on_instance(self, instance_id: str, dataset_name: str = "princeton-nlp/SWE-bench_Lite") -> Dict:
        """Run on a single instance by ID."""
        dataset_name = resolve_dataset_name(dataset_name)
        dataset = load_dataset(dataset_name, split="test")
        
        # Find the instance
        instance = None
        for item in dataset:
            if item["instance_id"] == instance_id:
                instance = item
                break
                
        if not instance:
            raise ValueError(f"Instance {instance_id} not found in dataset")
            
        return self.process_instance(instance)
    
    def _save_predictions(self, prediction: Dict):
        """Append a single prediction to the jsonl file."""
        if not self.pred_file:
            raise ValueError("Prediction timestamp not initialized. Call run_on_dataset first.")

        with jsonlines.open(self.pred_file, mode='a') as writer:
            writer.write(prediction)


def main():
    parser = argparse.ArgumentParser(description="Run code models on SWE-bench")
    parser.add_argument("--dataset_name", type=str,
                       default="lite",
                       help="Dataset alias or Hugging Face ID")
    parser.add_argument("--instance_id", type=str,
                       help="Run on a specific instance ID")
    parser.add_argument("--limit", type=int,
                       help="Limit number of instances to process")
    parser.add_argument("--prompt_template", type=str,
                       help="Path to custom prompt template")
    parser.add_argument("--model", type=str,
                       help="Model to use (e.g., opus-4.1, codex-4.2, or any name)")
    parser.add_argument("--backend", type=str, choices=["claude", "codex", "gemini", "local"],
                       help="Code model backend to use")
    parser.add_argument("--agent_command", "--agent-command", type=str,
                       help="Local agent command to run when --backend local")
    parser.add_argument("--agent_timeout", "--agent-timeout", type=int, default=600,
                       help="Local agent timeout in seconds (default: 600)")
    
    args = parser.parse_args()
    
    backend = args.backend or DEFAULT_BACKEND
    if backend == "local" and not args.agent_command:
        print("Error: --agent-command is required when using --backend local")
        sys.exit(1)

    # Check if selected CLI is available
    if backend == "local":
        cli_cmd = None
    elif backend == "codex":
        cli_cmd = "codex"
    elif backend == "gemini":
        cli_cmd = "gemini"
    else:
        cli_cmd = "claude"

    if cli_cmd:
        try:
            result = subprocess.run([cli_cmd, "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error: {cli_cmd} CLI not found. Please ensure '{cli_cmd}' is installed and in PATH")
                sys.exit(1)
        except FileNotFoundError:
            print(f"Error: {cli_cmd} CLI not found. Please ensure '{cli_cmd}' is installed and in PATH")
            sys.exit(1)

    agent = CodeSWEAgent(
        args.prompt_template,
        args.model,
        backend,
        agent_command=args.agent_command,
        agent_timeout=args.agent_timeout,
    )
    
    # Run on specific instance or dataset
    if args.instance_id:
        print(f"Running on instance: {args.instance_id}")
        prediction = agent.run_on_instance(args.instance_id, args.dataset_name)
        print(f"Prediction saved: {prediction}")
    else:
        print(f"Running on dataset: {args.dataset_name}")
        predictions = agent.run_on_dataset(args.dataset_name, limit=args.limit)
        print(f"Processed {len(predictions)} instances")


if __name__ == "__main__":
    main()
