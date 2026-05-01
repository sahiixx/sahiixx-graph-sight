"""Basic tests for graph-sight parser."""

import tempfile
from pathlib import Path

from graph_sight.parser import CodebaseParser


def test_parse_python_module():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "main.py").write_text("""
def hello():
    print("hello")

class Greeter:
    def greet(self):
        return "hi"
""")
        parser = CodebaseParser(root)
        nodes, edges = parser.parse()

        ids = {n.id for n in nodes}
        assert any("main.py" in nid for nid in ids)
        assert any("hello" in nid for nid in ids)
        assert any("Greeter" in nid for nid in ids)
        assert any("greet" in nid for nid in ids)

        assert len(edges) > 0
        assert any(e.type == "belongs_to" for e in edges)
