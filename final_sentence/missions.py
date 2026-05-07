"""Persistent mission system for Final Sentence."""

import json

from .paths import BASE_DIR


MISSION_DEFS = [
    {
        "id": "first_finish",
        "title": "First Finish",
        "description": "Complete any run once.",
        "target": 1,
        "metric": "finished_runs",
    },
    {
        "id": "first_win",
        "title": "Live to Tell",
        "description": "Win a full run.",
        "target": 1,
        "metric": "wins",
    },
    {
        "id": "combo_20",
        "title": "Steady Hands",
        "description": "Reach a combo of 20.",
        "target": 20,
        "metric": "best_combo",
    },
    {
        "id": "completion_80",
        "title": "Almost There",
        "description": "Reach 80% article completion in a run.",
        "target": 80,
        "metric": "best_completion",
    },
    {
        "id": "roulette_survivor",
        "title": "Lucky Devil",
        "description": "Survive roulette three times in total.",
        "target": 3,
        "metric": "roulette_survivals",
    },
]


class MissionStore:
    """Persist mission progress and evaluate completed runs."""

    def __init__(self, path=None):
        # Prepare the mission data file path.
        self.path = path or BASE_DIR / "data" / "missions.json"

    def load(self):
        # Load mission progress or create defaults.
        defaults = {
            "finished_runs": 0,
            "wins": 0,
            "best_combo": 0,
            "best_completion": 0.0,
            "roulette_survivals": 0,
        }
        if not self.path.exists():
            return defaults
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults
        defaults.update(raw)
        return defaults

    def save(self, data):
        # Save mission progress to disk.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def update_from_run(self, summary):
        # Merge one finished run into mission progress.
        data = self.load()
        data["finished_runs"] += 1
        if summary.get("result") == "Won":
            data["wins"] += 1
        data["best_combo"] = max(data["best_combo"], summary.get("best_combo", 0))
        data["best_completion"] = max(data["best_completion"], summary.get("completion_rate", 0.0))
        data["roulette_survivals"] += max(0, summary.get("roulette_survivals", 0))
        self.save(data)
        return data

    def mission_rows(self):
        # Build display rows for the mission menu.
        data = self.load()
        rows = []
        for mission in MISSION_DEFS:
            progress = data.get(mission["metric"], 0)
            target = mission["target"]
            clamped = min(progress, target)
            complete = progress >= target
            rows.append(
                {
                    "id": mission["id"],
                    "title": mission["title"],
                    "description": mission["description"],
                    "progress": progress,
                    "target": target,
                    "display_progress": clamped,
                    "complete": complete,
                }
            )
        return rows
