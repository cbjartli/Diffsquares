import argparse
from pathlib import Path
from random import Random, SystemRandom
import sys

from .generator import DIFFICULTIES, GenerationError, generate
from .layouts import LAYOUT_NAMES, make_layout
from .render import RenderError, check_output_paths, write_outputs


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Expected a positive integer") from error
    if value < 1:
        raise argparse.ArgumentTypeError("Expected a positive integer")
    return value


def sizes_argument(text: str) -> tuple[int, ...]:
    return tuple(positive_int(part.strip()) for part in text.split(","))


def layouts_argument(text: str) -> tuple[str, ...]:
    names = tuple(part.strip() for part in text.split(","))
    if any(name not in LAYOUT_NAMES for name in names):
        raise argparse.ArgumentTypeError("Layouts must be a comma-separated list of chain,branch,loop")
    return names


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Generate original, uniquely solvable square/triangle difference puzzles.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    result.add_argument("--count", type=positive_int, default=12, help="Number of puzzles")
    result.add_argument("--sizes", type=sizes_argument, default=(6, 8, 10),
                        help="Comma-separated numbers of squares; every size must fit every layout")
    result.add_argument("--layouts", type=layouts_argument, default=LAYOUT_NAMES,
                        help="Comma-separated layouts: chain,branch,loop")
    result.add_argument("--min-number", type=positive_int, default=1, help="Smallest square number")
    result.add_argument("--max-number", type=positive_int, default=30, help="Largest square number")
    result.add_argument("--difficulty", choices=(*DIFFICULTIES, "mixed"), default="mixed",
                        help="Mixed progresses from easy to medium to hard")
    result.add_argument("--seed", type=int, help="Reproducible random seed; otherwise chosen randomly")
    result.add_argument("--output", type=Path, default=Path("worksheets/puzzles"),
                        help="Output filename prefix (without .pdf or .tex)")
    result.add_argument("--paper", choices=("a4", "letter"), default="a4", help="Paper size")
    result.add_argument("--per-page", type=int, choices=(1, 2, 3, 4), default=3,
                        help="Puzzles per page; fewer gives more room")
    result.add_argument("--attempts", type=positive_int, default=150,
                        help="Maximum generation attempts per puzzle; never relaxes uniqueness/difficulty")
    result.add_argument("--no-pdf", action="store_true", help="Write LaTeX and JSON without running pdflatex")
    result.add_argument("--force", action="store_true", help="Replace existing generated files")
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser()
    args = arguments.parse_args(argv)
    if args.max_number <= args.min_number:
        arguments.error("--max-number must be greater than --min-number")
    if args.output.suffix in (".pdf", ".tex", ".json"):
        arguments.error("--output is a filename prefix: omit the .pdf, .tex, or .json extension")
    try:
        layouts = {(name, size): make_layout(name, size)
                   for name in args.layouts for size in args.sizes}
        check_output_paths(args.output, pdf=not args.no_pdf, force=args.force)
        seed = args.seed if args.seed is not None else SystemRandom().randrange(2**32)
        rng = Random(seed)
        puzzles = []
        for index in range(args.count):
            name = args.layouts[index % len(args.layouts)]
            size = args.sizes[(index // len(args.layouts) + index % len(args.layouts)) % len(args.sizes)]
            difficulty = (DIFFICULTIES[min(2, index * 3 // args.count)]
                          if args.difficulty == "mixed" else args.difficulty)
            puzzle = generate(layouts[name, size], args.min_number, args.max_number,
                              difficulty, rng, attempts=args.attempts)
            puzzles.append(puzzle)
        paths = write_outputs(puzzles, seed, args.output, pdf=not args.no_pdf,
                              force=args.force, per_page=args.per_page, paper=args.paper)
    except (ValueError, OSError, GenerationError, RenderError) as error:
        print(f"diffsquares: {error}", file=sys.stderr)
        return 1
    print(f"Generated {len(puzzles)} uniquely solvable puzzles (seed {seed}).")
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
