"""
Navegador AST determinista para consultar LegacyGraph (OppyTec-Legacy/grafos-legacy/)
y V2Graph (docs/architecture/graphify/) en el REPL de Python sin volcar graph.json crudo al prompt.
"""
import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]
LEGACY_GRAPH_PATH = ROOT_DIR / "OppyTec-Legacy" / "grafos-legacy" / "graphify-out" / "graph.json"
V2_GRAPH_PATH = ROOT_DIR / "docs" / "architecture" / "graphify" / "graph.json"


class ASTGraphNavigator:
    def __init__(self, graph_path: Path, read_only: bool = True) -> None:
        self.graph_path = graph_path
        self.read_only = read_only
        self._cache: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._cache is None:
            if not self.graph_path.exists():
                return {"nodes": [], "edges": []}
            self._cache = json.loads(self.graph_path.read_text(encoding="utf-8"))
        return self._cache

    def neighbors(self, symbol_query: str, depth: int = 1, limit: int = 25) -> dict[str, Any]:
        """Devuelve únicamente la vecindad inmediata (< 150 tokens) de un símbolo AST."""
        data = self._load()
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        matched_ids = {
            n.get("id") for n in nodes
            if symbol_query.lower() in str(n.get("id", "")).lower()
            or symbol_query.lower() in str(n.get("label", "")).lower()
            or symbol_query.lower() in str(n.get("path", "")).lower()
        }
        related_edges = [
            e for e in edges
            if e.get("source") in matched_ids or e.get("target") in matched_ids
        ][:limit]
        return {
            "query": symbol_query,
            "matched_count": len(matched_ids),
            "sample_matches": sorted(str(x) for x in list(matched_ids)[:limit]),
            "edges": related_edges,
        }


legacy_graph = ASTGraphNavigator(LEGACY_GRAPH_PATH, read_only=True)
v2_graph = ASTGraphNavigator(V2_GRAPH_PATH, read_only=False)
