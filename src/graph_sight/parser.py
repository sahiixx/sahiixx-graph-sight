"""Codebase parser — extract modules, functions, imports, and relationships."""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class CodeNode:
    """A node in the code graph."""
    id: str
    name: str
    type: str  # module, function, class, test
    file: str
    language: str
    lines: int = 0
    complexity: int = 0
    imports: list[str] = field(default_factory=list)


@dataclass
class CodeEdge:
    """A relationship between two code nodes."""
    source: str
    target: str
    type: str  # depends_on, calls, imports, tested_by
    weight: float = 1.0


class CodebaseParser:
    """Parse a codebase into nodes and edges."""

    SUPPORTED = {"py", "js", "ts", "jsx", "tsx"}

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def parse(self) -> tuple[list[CodeNode], list[CodeEdge]]:
        nodes: list[CodeNode] = []
        edges: list[CodeEdge] = []
        for file_path in self._walk():
            file_nodes, file_edges = self._parse_file(file_path)
            nodes.extend(file_nodes)
            edges.extend(file_edges)
        return nodes, edges

    def _walk(self) -> Iterator[Path]:
        for dirpath, _, filenames in os.walk(self.root):
            # Skip common non-source dirs
            if any(part.startswith((".", "node_modules", "venv", ".git", "__pycache__")) for part in Path(dirpath).parts):
                continue
            for name in filenames:
                ext = name.split(".")[-1] if "." in name else ""
                if ext in self.SUPPORTED:
                    yield Path(dirpath) / name

    def _parse_file(self, file_path: Path) -> tuple[list[CodeNode], list[CodeEdge]]:
        rel = str(file_path.relative_to(self.root))
        ext = file_path.suffix.lstrip(".")
        language = {"py": "python", "js": "javascript", "ts": "typescript", "jsx": "javascript", "tsx": "typescript"}.get(ext, ext)
        nodes: list[CodeNode] = []
        edges: list[CodeEdge] = []

        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return nodes, edges

        lines = source.count("\n") + 1
        module_id = f"module:{rel}"
        nodes.append(CodeNode(
            id=module_id, name=rel, type="module",
            file=str(rel), language=language, lines=lines,
        ))

        if ext == "py":
            file_nodes, file_edges = self._parse_python(rel, source, module_id)
            nodes.extend(file_nodes)
            edges.extend(file_edges)
        else:
            # JS/TS: regex-based import extraction
            imports = self._extract_js_imports(source)
            for imp in imports:
                edges.append(CodeEdge(source=module_id, target=f"module:{imp}", type="imports"))

        return nodes, edges

    def _parse_python(self, rel: str, source: str, module_id: str) -> tuple[list[CodeNode], list[CodeEdge]]:
        nodes: list[CodeNode] = []
        edges: list[CodeEdge] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return nodes, edges

        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    imports.append(alias.name)

        # Update module node with imports
        for n in nodes:
            if n.id == module_id:
                n.imports = imports
        # Actually module node already exists, find it and update
        # But we can't mutate easily here; create edges directly
        for imp in imports:
            edges.append(CodeEdge(source=module_id, target=f"module:{imp}", type="imports"))

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_id = f"func:{rel}::{node.name}"
                complexity = self._cyclomatic(node)
                nodes.append(CodeNode(
                    id=func_id, name=node.name, type="function",
                    file=rel, language="python",
                    lines=node.end_lineno - node.lineno if node.end_lineno else 1,
                    complexity=complexity,
                ))
                edges.append(CodeEdge(source=func_id, target=module_id, type="belongs_to"))
            elif isinstance(node, ast.ClassDef):
                class_id = f"class:{rel}::{node.name}"
                nodes.append(CodeNode(
                    id=class_id, name=node.name, type="class",
                    file=rel, language="python",
                    lines=node.end_lineno - node.lineno if node.end_lineno else 1,
                ))
                edges.append(CodeEdge(source=class_id, target=module_id, type="belongs_to"))
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_id = f"method:{rel}::{node.name}.{child.name}"
                        nodes.append(CodeNode(
                            id=method_id, name=child.name, type="method",
                            file=rel, language="python",
                            lines=child.end_lineno - child.lineno if child.end_lineno else 1,
                            complexity=self._cyclomatic(child),
                        ))
                        edges.append(CodeEdge(source=method_id, target=class_id, type="belongs_to"))
                        edges.append(CodeEdge(source=method_id, target=module_id, type="belongs_to"))

        return nodes, edges

    @staticmethod
    def _cyclomatic(node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                   ast.With, ast.Assert, ast.comprehension)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    @staticmethod
    def _extract_js_imports(source: str) -> list[str]:
        imports: list[str] = []
        # import X from 'path'
        for m in re.finditer(r"import\s+.*?\s+from\s+['\"](.+?)['\"]", source):
            imports.append(m.group(1))
        # require('path')
        for m in re.finditer(r"require\s*\(\s*['\"](.+?)['\"]\s*\)", source):
            imports.append(m.group(1))
        return imports
