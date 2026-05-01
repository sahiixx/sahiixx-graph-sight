"""CLI for graph-sight."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from graph_sight.graph import Neo4jGraph
from graph_sight.parser import CodebaseParser
from graph_sight.query import QueryEngine
from graph_sight.trust import TrustScorer

app = typer.Typer(help="graph-sight — Relationship-aware codebase context for AI agents")
console = Console()


@app.command()
def index(
    path: str = typer.Argument(..., help="Path to codebase root"),
    neo4j_uri: str = typer.Option("bolt://localhost:7687", "--neo4j", help="Neo4j Bolt URI"),
    neo4j_user: str = typer.Option("neo4j", "--user", help="Neo4j user"),
    neo4j_password: str = typer.Option("password", "--password", help="Neo4j password"),
) -> None:
    """Index a codebase into Neo4j."""
    root = Path(path).resolve()
    console.print(f"[bold blue]Indexing {root}...[/bold blue]")

    parser = CodebaseParser(root)
    nodes, edges = parser.parse()
    console.print(f"Parsed {len(nodes)} nodes, {len(edges)} edges")

    scorer = TrustScorer(root)
    scores = scorer.score_all(nodes)
    for node in nodes:
        if node.id in scores:
            # We can't mutate dataclass fields directly if frozen; but they're not frozen
            # However CodeNode doesn't have trust_score field. Let's add it dynamically
            pass  # We'll handle this in graph.py by passing scores separately

    with Neo4jGraph(neo4j_uri, neo4j_user, neo4j_password) as graph:
        graph.init_schema()
        graph.merge_nodes(nodes)
        # Update trust scores
        for nid, score in scores.items():
            graph.driver.session().run(
                "MATCH (n:CodeNode {id: $id}) SET n.trust_score = $score",
                id=nid, score=score,
            )
        graph.merge_edges(edges)

    console.print(f"[bold green]Indexed {len(nodes)} nodes into Neo4j.[/bold green]")


@app.command()
def query(
    text: str = typer.Argument(..., help="Query string"),
    depth: int = typer.Option(2, "--depth", "-d", help="Relationship depth"),
    min_trust: float = typer.Option(0.0, "--min-trust", "-t", help="Minimum trust score"),
    neo4j_uri: str = typer.Option("bolt://localhost:7687", "--neo4j"),
    neo4j_user: str = typer.Option("neo4j", "--user"),
    neo4j_password: str = typer.Option("password", "--password"),
) -> None:
    """Query the code graph for relevant context."""
    with Neo4jGraph(neo4j_uri, neo4j_user, neo4j_password) as graph:
        engine = QueryEngine(graph)
        results = engine.query(text, depth=depth, min_trust=min_trust)

    table = Table(title=f"Context for: {text}")
    table.add_column("Node", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Trust", style="green")
    table.add_column("Distance", style="yellow")

    for r in results[:20]:
        table.add_row(r.name, r.type, f"{r.trust:.2f}", str(r.distance))

    console.print(table)


@app.command()
def context(
    text: str = typer.Argument(..., help="Query string"),
    output: str = typer.Option("context.md", "--output", "-o", help="Output file"),
    depth: int = typer.Option(2, "--depth", "-d"),
    min_trust: float = typer.Option(0.0, "--min-trust", "-t"),
    neo4j_uri: str = typer.Option("bolt://localhost:7687", "--neo4j"),
    neo4j_user: str = typer.Option("neo4j", "--user"),
    neo4j_password: str = typer.Option("password", "--password"),
) -> None:
    """Generate a markdown context file for AI agents."""
    with Neo4jGraph(neo4j_uri, neo4j_user, neo4j_password) as graph:
        engine = QueryEngine(graph)
        results = engine.query(text, depth=depth, min_trust=min_trust)
        md = engine.to_markdown(results, text)

    Path(output).write_text(md, encoding="utf-8")
    console.print(f"[bold green]Context written to {output} ({len(results)} nodes)[/bold green]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
