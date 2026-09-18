"""Edge-sharing regular polygons; the square graph supplies the puzzle rules."""

from collections.abc import Iterator
from dataclasses import dataclass
from math import cos, hypot, pi, sin, sqrt

Point = tuple[float, float]
Polygon = tuple[Point, ...]
EPS = 1e-8
LAYOUT_NAMES = ("chain", "branch", "loop")


@dataclass(frozen=True)
class Triangle:
    vertices: Polygon
    a: int
    b: int


@dataclass(frozen=True)
class Layout:
    name: str
    squares: tuple[Polygon, ...]
    triangles: tuple[Triangle, ...]

    @property
    def edges(self) -> tuple[tuple[int, int], ...]:
        return tuple((triangle.a, triangle.b) for triangle in self.triangles)

    @property
    def polygons(self) -> tuple[Polygon, ...]:
        return self.squares + tuple(t.vertices for t in self.triangles)


def center(polygon: Polygon) -> Point:
    return (sum(p[0] for p in polygon) / len(polygon),
            sum(p[1] for p in polygon) / len(polygon))


def sides(polygon: Polygon) -> list[tuple[Point, Point]]:
    return list(zip(polygon, polygon[1:] + polygon[:1]))


def overlapping(a: Polygon, b: Polygon) -> bool:
    """Separating-axis test: boundary-only contact is not an overlap."""
    for p, q in sides(a) + sides(b):
        nx, ny = q[1] - p[1], p[0] - q[0]
        ap = [x * nx + y * ny for x, y in a]
        bp = [x * nx + y * ny for x, y in b]
        if min(max(ap), max(bp)) - max(min(ap), min(bp)) < EPS:
            return False
    return True


def edge_contact(a: Polygon, b: Polygon) -> bool:
    for p, q in sides(a):
        dx, dy = q[0] - p[0], q[1] - p[1]
        for r, s in sides(b):
            if any(abs(dx * (v[1] - p[1]) - dy * (v[0] - p[0])) > EPS
                   for v in (r, s)):
                continue
            projections = [dx * (v[0] - p[0]) + dy * (v[1] - p[1])
                           for v in (r, s)]
            if min(dx * dx + dy * dy, max(projections)) - max(0, min(projections)) > EPS:
                return True
    return False


def _square_outside(a: Point, b: Point) -> Polygon:
    dx, dy = b[0] - a[0], b[1] - a[1]
    return (b, a, (a[0] + dy, a[1] - dx), (b[0] + dy, b[1] - dx))


def _attachments(layout: Layout, parent: int) -> Iterator[tuple[Polygon, Triangle]]:
    for a, b in sides(layout.squares[parent]):
        tip = ((a[0] + b[0]) / 2 + sqrt(3) / 2 * (b[1] - a[1]),
               (a[1] + b[1]) / 2 - sqrt(3) / 2 * (b[0] - a[0]))
        triangle = (b, a, tip)
        if any(overlapping(triangle, polygon)
               or (i != parent and edge_contact(triangle, polygon))
               for i, polygon in enumerate(layout.polygons)):
            continue
        for start, end in ((a, tip), (tip, b)):
            square = _square_outside(start, end)
            if any(overlapping(square, polygon) or edge_contact(square, polygon)
                   for polygon in layout.polygons):
                continue
            yield square, Triangle(triangle, parent, len(layout.squares))


def _add(layout: Layout, square: Polygon, triangle: Triangle) -> Layout:
    return Layout(layout.name, layout.squares + (square,), layout.triangles + (triangle,))


def _hexagonal_loop() -> Layout:
    hexagon = tuple((cos(i * pi / 3), sin(i * pi / 3)) for i in range(6))
    squares = tuple(_square_outside(a, b) for a, b in sides(hexagon))
    triangles = tuple(
        Triangle((hexagon[i], squares[i][2], squares[(i - 1) % 6][3]),
                 (i - 1) % 6, i)
        for i in range(6)
    )
    return Layout("loop", squares, triangles)


def make_layout(name: str, size: int) -> Layout:
    if name not in LAYOUT_NAMES:
        raise ValueError(f"Unknown layout: {name}")
    minimum = {"chain": 2, "branch": 4, "loop": 6}[name]
    if size < minimum:
        raise ValueError(f"{name} layouts need at least {minimum} squares (got {size})")
    if name == "loop":
        layout = _hexagonal_loop()
        depths = [0] * 6
    else:
        layout = Layout(name, (((0., 0.), (1., 0.), (1., 1.), (0., 1.)),), ())
        depths = [0]

    while len(layout.squares) < size:
        degrees = [0] * len(layout.squares)
        for a, b in layout.edges:
            degrees[a] += 1
            degrees[b] += 1
        if name == "chain":
            parents = [len(layout.squares) - 1]
        elif name == "branch" and degrees[0] < 3:
            parents = [0]
        else:
            parents = sorted(
                (i for i, degree in enumerate(degrees) if degree < (3 if name == "loop" else 2)),
                key=lambda i: (depths[i], i),
            )
        chosen = None
        for parent in parents:
            candidates = list(_attachments(layout, parent))
            if not candidates:
                continue
            if name == "chain":
                chosen = max(candidates, key=lambda pair: (
                    center(pair[0])[0], -abs(center(pair[0])[1] - .5)))
            else:
                origin = (.5, .5) if name == "branch" else (0., 0.)
                chosen = max(candidates, key=lambda pair: hypot(
                    center(pair[0])[0] - origin[0], center(pair[0])[1] - origin[1]))
            depths.append(depths[parent] + 1)
            break
        if chosen is None:
            raise ValueError(f"Cannot extend the {name} layout to {size} squares without overlaps")
        layout = _add(layout, *chosen)
    return layout
