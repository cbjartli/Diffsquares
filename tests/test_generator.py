from random import Random
import unittest

from diffsquares.generator import DIFFICULTIES, GenerationError, generate
from diffsquares.layouts import LAYOUT_NAMES, make_layout
from diffsquares.solver import solve
from test_solver import brute_force


class GeneratorTests(unittest.TestCase):
    def test_unique_solutions_and_requested_difficulty_across_seeds(self):
        for name in LAYOUT_NAMES:
            for difficulty in DIFFICULTIES:
                for seed in range(5):
                    with self.subTest(layout=name, difficulty=difficulty, seed=seed):
                        puzzle = generate(make_layout(name, 6 + seed % 3), 1, 30, difficulty, Random(seed))
                        result = solve(puzzle.layout, puzzle.square_clues, puzzle.triangle_clues, 1, 30)
                        self.assertEqual(result.solutions, [puzzle.square_solution])
                        self.assertEqual(puzzle.difficulty, difficulty)
                        self.assertGreater(sum(c is None for c in puzzle.square_clues + puzzle.triangle_clues), 0)
                        self.assertEqual(puzzle.triangle_solution,
                                         tuple(abs(puzzle.square_solution[a] - puzzle.square_solution[b])
                                               for a, b in puzzle.layout.edges))
                        self.assertTrue(all(v > 0 for v in puzzle.triangle_solution))
                        self.assertTrue(all(clue is None or clue == value for clue, value in
                                            zip(puzzle.square_clues + puzzle.triangle_clues,
                                                puzzle.square_solution + puzzle.triangle_solution)))

    def test_small_generated_puzzles_are_unique_by_brute_force(self):
        for seed in range(15):
            puzzle = generate(make_layout("chain", 4), 5, 9, "easy", Random(seed))
            self.assertEqual(brute_force(puzzle.layout, puzzle.square_clues, puzzle.triangle_clues, 5, 9),
                             [puzzle.square_solution])

    def test_reproducible_with_same_seed(self):
        layout = make_layout("loop", 8)
        self.assertEqual(generate(layout, 1, 30, "hard", Random(42)),
                         generate(layout, 1, 30, "hard", Random(42)))

    def test_impossible_difficulty_reports_failure(self):
        with self.assertRaisesRegex(GenerationError, "Could not make a hard"):
            generate(make_layout("chain", 2), 1, 2, "hard", Random(0), attempts=3)

    def test_argument_validation(self):
        for minimum, maximum, difficulty, attempts in (
            (0, 30, "easy", 1), (5, 5, "easy", 1), (1, 30, "unknown", 1), (1, 30, "easy", 0)
        ):
            with self.assertRaises(ValueError):
                generate(make_layout("chain", 2), minimum, maximum, difficulty, Random(0),
                         attempts=attempts)


if __name__ == "__main__":
    unittest.main()
