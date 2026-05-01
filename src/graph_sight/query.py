"""Query engine — find relevant context for AI agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ContextResult:
    root: str
    node_id: str
    name: str
    type: str
    trust: float
    distance: int
    snippet: str = ""


class QueryEngine:
    """Rank and assemble context from the code graph."""

    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def query(self, text: str, depth: int = 2, min_trust: float = 0.0) -> list[ContextResult]:
        rows = self.graph.query_context(text, depth=depth, min_trust=min_trust)
        results: list[ContextResult] = []
        seen: set[str] = set()
        for row in rows:
            nid = row.get("node_id", "")
            if nid in seen:
                continue
            seen.add(nid)
            trust = row.get("trust", 0.5) or 0.5
            if trust < min_trust:
                continue
            results.append(ContextResult(
                root=row.get("root", ""),
                node_id=nid,
                name=row.get("name", ""),
                type=row.get("type", ""),
                trust=trust,
                distance=row.get("dist", 1),
            ))
        # Sort by distance first, then trust desc
        results.sort(key=lambda r: (r.distance, -r.trust))
        return results

    def to_markdown(self, results: list[ContextResult], query: str) -> str:
        lines = [
            f"# Context for: {query}",
            "",
            f"Found {len(results)} relevant nodes.",
            "",
        ]
        for r in results[:20]:
            trust_badge = "🟢" if r.trust >= 0.7 else "🟡" if r.trust >= 0.4 else "🔴"
            lines.append(f"## {r.name} ({r.type}) {trust_badge} trust={r.trust}")
            lines.append(f"- **File:** `{r.node_id}`")
            lines.append(f"- **Distance from query:** {r.distance} hop(s)")
            lines.append("")
        return "\n".join(lines)
