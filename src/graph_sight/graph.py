"""Neo4j graph builder for codebase relationships."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None  # type: ignore[assignment,misc]

from graph_sight.parser import CodeEdge, CodeNode


class Neo4jGraph:
    """Store and query code relationships in Neo4j."""

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j", password: str = "password") -> None:
        if GraphDatabase is None:
            raise RuntimeError("neo4j driver not installed — `pip install neo4j`")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def __enter__(self) -> "Neo4jGraph":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def init_schema(self) -> None:
        """Create constraints and indexes."""
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT code_node_id IF NOT EXISTS FOR (n:CodeNode) REQUIRE n.id IS UNIQUE")
            session.run("CREATE INDEX code_node_type IF NOT EXISTS FOR (n:CodeNode) ON (n.type)")
            session.run("CREATE INDEX code_node_language IF NOT EXISTS FOR (n:CodeNode) ON (n.language)")

    def merge_nodes(self, nodes: list[CodeNode]) -> None:
        with self.driver.session() as session:
            for node in nodes:
                props = {k: v for k, v in asdict(node).items() if v is not None}
                session.run(
                    "MERGE (n:CodeNode {id: $id}) SET n += $props",
                    id=node.id, props=props,
                )

    def merge_edges(self, edges: list[CodeEdge]) -> None:
        with self.driver.session() as session:
            for edge in edges:
                session.run(
                    f"""
                    MATCH (a:CodeNode {{id: $source}}), (b:CodeNode {{id: $target}})
                    MERGE (a)-[r:{edge.type.upper()}]->(b)
                    SET r.weight = $weight
                    """,
                    source=edge.source, target=edge.target, weight=edge.weight,
                )

    def query_context(self, query: str, depth: int = 2, min_trust: float = 0.0) -> list[dict[str, Any]]:
        """Find contextually relevant nodes around a name match."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n:CodeNode)
                WHERE n.name CONTAINS $query OR n.id CONTAINS $query
                CALL {
                    WITH n
                    MATCH path = (n)-[:DEPENDS_ON|IMPORTS|CALLS|BELONGS_TO*1..""" + str(depth) + """]-(related)
                    RETURN related, length(path) AS dist
                }
                RETURN n.id AS root, related.id AS node_id, related.name AS name,
                       related.type AS type, related.trust_score AS trust, dist
                ORDER BY dist, trust DESC
                """,
                query=query,
            )
            return [dict(r) for r in result]

    def get_trust_scores(self) -> list[dict[str, Any]]:
        """Return all nodes with their trust scores."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n:CodeNode)
                RETURN n.id AS id, n.name AS name, n.type AS type,
                       n.trust_score AS trust, n.complexity AS complexity
                ORDER BY trust DESC
                """
            )
            return [dict(r) for r in result]
