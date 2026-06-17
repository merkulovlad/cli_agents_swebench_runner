from datetime import datetime


def log_status(message: str) -> None:
    """Print a timestamped status line immediately."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)
