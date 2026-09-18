from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
from random import Random
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from diffsquares.__main__ import main, parser
from diffsquares.generator import generate
from diffsquares.layouts import make_layout
from diffsquares.render import RenderError, latex, write_outputs


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.puzzle = generate(make_layout("chain", 6), 1, 30, "hard", Random(42))

    def test_worksheet_draws_only_clues_answer_key_draws_all_values(self):
        puzzle = self.puzzle
        worksheet = latex([puzzle] * 4, 42)
        answers = latex([puzzle] * 4, 42, answers=True)
        clue_count = sum(c is not None for c in puzzle.square_clues + puzzle.triangle_clues)
        self.assertEqual(worksheet.count(r"\node["), 4 * clue_count)
        self.assertEqual(answers.count(r"\node["), 4 * len(puzzle.layout.polygons))
        self.assertEqual(worksheet.count(r"\newpage"), 1)
        self.assertEqual(worksheet.count(r"\draw["), 4 * len(puzzle.layout.polygons))
        self.assertIn("from 1 to 30", worksheet)
        self.assertIn("greater than zero", worksheet)
        self.assertNotIn("blue!65!black", worksheet)
        self.assertIn("blue!65!black", answers)
        self.assertIn("Trial depth: 2", answers)

    def test_sources_json_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "new" / "worksheet"
            paths = write_outputs([self.puzzle], 42, prefix, pdf=False)
            self.assertEqual(len(paths), 3)
            data = json.loads(paths[2].read_text())
            self.assertEqual(data["seed"], 42)
            self.assertEqual(data["puzzles"][0]["square_solution"], list(self.puzzle.square_solution))
            with self.assertRaises(FileExistsError):
                write_outputs([self.puzzle], 42, prefix, pdf=False)
            write_outputs([self.puzzle], 42, prefix, pdf=False, force=True)
            prefix.with_suffix(".pdf").write_bytes(b"old PDF")
            with self.assertRaisesRegex(FileExistsError, "stale"):
                write_outputs([self.puzzle], 42, prefix, pdf=False, force=True)
            self.assertFalse(any(path.name.startswith(".diffsquares-") for path in prefix.parent.iterdir()))

    def test_failed_latex_preserves_existing_outputs_and_cleans_temporary_files(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "worksheet"
            paths = write_outputs([self.puzzle], 42, prefix, pdf=False)
            originals = [path.read_bytes() for path in paths]
            failed = subprocess.CompletedProcess(["pdflatex"], 1, "! Missing TikZ")
            with patch("diffsquares.render.subprocess.run", return_value=failed):
                with self.assertRaisesRegex(RenderError, "Missing TikZ"):
                    write_outputs([self.puzzle], 99, prefix, force=True)
            self.assertEqual([path.read_bytes() for path in paths], originals)
            self.assertFalse(prefix.with_suffix(".pdf").exists())
            self.assertFalse(any(path.name.startswith(".diffsquares-") for path in prefix.parent.iterdir()))

    def test_missing_compiler_and_timeout_are_explicit_errors(self):
        for error, message in ((FileNotFoundError(), "pdflatex was not found"),
                               (subprocess.TimeoutExpired("pdflatex", 120), "timed out")):
            with tempfile.TemporaryDirectory() as directory:
                prefix = Path(directory) / "worksheet"
                with patch("diffsquares.render.subprocess.run", side_effect=error):
                    with self.assertRaisesRegex(RenderError, message):
                        write_outputs([self.puzzle], 42, prefix)
                self.assertEqual(list(prefix.parent.iterdir()), [])

    def test_paper_and_number_range_are_configurable(self):
        puzzle = generate(make_layout("chain", 4), 10, 100, "easy", Random(42))
        text = latex([puzzle], 12, paper="letter", per_page=1)
        self.assertIn("letterpaper", text)
        self.assertIn("from 10 to 100", text)
        for puzzles, options in (([], {}), ([self.puzzle], {"per_page": 0}),
                                 ([self.puzzle], {"paper": "bogus"}),
                                 ([self.puzzle, puzzle], {})):
            with self.assertRaises(ValueError):
                latex(puzzles, 42, **options)


class CliTests(unittest.TestCase):
    def test_no_pdf_command_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "test"
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["--no-pdf", "--seed", "42", "--output", str(prefix)]), 0)
            self.assertIn("12 uniquely solvable", output.getvalue())
            puzzles = json.loads(prefix.with_suffix(".json").read_text())["puzzles"]
            self.assertEqual([p["difficulty"] for p in puzzles], ["easy"] * 4 + ["medium"] * 4 + ["hard"] * 4)
            self.assertEqual({p["layout"] for p in puzzles}, {"chain", "branch", "loop"})
            self.assertEqual({len(p["squares"]) for p in puzzles}, {6, 8, 10})
            for name in ("chain", "branch", "loop"):
                self.assertEqual({len(p["squares"]) for p in puzzles if p["layout"] == name}, {6, 8, 10})

    def test_bad_arguments_are_reported(self):
        for args in (["--count", "0"], ["--sizes", "2,no"], ["--layouts", "bogus"],
                     ["--max-number", "1"], ["--output", "name.pdf"]):
            with self.subTest(args=args), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(args)
                self.assertEqual(error.exception.code, 2)
        for args in (["--no-pdf", "--sizes", "3"],
                     ["--no-pdf", "--layouts", "chain", "--sizes", "2",
                      "--max-number", "2", "--difficulty", "hard", "--attempts", "1"]):
            with self.subTest(args=args), redirect_stderr(io.StringIO()) as output:
                self.assertEqual(main(args), 1)
                self.assertIn("diffsquares:", output.getvalue())

    def test_a_single_layout_rotates_through_every_requested_size(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "short-chains"
            with redirect_stdout(io.StringIO()):
                status = main(["--no-pdf", "--count", "8", "--layouts", "chain",
                               "--sizes", "3,4,5,6", "--difficulty", "easy", "--max-number", "15",
                               "--seed", "123", "--output", str(prefix)])
            self.assertEqual(status, 0)
            puzzles = json.loads(prefix.with_suffix(".json").read_text())["puzzles"]
            self.assertEqual([len(p["squares"]) for p in puzzles], [3, 4, 5, 6] * 2)

    def test_help_documents_primary_configuration(self):
        text = parser().format_help()
        for flag in ("--sizes", "--layouts", "--difficulty", "--min-number", "--max-number", "--seed"):
            self.assertIn(flag, text)


if __name__ == "__main__":
    unittest.main()
