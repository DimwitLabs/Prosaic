"""Writing metrics tracking."""

import json
from datetime import datetime
from pathlib import Path

from prosaic.utils import read_text, write_text


class MetricsTracker:
    """Track writing metrics over time."""

    def __init__(self, workspace: Path) -> None:
        """Initialize metrics tracker."""
        self.workspace = workspace
        self.metrics_file = workspace / "metrics.json"
        self.metrics = self._load()
        self._session_start = datetime.now().isoformat()
        self._baseline_words = 0

    def _load(self) -> dict:
        """Load metrics from file."""
        default = {"daily": {}, "sessions": []}
        if self.metrics_file.exists():
            try:
                data = json.loads(read_text(self.metrics_file))
                if isinstance(data, dict):
                    if "daily" not in data:
                        data["daily"] = {}
                    if "sessions" not in data:
                        data["sessions"] = []
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return default

    def _save(self) -> None:
        """Save metrics to file."""
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        write_text(self.metrics_file, json.dumps(self.metrics, indent=2))

    def set_baseline(self, word_count: int) -> None:
        """Set baseline word count for current session."""
        self._baseline_words = word_count

    def record_save(self, word_count: int, file_path: Path) -> None:
        """Record a save event with current word count."""
        today = datetime.now().strftime("%Y-%m-%d")
        words_written = max(0, word_count - self._baseline_words)

        if today not in self.metrics["daily"]:
            self.metrics["daily"][today] = {"words": 0, "saves": 0, "files": []}

        self.metrics["daily"][today]["words"] += words_written
        self.metrics["daily"][today]["saves"] += 1

        file_str = str(file_path)
        if file_str not in self.metrics["daily"][today]["files"]:
            self.metrics["daily"][today]["files"].append(file_str)

        self._baseline_words = word_count
        self._save()

    def get_today_stats(self) -> dict:
        """Get statistics for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.metrics["daily"].get(
            today, {"words": 0, "saves": 0, "files": []}
        )

    def get_week_stats(self) -> dict:
        """Get statistics for the past 7 days."""
        total_words = 0
        total_saves = 0
        all_files = set()

        for key, data in self.metrics["daily"].items():
            try:
                date = datetime.strptime(key, "%Y-%m-%d")
                if (datetime.now() - date).days < 7:
                    total_words += data.get("words", 0)
                    total_saves += data.get("saves", 0)
                    all_files.update(data.get("files", []))
            except ValueError:
                continue

        return {
            "words": total_words,
            "saves": total_saves,
            "files": list(all_files),
        }
