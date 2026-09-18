from dataclasses import dataclass
from random import Random

from .layouts import Layout
from .solver import Reasoning, SearchLimitError, solve

DIFFICULTIES = ("easy", "medium", "hard")


class GenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Puzzle:
    layout: Layout
    square_clues: tuple[int | None, ...]
    triangle_clues: tuple[int | None, ...]
    square_solution: tuple[int, ...]
    triangle_solution: tuple[int, ...]
    reasoning: Reasoning
    minimum: int
    maximum: int

    @property
    def difficulty(self) -> str:
        return self.reasoning.difficulty


def _solution(layout: Layout, minimum: int, maximum: int, rng: Random) -> tuple[int, ...]:
    values: list[int] = []
    smooth = rng.random() < .5
    for index in range(len(layout.squares)):
        earlier = [values[b if a == index else a] for a, b in layout.edges
                   if index in (a, b) and (b if a == index else a) < index]
        choices = [v for v in range(minimum, maximum + 1) if v not in earlier]
        if not choices:
            raise GenerationError("Cannot assign distinct adjacent squares in this number range")
        if smooth and earlier:
            nearby = [v for v in choices if abs(v - earlier[0]) <= max(2, (maximum - minimum) // 3)]
            if nearby:
                choices = nearby
        values.append(rng.choice(choices))
    return tuple(values)


def generate(
    layout: Layout,
    minimum: int,
    maximum: int,
    difficulty: str,
    rng: Random,
    *,
    attempts: int = 150,
) -> Puzzle:
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unknown difficulty: {difficulty}")
    if minimum < 1 or maximum <= minimum:
        raise ValueError("Use a positive square-number range containing at least two integers")
    if attempts < 1:
        raise ValueError("Generation attempts must be positive")
    target_depth = DIFFICULTIES.index(difficulty)
    search_limits = 0
    for _ in range(attempts):
        solution = _solution(layout, minimum, maximum, rng)
        differences = tuple(abs(solution[a] - solution[b]) for a, b in layout.edges)
        squares: list[int | None] = list(solution)
        triangles: list[int | None] = list(differences)
        square_order = list(range(len(squares)))
        triangle_order = list(range(len(squares), len(squares) + len(triangles)))
        rng.shuffle(square_order)
        rng.shuffle(triangle_order)
        order = square_order + triangle_order
        if difficulty == "easy":
            rng.shuffle(order)
        try:
            for index in order:
                clues, position = ((squares, index) if index < len(squares)
                                   else (triangles, index - len(squares)))
                previous = clues[position]
                clues[position] = None
                result = solve(layout, tuple(squares), tuple(triangles), minimum, maximum)
                keep = len(result.solutions) == 1
                if keep and difficulty != "hard":
                    report = solve(layout, tuple(squares), tuple(triangles), minimum, maximum,
                                   strategy="reference").reasoning
                    keep = report.max_trial_depth <= target_depth
                if not keep:
                    clues[position] = previous
            reference = solve(layout, tuple(squares), tuple(triangles), minimum, maximum,
                              strategy="reference")
        except SearchLimitError:
            search_limits += 1
            continue
        if reference.reasoning.difficulty == difficulty and reference.solutions == [solution]:
            return Puzzle(layout, tuple(squares), tuple(triangles), solution, differences,
                          reference.reasoning, minimum, maximum)
    detail = f" ({search_limits} attempts hit the solver budget)" if search_limits else ""
    raise GenerationError(
        f"Could not make a {difficulty} {layout.name} puzzle with {len(layout.squares)} squares "
        f"in {minimum}..{maximum} after {attempts} attempts{detail}. "
        "Try more squares, a wider range, an easier difficulty, or a larger --attempts value."
    )
