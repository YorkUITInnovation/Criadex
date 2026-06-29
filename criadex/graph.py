import re
import time
from collections import Counter, defaultdict
from typing import Dict, List, Set


class GroupGraphStore:
    STOP_WORDS = {
        "about", "after", "again", "also", "and", "are", "because", "been",
        "before", "between", "both", "but", "can", "course", "could", "each",
        "from", "have", "into", "just", "like", "more", "most", "must",
        "only", "other", "over", "same", "some", "such", "than", "that",
        "their", "them", "then", "there", "these", "they", "this", "those",
        "through", "under", "very", "what", "when", "where", "which", "while",
        "with", "would", "your",
    }
    TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")

    def __init__(self) -> None:
        self._graphs: Dict[str, dict] = {}

    def _extract_terms(self, text: str) -> Set[str]:
        terms: Set[str] = set()
        for match in self.TOKEN_PATTERN.findall(text or ""):
            token = match.lower().strip()
            if token in self.STOP_WORDS:
                continue
            if token.isdigit():
                continue
            terms.add(token)
        return terms

    def build(self, group_name: str, documents: List[str]) -> dict:
        adjacency: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        frequency: Counter = Counter()

        for text in documents:
            terms = sorted(self._extract_terms(text))
            if not terms:
                continue
            for term in terms:
                frequency[term] += 1
            for i, left in enumerate(terms):
                for right in terms[i + 1:]:
                    adjacency[left][right] += 1
                    adjacency[right][left] += 1

        node_count = len(adjacency)
        edge_count = sum(len(neighbors) for neighbors in adjacency.values()) // 2
        top_entities = [token for token, _ in frequency.most_common(10)]
        built_at = round(time.time())

        self._graphs[group_name] = {
            "status": "READY",
            "built_at": built_at,
            "node_count": node_count,
            "edge_count": edge_count,
            "top_entities": top_entities,
            "adjacency": {k: dict(v) for k, v in adjacency.items()},
        }
        return self.status(group_name)

    def status(self, group_name: str) -> dict:
        graph = self._graphs.get(group_name)
        if graph is None:
            return {
                "status": "NOT_BUILT",
                "built_at": None,
                "node_count": 0,
                "edge_count": 0,
                "top_entities": [],
            }
        return {
            "status": graph["status"],
            "built_at": graph["built_at"],
            "node_count": graph["node_count"],
            "edge_count": graph["edge_count"],
            "top_entities": graph["top_entities"],
        }

    def expand_query(
        self,
        group_name: str,
        query: str,
        max_hops: int,
        max_terms: int
    ) -> List[str]:
        graph = self._graphs.get(group_name)
        if graph is None:
            return []

        adjacency: Dict[str, Dict[str, int]] = graph["adjacency"]
        seeds = self._extract_terms(query)
        if not seeds:
            return []

        frontier = set(seeds)
        discovered = set(seeds)
        scored_candidates: Counter = Counter()

        for _ in range(max(1, max_hops)):
            new_frontier = set()
            for term in frontier:
                neighbors = adjacency.get(term, {})
                for neighbor, weight in neighbors.items():
                    scored_candidates[neighbor] += weight
                    if neighbor not in discovered:
                        discovered.add(neighbor)
                        new_frontier.add(neighbor)
            if not new_frontier:
                break
            frontier = new_frontier

        for seed in seeds:
            scored_candidates.pop(seed, None)

        return [term for term, _ in scored_candidates.most_common(max_terms)]
