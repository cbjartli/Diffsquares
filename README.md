# Square & Triangle Puzzles

Generate original, printable arithmetic puzzles: every triangle shares a side
with **exactly two squares**, and its number is the **positive difference**
between those square numbers. Fill in all the missing numbers.

The generator makes straight-ish chains, branching shapes, and hexagonal loops
(with additional arms for larger puzzles). Every square and triangle is drawn
to scale, with genuinely shared sides and no overlapping interiors.

## Generate a worksheet

Requires Python 3.10+ with **no third-party Python dependencies**. PDF output
also needs `pdflatex`, TikZ, and the geometry package. On Debian/Ubuntu these
are provided by `texlive-latex-base`, `texlive-latex-recommended`, and
`texlive-pictures`.

From this directory:

```sh
python3 -m diffsquares --seed 42
```

This creates 12 puzzles, progressing from warm-ups to challenges:

- `worksheets/puzzles.pdf`: printable worksheet, three puzzles per A4 page.
- `worksheets/puzzles-answers.pdf`: separate answer key; added numbers are blue.
- Matching `.tex` files: editable LaTeX/TikZ sources.
- `worksheets/puzzles.json`: clues, geometry, **solutions**, seed, and difficulty measurements.

Use a new `--output` prefix for another set, or `--force` to replace existing
outputs. Compilation happens in a temporary directory; a failed generation or
compilation does not replace existing outputs.

```sh
# Short warm-up chains, square numbers from 1 to 15.
python3 -m diffsquares --count 8 --layouts chain --sizes 3,4,5,6 \
  --max-number 15 --difficulty easy --seed 123 --output worksheets/warmups

# Longer, challenging puzzles, including branching shapes and loops.
python3 -m diffsquares --count 9 --sizes 8,10,12 --difficulty hard \
  --max-number 50 --seed 456 --output worksheets/challenges

# US Letter, with larger spaces for writing.
python3 -m diffsquares --paper letter --per-page 2 --seed 789 \
  --output worksheets/large-print

# Generate only the editable sources and JSON, without requiring LaTeX.
python3 -m diffsquares --no-pdf --seed 42 --output worksheets/source-only

python3 -m diffsquares --help
```

`--sizes` counts **squares**, not all shapes. Chains need at least 2 squares,
branches at least 4, and loops at least 6. Every requested size must work with
every requested layout. Sizes and layouts rotate through the worksheet.
`--min-number` and `--max-number` set the inclusive square range (default 1-30).
Triangles can be 1 through the difference between those bounds, regardless of
`--min-number`. Nonadjacent squares may repeat; adjacent squares cannot, because
zero differences are forbidden.

The same seed **and options** reproduce the same puzzles with this version of
the generator. PDF metadata need not be byte-for-byte identical.

## Task shortcuts

If [just](https://just.systems/) is installed, the `justfile` provides shortcuts:

```sh
just                          # List tasks.
just help                     # Show generator options.
just generate --seed 123       # Generate a standard mixed worksheet.
just sample --force           # Rebuild the original sample and answer key.
just warmups                  # Short, easy chains.
just challenges               # Longer, hard puzzles.
just large-print              # US Letter, two puzzles per page.
just sources                  # LaTeX and JSON only; no LaTeX installation needed.
just test                     # Run the test suite.
```

Generation tasks accept additional CLI options, which override their presets:

```sh
just warmups --seed 999 --max-number 20 --output "worksheets/new warmups"
just test -k solver
```

Existing outputs remain protected: use `--force` to replace them, or choose a
new `--output` prefix. To select another Python interpreter, use
`just --set python /path/to/python test` (or any other task).

## Uniqueness and difficulty

**Uniqueness is checked, not assumed.** Clues are removed only when an exact
constraint solver proves that just one assignment remains within the printed
number range. Missing triangle numbers then follow uniquely from the squares.
The printed range is part of the puzzle: it can rule out alternatives.

Difficulty is **not the number of blanks**. A separate reference solver uses
this strategy:

1. Use filled squares and triangle clues to find candidates for neighboring
   squares; place numbers whenever only one candidate remains.
2. When stuck, choose a square with the fewest candidates and test alternatives.
3. Follow each alternative, making further trials if needed, until it either
   contradicts a clue or gives a complete solution.

| CLI setting | Worksheet label | Required reasoning under this strategy |
|---|---|---|
| `easy` | Warm-up | Direct deductions; no trial placements |
| `medium` | Tricky | Trials needed, but no nested trials |
| `hard` | Challenge | At least two levels of nested trials |
| `mixed` | All three | An approximately even mix, ordered by difficulty |

For example, a square containing 12 next to a triangle containing 7 leaves two
possible neighboring squares: 5 or 19. Another part of the puzzle may eliminate
one choice. Checking these alternatives is intentional, not a flaw in uniqueness.

These levels are a **reproducible estimate**, not a claim about the only or
shortest human solution. A clever global observation may beat the reference
strategy. The answer key reports maximum trial depth and alternatives tested;
JSON also records forced placements and contradictions across all tested branches.

Some combinations (especially very small ranges or short hard puzzles) cannot
meet the requested level. The generator reports failure rather than silently
substituting an easier or ambiguous puzzle. Increase the size, range, or
`--attempts` budget, or choose an easier level.

LaTeX is the final drawing format, while Python handles geometry, randomness,
and solving. This keeps the worksheet easy to edit without trying to implement
a puzzle solver in TeX. No external service is used.

## Development

```sh
python3 -m unittest discover -s tests -v
```

The library separates layouts, constraint solving, clue generation, and rendering.
Triangle endpoints and geometry indices in JSON are zero-based; displayed puzzle
numbers are one-based. The `.json` file contains answers and should not be given
to the student.
