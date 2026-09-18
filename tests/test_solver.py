from itertools import product
from random import Random
import unittest

from diffsquares.layouts import make_layout
from diffsquares.solver import SearchLimitError, solve


def brute_force(layout, squares, triangles, minimum, maximum):
    solutions = []
    for values in product(range(minimum, maximum + 1), repeat=len(squares)):
        if any(clue is not None and clue != value for clue, value in zip(squares, values)):
            continue
        differences = [abs(values[a] - values[b]) for a, b in layout.edges]
        if any(difference == 0 or (clue is not None and clue != difference)
               for clue, difference in zip(triangles, differences)):
            continue
        solutions.append(values)
    return solutions


class SolverTests(unittest.TestCase):
    def test_both_strategies_against_independent_exhaustive_enumeration(self):
        rng = Random(152)
        for name, size in (("chain", 4), ("branch", 4), ("loop", 6)):
            layout = make_layout(name, size)
            for case in range(35):
                minimum, maximum = (1, 4) if case % 2 else (5, 8)
                squares = tuple(rng.choice([None, None, *range(minimum, maximum + 1)])
                                for _ in layout.squares)
                triangles = tuple(rng.choice([None, None, 1, 2, 3]) for _ in layout.triangles)
                expected = brute_force(layout, squares, triangles, minimum, maximum)
                for strategy in ("exact", "reference"):
                    with self.subTest(name=name, case=case, strategy=strategy):
                        result = solve(layout, squares, triangles, minimum, maximum, strategy=strategy)
                        self.assertEqual(len(result.solutions), min(2, len(expected)))
                        self.assertEqual(len(set(result.solutions)), len(result.solutions))
                        self.assertTrue(all(solution in expected for solution in result.solutions))

    def test_known_reasoning_depths(self):
        cases = (
            ((1, None, 10), (3, None), (1, 4, 10), 0),
            ((10, None, None, 13), (2, 3, 4), (10, 12, 9, 13), 1),
            ((2, None, None, None, None, 21), (7, 1, 1, 8, 6), (2, 9, 8, 7, 15, 21), 2),
        )
        for squares, triangles, solution, depth in cases:
            with self.subTest(depth=depth):
                result = solve(make_layout("chain", len(squares)), squares, triangles, 1, 30,
                               strategy="reference")
                self.assertEqual(result.solutions, [solution])
                self.assertEqual(result.reasoning.max_trial_depth, depth)
                self.assertEqual(result.reasoning.difficulty, ("easy", "medium", "hard")[depth])
                if depth:
                    self.assertGreater(result.reasoning.contradictions, 0)
                    self.assertGreaterEqual(result.reasoning.alternatives_tested, 2)

    def test_unknown_triangle_still_forbids_equal_squares(self):
        layout = make_layout("chain", 2)
        self.assertEqual(solve(layout, (4, 4), (None,), 1, 10).solutions, [])
        self.assertEqual(solve(layout, (4, 6), (None,), 1, 10).solutions, [(4, 6)])

    def test_nonadjacent_numbers_can_repeat(self):
        layout = make_layout("chain", 3)
        self.assertEqual(solve(layout, (4, None, 4), (2, 2), 1, 10).solutions, [(4, 2, 4), (4, 6, 4)])

    def test_invalid_constraints_are_errors_not_solutions(self):
        layout = make_layout("chain", 2)
        cases = [
            ((None,), (None,), 1, 10),
            ((None, None), (), 1, 10),
            ((0, None), (None,), 1, 10),
            ((None, None), (0,), 1, 10),
            ((None, None), (10,), 1, 10),
            ((None, None), (None,), 0, 10),
            ((None, None), (None,), 2, 2),
        ]
        for squares, triangles, minimum, maximum in cases:
            with self.subTest(squares=squares, triangles=triangles, minimum=minimum, maximum=maximum):
                with self.assertRaises(ValueError):
                    solve(layout, squares, triangles, minimum, maximum)
        with self.assertRaises(SearchLimitError):
            solve(layout, (None, None), (None,), 1, 30, node_budget=1)


if __name__ == "__main__":
    unittest.main()
