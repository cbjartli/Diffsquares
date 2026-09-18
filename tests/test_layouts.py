from math import hypot
import unittest

from diffsquares.layouts import LAYOUT_NAMES, edge_contact, make_layout, overlapping, sides


class LayoutTests(unittest.TestCase):
    def test_regular_polygons_and_exactly_the_intended_shared_sides(self):
        for name in LAYOUT_NAMES:
            for size in (6, 8, 12, 16):
                with self.subTest(name=name, size=size):
                    layout = make_layout(name, size)
                    self.assertEqual(len(layout.squares), size)
                    self.assertEqual(len(layout.triangles), size if name == "loop" else size - 1)
                    for polygon in layout.polygons:
                        for a, b in sides(polygon):
                            self.assertAlmostEqual(hypot(a[0] - b[0], a[1] - b[1]), 1)
                        if len(polygon) == 4:
                            a, b, c, _ = polygon
                            self.assertAlmostEqual(
                                (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]), 0)
                    contacts = set()
                    for i, a in enumerate(layout.polygons):
                        for j, b in enumerate(layout.polygons[:i]):
                            self.assertFalse(overlapping(a, b), (name, size, i, j))
                            if edge_contact(a, b):
                                contacts.add((i, j))
                    expected = {(size + i, end) for i, edge in enumerate(layout.edges) for end in edge}
                    self.assertEqual(contacts, expected)

    def test_graph_shapes_and_connectivity(self):
        for name in LAYOUT_NAMES:
            layout = make_layout(name, 10)
            neighbors = [set() for _ in layout.squares]
            for a, b in layout.edges:
                neighbors[a].add(b)
                neighbors[b].add(a)
            reached = {0}
            while True:
                expanded = reached | {j for i in reached for j in neighbors[i]}
                if expanded == reached:
                    break
                reached = expanded
            self.assertEqual(len(reached), 10)
            if name == "chain":
                self.assertEqual(sorted(map(len, neighbors)), [1, 1] + [2] * 8)
            elif name == "branch":
                self.assertEqual(len(neighbors[0]), 3)
            else:
                self.assertEqual(len(layout.edges), len(layout.squares))

    def test_layout_validation_and_minimum_sizes(self):
        for name, minimum in (("chain", 2), ("branch", 4), ("loop", 6)):
            self.assertEqual(len(make_layout(name, minimum).squares), minimum)
            with self.assertRaises(ValueError):
                make_layout(name, minimum - 1)
        with self.assertRaises(ValueError):
            make_layout("unknown", 6)


if __name__ == "__main__":
    unittest.main()
