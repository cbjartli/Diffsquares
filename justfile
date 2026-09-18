set positional-arguments

python := "python3"

# List available tasks.
default:
    @just --list

# Show all generator options.
help:
    "{{python}}" -m diffsquares --help

# Generate worksheets; pass any generator options after the task name.
generate *args:
    "{{python}}" -m diffsquares "$@"

# Reproduce the original 12-puzzle sample and answer key.
sample *args:
    "{{python}}" -m diffsquares --seed 42 --output worksheets/sample "$@"

# Generate eight short, easy chains with square numbers from 1 to 15.
warmups *args:
    "{{python}}" -m diffsquares --count 8 --layouts chain --sizes 3,4,5,6 --max-number 15 --difficulty easy --seed 123 --output worksheets/warmups "$@"

# Generate nine longer, hard puzzles with square numbers from 1 to 50.
challenges *args:
    "{{python}}" -m diffsquares --count 9 --sizes 8,10,12 --difficulty hard --max-number 50 --seed 456 --output worksheets/challenges "$@"

# Generate US Letter worksheets with two puzzles per page.
large-print *args:
    "{{python}}" -m diffsquares --paper letter --per-page 2 --seed 789 --output worksheets/large-print "$@"

# Generate LaTeX and JSON only, without running pdflatex.
sources *args:
    "{{python}}" -m diffsquares --no-pdf --seed 42 --output worksheets/source-only "$@"

# Run the test suite; optional unittest discovery flags are forwarded.
test *args:
    "{{python}}" -m unittest discover -s tests -v "$@"
