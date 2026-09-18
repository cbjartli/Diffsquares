"""Exact constraint solving and a separate, deliberately simpler reference strategy."""

from collections import deque
from dataclasses import dataclass

from .layouts import Layout


class SearchLimitError(RuntimeError):
    pass


@dataclass
class Reasoning:
    forced_moves: int = 0
    alternatives_tested: int = 0
    contradictions: int = 0
    max_trial_depth: int = 0

    @property
    def difficulty(self) -> str:
        if self.max_trial_depth == 0:
            return "easy"
        return "medium" if self.max_trial_depth == 1 else "hard"


@dataclass
class SolveResult:
    solutions: list[tuple[int, ...]]
    reasoning: Reasoning
    search_nodes: int


def solve(
    layout: Layout,
    square_clues: tuple[int | None, ...],
    triangle_clues: tuple[int | None, ...],
    minimum: int,
    maximum: int,
    *,
    limit: int = 2,
    strategy: str = "exact",
    node_budget: int = 100_000,
) -> SolveResult:
    """Count up to `limit` solutions; exhausting the budget raises, never means unique.

    Exact mode propagates all candidate sets. Reference mode propagates only from
    known/singleton squares, then explicitly tests alternatives in smallest-domain
    order. Its search depth measures this strategy, not intrinsic human difficulty.
    """
    if minimum < 1 or maximum <= minimum:
        raise ValueError("Use a positive square-number range containing at least two integers")
    if len(square_clues) != len(layout.squares) or len(triangle_clues) != len(layout.triangles):
        raise ValueError("Clue counts do not match the layout")
    if limit < 1 or node_budget < 1 or strategy not in ("exact", "reference"):
        raise ValueError("Invalid solver limit, budget, or strategy")
    if any(v is not None and not minimum <= v <= maximum for v in square_clues):
        raise ValueError("Square clue outside the allowed range")
    if any(v is not None and not 1 <= v <= maximum - minimum for v in triangle_clues):
        raise ValueError("Triangle clue outside the possible positive differences")

    full = (1 << (maximum - minimum + 1)) - 1
    domains = [full if v is None else 1 << (v - minimum) for v in square_clues]
    neighbors: list[list[tuple[int, int | None]]] = [[] for _ in domains]
    for (a, b), difference in zip(layout.edges, triangle_clues):
        neighbors[a].append((b, difference))
        neighbors[b].append((a, difference))
    reasoning = Reasoning()
    result = SolveResult([], reasoning, 0)

    def propagate(values: list[int]) -> bool:
        queue = deque(range(len(values)))
        queued = set(queue)
        while queue:
            source = queue.popleft()
            queued.remove(source)
            source_mask = values[source]
            singleton = source_mask.bit_count() == 1
            if strategy == "reference" and not singleton:
                continue
            for target, difference in neighbors[source]:
                if difference is None:
                    supported = full ^ source_mask if singleton else full
                else:
                    supported = ((source_mask << difference) | (source_mask >> difference)) & full
                revised = values[target] & supported
                if not revised:
                    return False
                if revised != values[target]:
                    if revised.bit_count() == 1 and values[target].bit_count() > 1:
                        reasoning.forced_moves += 1
                    values[target] = revised
                    if target not in queued:
                        queue.append(target)
                        queued.add(target)
        return True

    def visit(values: list[int], depth: int) -> None:
        result.search_nodes += 1
        if result.search_nodes > node_budget:
            raise SearchLimitError(f"Solver exceeded its {node_budget:,}-node budget")
        reasoning.max_trial_depth = max(reasoning.max_trial_depth, depth)
        if not propagate(values):
            reasoning.contradictions += 1
            return
        choices = [i for i, domain in enumerate(values) if domain.bit_count() > 1]
        if not choices:
            result.solutions.append(tuple(minimum + v.bit_length() - 1 for v in values))
            return
        index = min(choices, key=lambda i: (values[i].bit_count(), -len(neighbors[i]), i))
        remaining = values[index]
        while remaining and len(result.solutions) < limit:
            bit = remaining & -remaining
            remaining ^= bit
            child = values.copy()
            child[index] = bit
            reasoning.alternatives_tested += 1
            visit(child, depth + 1)

    visit(domains, 0)
    return result
