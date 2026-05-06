"""Local leaderboard storage for completed matches."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime

from .paths import BASE_DIR


@dataclass
class LeaderboardEntry:
    """One saved leaderboard result."""

    player: str
    result: str
    avg_wpm: int
    max_wpm: int
    avg_acc: float
    chars: int
    mistakes: int
    roulettes: int
    created_at: str


class LeaderboardStore:
    """Persist and rank match results in a JSON file."""

    def __init__(self, path=None):
        # Prepare the leaderboard path.
        self.path = path or BASE_DIR / "data" / "leaderboard.json"

    def load(self):
        # Load all saved leaderboard rows.
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

    def save_entry(self, entry):
        # Append a new result to the leaderboard file.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rows = self.load()
        rows.append(asdict(entry))
        self.path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def top_entries(self, limit=8):
        # Return leaderboard rows sorted by result, speed, and accuracy.
        rows = self.load()
        rows.sort(
            key=lambda row: (
                1 if row.get("result") == "Won" else 0,
                row.get("avg_wpm", 0),
                row.get("avg_acc", 0),
                row.get("chars", 0),
            ),
            reverse=True,
        )
        return rows[:limit]


def create_entry(player, result, avg_wpm, max_wpm, avg_acc, chars, mistakes, roulettes):
    # Build a leaderboard entry from match stats.
    return LeaderboardEntry(
        player=player or "Player",
        result=result,
        avg_wpm=avg_wpm,
        max_wpm=max_wpm,
        avg_acc=avg_acc,
        chars=chars,
        mistakes=mistakes,
        roulettes=roulettes,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

