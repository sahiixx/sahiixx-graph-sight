"""Trust scoring for code nodes."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TrustFactors:
    coverage: float = 0.0
    churn: float = 0.0
    author_trust: float = 0.5
    reviewed: float = 0.0
    age: float = 0.5
    complexity: float = 0.5


class TrustScorer:
    """Compute trust scores for code nodes."""

    WEIGHTS = {
        "coverage": 0.30,
        "churn": 0.20,
        "author_trust": 0.15,
        "reviewed": 0.15,
        "age": 0.10,
        "complexity": 0.10,
    }

    def __init__(self, root: Path) -> None:
        self.root = root

    def score(self, node_id: str, file: str, complexity: int = 0) -> float:
        factors = TrustFactors()
        path = self.root / file

        # Coverage: placeholder — would integrate with coverage.py output
        factors.coverage = self._coverage_score(path)

        # Churn: git log count in last 90 days
        factors.churn = self._churn_score(path)

        # Age: newer = lower trust
        factors.age = self._age_score(path)

        # Complexity: higher = lower trust
        factors.complexity = max(0.0, 1.0 - (complexity / 20.0))

        # Weighted sum
        total = 0.0
        for key, weight in self.WEIGHTS.items():
            total += getattr(factors, key) * weight
        return round(min(max(total, 0.0), 1.0), 3)

    def _coverage_score(self, path: Path) -> float:
        # TODO: integrate with coverage.py XML output
        return 0.5

    def _churn_score(self, path: Path) -> float:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.root), "log", "--since=90 days ago", "--oneline", "--", str(path)],
                capture_output=True, text=True, timeout=10,
            )
            commits = len([l for l in result.stdout.splitlines() if l.strip()])
            # More commits = lower trust (unstable)
            return max(0.0, 1.0 - (commits / 20.0))
        except Exception:
            return 0.5

    def _age_score(self, path: Path) -> float:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.root), "log", "--follow", "--format=%ct", "--", str(path)],
                capture_output=True, text=True, timeout=10,
            )
            timestamps = [int(l) for l in result.stdout.splitlines() if l.strip().isdigit()]
            if not timestamps:
                return 0.5
            import time
            oldest = min(timestamps)
            age_days = (time.time() - oldest) / 86400
            # Older = higher trust (0.2 to 1.0)
            return min(1.0, max(0.2, age_days / 365.0))
        except Exception:
            return 0.5

    def score_all(self, nodes: list[Any]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for node in nodes:
            scores[node.id] = self.score(node.id, getattr(node, "file", ""), getattr(node, "complexity", 0))
        return scores
