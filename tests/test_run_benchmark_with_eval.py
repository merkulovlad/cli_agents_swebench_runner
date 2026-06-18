import json

import jsonlines

from run_benchmark_with_eval import EnhancedBenchmarkRunner


def test_log_result_aggregates_task_times(tmp_path):
    prediction_file = tmp_path / "predictions.jsonl"
    with jsonlines.open(prediction_file, mode="w") as writer:
        writer.write({"instance_id": "one", "task_time_seconds": 10.0})
        writer.write({"instance_id": "two", "task_time_seconds": 20.0})
        writer.write({"instance_id": "old-result-without-timing"})

    runner = EnhancedBenchmarkRunner.__new__(EnhancedBenchmarkRunner)
    runner.log_file = tmp_path / "benchmark_scores.log"
    runner.model = None
    runner.backend = "local"

    runner.log_result(
        "dataset",
        3,
        100.0,
        None,
        40.0,
        0,
        prediction_file,
        evaluation_status="skipped",
    )

    saved = json.loads(runner.log_file.read_text())
    assert saved["total_task_time"] == 30.0
    assert saved["average_task_time"] == 15.0
