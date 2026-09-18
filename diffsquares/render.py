"""LaTeX output and machine-readable puzzles; no Python rendering dependencies."""

from dataclasses import asdict
from pathlib import Path
import json
import subprocess
import tempfile

from .generator import Puzzle
from .layouts import center

LABELS = {"easy": "Warm-up", "medium": "Tricky", "hard": "Challenge"}


class RenderError(RuntimeError):
    pass


def _diagram(puzzle: Puzzle, width_mm: float, height_mm: float, answers: bool) -> str:
    points = [p for polygon in puzzle.layout.polygons for p in polygon]
    width = max(p[0] for p in points) - min(p[0] for p in points)
    height = max(p[1] for p in points) - min(p[1] for p in points)
    unit = min(12., (width_mm - 2) / width, (height_mm - 2) / height)
    font_size = min(13., unit * 1.1)
    lines = [
        rf"\begin{{tikzpicture}}[x={unit:.3f}mm,y={unit:.3f}mm,"
        rf"line width=.55pt,line join=round,every node/.style={{inner sep=0pt,"
        rf"font=\sffamily\fontsize{{{font_size:.2f}}}{{{font_size + 1:.2f}}}\selectfont}}]"
    ]
    groups = (
        (puzzle.layout.squares, puzzle.square_clues, puzzle.square_solution, "white"),
        (tuple(t.vertices for t in puzzle.layout.triangles),
         puzzle.triangle_clues, puzzle.triangle_solution, "black!5"),
    )
    for polygons, clues, solutions, fill in groups:
        for polygon, clue, solution in zip(polygons, clues, solutions):
            path = " -- ".join(f"({x:.6f},{y:.6f})" for x, y in polygon)
            lines.append(rf"\draw[fill={fill}] {path} -- cycle;")
            value = solution if answers else clue
            if value is not None:
                x, y = center(polygon)
                color = "blue!65!black" if answers and clue is None else "black"
                text_scale = min(1., 2 / len(str(value)))
                lines.append(rf"\node[text={color},scale={text_scale:.3f}] "
                             rf"at ({x:.6f},{y:.6f}) {{{value}}};")
    lines.append(r"\end{tikzpicture}")
    return "\n".join(lines)


def latex(puzzles: list[Puzzle], seed: int, *, answers: bool = False,
          per_page: int = 3, paper: str = "a4") -> str:
    if not puzzles:
        raise ValueError("A worksheet needs at least one puzzle")
    if per_page not in (1, 2, 3, 4) or paper not in ("a4", "letter"):
        raise ValueError("Invalid page configuration")
    minimum, maximum = puzzles[0].minimum, puzzles[0].maximum
    if any((p.minimum, p.maximum) != (minimum, maximum) for p in puzzles):
        raise ValueError("All puzzles on a worksheet must use the same number range")
    width, height = (210., 297.) if paper == "a4" else (215.9, 279.4)
    row_height = (height - 28 - 31) / per_page
    title = r"Square \& Triangle Puzzles" + (" -- Answers" if answers else "")
    lines = [
        rf"\documentclass[11pt,{paper}paper]{{article}}",
        r"\usepackage[margin=14mm]{geometry}",
        r"\usepackage{tikz}",
        r"\pagestyle{empty}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{0pt}",
        r"\begin{document}",
    ]
    page_count = (len(puzzles) + per_page - 1) // per_page
    for i, puzzle in enumerate(puzzles):
        if i % per_page == 0:
            if i:
                lines.append(r"\newpage")
            lines.extend([
                rf"{{\Large\bfseries {title}}}\par\smallskip",
                rf"{{\small Fill every blank. Squares are whole numbers from {minimum} to {maximum}.",
                r"Numbers may repeat.\par",
                r"Each triangle is the larger adjacent square minus the smaller: $|a-b|$.",
                r"Triangle numbers must be greater than zero.}\par\smallskip",
                rf"{{\footnotesize Set {seed} \hfill Page {i // per_page + 1} of {page_count}}}",
                r"\par\medskip",
            ])
        description = (f"{i + 1}. {LABELS[puzzle.difficulty]} "
                       f"--- {puzzle.layout.name}, {len(puzzle.layout.squares)} squares")
        lines.extend([
            rf"\begin{{minipage}}[t][{row_height:.2f}mm][t]{{\textwidth}}",
            rf"{{\bfseries {description}}}",
        ])
        if answers:
            report = puzzle.reasoning
            lines.append(
                rf"\hfill {{\scriptsize Trial depth: {report.max_trial_depth}; "
                rf"alternatives tested: {report.alternatives_tested}}}"
            )
        lines.extend([
            r"\par\smallskip",
            r"\begin{center}",
            _diagram(puzzle, width - 28, row_height - 17, answers),
            r"\end{center}",
            r"\end{minipage}\par",
        ])
    lines.extend([r"\end{document}", ""])
    return "\n".join(lines)


def json_data(puzzles: list[Puzzle], seed: int) -> str:
    data = {
        "schema_version": 1,
        "seed": seed,
        "rule": "Each triangle is the strictly positive absolute difference of its two squares.",
        "puzzles": [
            {
                "number": i + 1,
                "layout": puzzle.layout.name,
                "square_range": [puzzle.minimum, puzzle.maximum],
                "difficulty": puzzle.difficulty,
                "reasoning": asdict(puzzle.reasoning),
                "square_clues": puzzle.square_clues,
                "triangle_clues": puzzle.triangle_clues,
                "square_solution": puzzle.square_solution,
                "triangle_solution": puzzle.triangle_solution,
                "squares": puzzle.layout.squares,
                "triangles": [asdict(t) for t in puzzle.layout.triangles],
            }
            for i, puzzle in enumerate(puzzles)
        ],
    }
    return json.dumps(data, indent=2) + "\n"


def output_paths(prefix: Path, pdf: bool) -> list[Path]:
    suffixes = [".tex", "-answers.tex", ".json"]
    if pdf:
        suffixes += [".pdf", "-answers.pdf"]
    return [prefix.with_name(prefix.name + suffix) for suffix in suffixes]


def check_output_paths(prefix: Path, *, pdf: bool, force: bool) -> None:
    for target in output_paths(prefix, pdf):
        if target.exists() and (not force or not target.is_file()):
            raise FileExistsError(f"Output already exists: {target}. Choose another prefix or use --force.")
    if not pdf:
        for target in output_paths(prefix, True)[-2:]:
            if target.exists():
                raise FileExistsError(
                    f"{target} would become a stale answer/worksheet. "
                    "Choose another prefix or omit --no-pdf to regenerate the PDFs too."
                )


def write_outputs(puzzles: list[Puzzle], seed: int, prefix: Path, *,
                  pdf: bool = True, force: bool = False, per_page: int = 3,
                  paper: str = "a4") -> list[Path]:
    check_output_paths(prefix, pdf=pdf, force=force)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    targets = output_paths(prefix, pdf)
    with tempfile.TemporaryDirectory(prefix=".diffsquares-", dir=prefix.parent) as temporary:
        stage = Path(temporary)
        worksheet = stage / "puzzles.tex"
        answers = stage / "answers.tex"
        metadata = stage / "puzzles.json"
        worksheet.write_text(latex(puzzles, seed, per_page=per_page, paper=paper), encoding="utf-8")
        answers.write_text(latex(puzzles, seed, answers=True, per_page=per_page, paper=paper),
                           encoding="utf-8")
        metadata.write_text(json_data(puzzles, seed), encoding="utf-8")
        sources = [worksheet, answers, metadata]
        if pdf:
            for source in (worksheet, answers):
                try:
                    completed = subprocess.run(
                        ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode",
                         "-halt-on-error", source.name],
                        cwd=stage, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace", timeout=120,
                    )
                except FileNotFoundError as error:
                    raise RenderError(
                        "pdflatex was not found. Install a LaTeX distribution with TikZ "
                        "or use --no-pdf to generate the sources only."
                    ) from error
                except subprocess.TimeoutExpired as error:
                    raise RenderError(f"pdflatex timed out while compiling {source.name}") from error
                if completed.returncode:
                    tail = "\n".join(completed.stdout.splitlines()[-25:])
                    raise RenderError(f"pdflatex failed for {source.name}:\n{tail}")
            sources.extend([worksheet.with_suffix(".pdf"), answers.with_suffix(".pdf")])
        for source, target in zip(sources, targets):
            source.replace(target)
    return targets
