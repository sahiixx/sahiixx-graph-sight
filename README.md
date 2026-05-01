# graph-sight

> **codesight gives you context. graph-sight gives you *relationships*.**

[![Neo4j](https://img.shields.io/badge/neo4j-powered-blue)](https://neo4j.com)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## The Problem

AI coding agents have a context window. You have a 100K-line codebase. How do you feed the *right* 10K lines into the agent?

Existing solutions:
- **codesight** (980 ★) — AST parser + 30 framework detectors. One `npx` call, zero deps. Flat context.
- **graphify** (34K ★) — Knowledge graph from any folder. Great for query.
- **code-review-graph** (13K ★) — Local knowledge graph for Claude Code.

**graph-sight** goes further:
1. Parses your codebase into a **living knowledge graph**
2. Scores every module by **trust** (test coverage, change frequency, author reputation)
3. Ranks context by **relevance** to your query
4. Generates **relationship-aware** context that agents actually understand

---

## What It Does

```bash
# 1. Index your codebase into Neo4j
python -m graph_sight index ./my-project --neo4j bolt://localhost:7687

# 2. Query for context
python -m graph_sight query "auth module" --depth 2 --min-trust 0.7

# 3. Generate agent context
python -m graph_sight context "refactor auth" --output context.md
```

**Output:** A `context.md` with:
- Ranked list of relevant files
- Trust scores for each module
- Relationship map (what depends on what)
- Risk flags (untested code, stale files)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  📁 Codebase                                                │
│   ├── src/                                                  │
│   ├── tests/                                                │
│   └── package.json / pyproject.toml                         │
├─────────────────────────────────────────────────────────────┤
│  🔍 Parser Layer                                            │
│   ├── AST extractor (tree-sitter)                          │
│   ├── Import mapper (static analysis)                        │
│   └── Git historian (blame, churn, coverage)                │
├─────────────────────────────────────────────────────────────┤
│  🧠 Graph Layer (Neo4j)                                     │
│   ├── (:Module {name, trust_score, language})              │
│   ├── (:Function {name, trust_score, complexity})          │
│   ├── (:Test {name, status, coverage})                      │
│   └── [:DEPENDS_ON {weight}] [:TESTED_BY {weight}]          │
├─────────────────────────────────────────────────────────────┤
│  🎯 Query Engine                                            │
│   ├── Semantic search (embeddings)                          │
│   ├── Trust scoring (Pagerank + coverage)                  │
│   └── Context assembly (ranked, pruned)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Trust Scoring

Every node in the graph gets a trust score (0.0–1.0):

| Factor | Weight | Source |
|--------|--------|--------|
| Test coverage | 30% | Coverage.py / jest --coverage |
| Change churn | 20% | Git log (frequently changed = lower trust) |
| Author reputation | 15% | Internal trust graph or git history |
| Review status | 15% | PR review data |
| Age | 10% | Newer code = lower trust |
| Complexity | 10% | Cyclomatic complexity |

**Why trust matters:** When you ask Claude to "refactor auth," you want it to see the *well-tested, stable* auth module — not the experimental branch someone pushed last week.

---

## Quick Start

```bash
# Install
pip install graph-sight

# Or clone
git clone https://github.com/sahiixx/graph-sight.git
cd graph-sight
pip install -e ".[dev]"

# Start Neo4j (docker)
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.15

# Index a codebase
graph-sight index ./my-project

# Query
graph-sight query "auth module" --depth 2 --min-trust 0.7

# Generate context for Claude Code
graph-sight context "refactor auth" --output context.md
```

---

## Comparison

| Feature | graph-sight | codesight | graphify | code-review-graph |
|---------|-------------|-----------|----------|-------------------|
| AST parsing | ✅ | ✅ | ❌ | ✅ |
| Knowledge graph | ✅ (Neo4j) | ❌ | ✅ (custom) | ✅ (custom) |
| Trust scoring | ✅ | ❌ | ❌ | ❌ |
| Relationship context | ✅ | ❌ | ✅ | ✅ |
| One-command install | ✅ `pip install` | ✅ `npx` | ❌ | ❌ |
| Framework detection | 30+ | 30+ | ❌ | ❌ |
| Embeddings search | ✅ | ❌ | ✅ | ❌ |
| Coverage integration | ✅ | ❌ | ❌ | ❌ |

---

## Ecosystem

| Repo | Role |
|------|------|
| [`titans-memory`](https://github.com/sahiixx/titans-memory) | Surprise-weighted agent memory |
| [`goose-aios`](https://github.com/sahiixx/goose-aios) | Local LLM backend |
| [`friday-os`](https://github.com/sahiixx/friday-os) | Voice-first AI OS that uses graph-sight for context |
| [`agent-design.md`](https://github.com/sahiixx/sahiixx-agent-design.md) | Visual identity spec |

---

## License

MIT — see [LICENSE](LICENSE).

> *"Context is flat. Relationships are deep."*
