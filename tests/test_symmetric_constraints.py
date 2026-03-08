# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for symmetricConstraints module (add_symmetric_constraints only)."""
import pytest
from conftest import (MockVector, MockLineSegment, MockArcOfCircle, MockCircle,
                      MockPoint, MockSketch, MockConstraint)

from freecad.toSketch.symmetricConstraints import add_symmetric_constraints


# ── Helpers ──────────────────────────────────────────────────────
def _symmetric_count(sketch):
    return sum(1 for c in sketch.added_constraints if c.Type == 'Symmetric')


def _make_line(x1, y1, x2, y2):
    return MockLineSegment(MockVector(x1, y1), MockVector(x2, y2))


# ── Lines symmetric about axes ───────────────────────────────────
class TestSymmetricLines:

    def test_two_lines_symmetric_about_y_axis(self):
        """Lines mirrored about Y-axis → Symmetric constraints on start+end."""
        sketch = MockSketch(geometry=[
            _make_line(5, 0, 5, 10),    # right of Y-axis
            _make_line(-5, 0, -5, 10),  # mirror left
        ])
        add_symmetric_constraints(sketch)
        # Each pair of lines adds 2 Symmetric constraints (start + end)
        assert _symmetric_count(sketch) == 2

    def test_two_lines_symmetric_about_x_axis(self):
        """Lines mirrored about X-axis → Symmetric constraints."""
        sketch = MockSketch(geometry=[
            _make_line(0, 5, 10, 5),    # above X-axis
            _make_line(0, -5, 10, -5),  # mirror below
        ])
        add_symmetric_constraints(sketch)
        assert _symmetric_count(sketch) == 2

    def test_lines_not_symmetric(self):
        """Asymmetric lines → no constraint."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(3, 7, 15, 7),
        ])
        add_symmetric_constraints(sketch)
        assert _symmetric_count(sketch) == 0


# ── Arcs/circles symmetric ──────────────────────────────────────
class TestSymmetricArcs:

    def test_arcs_symmetric_about_y_axis(self):
        """Arcs with mirrored centers and equal radii → Symmetric."""
        sketch = MockSketch(geometry=[
            MockArcOfCircle(MockVector(5, 0), 3.0, MockVector(8, 0), MockVector(5, 3)),
            MockArcOfCircle(MockVector(-5, 0), 3.0, MockVector(-8, 0), MockVector(-5, 3)),
        ])
        add_symmetric_constraints(sketch)
        assert _symmetric_count(sketch) == 1

    def test_arcs_different_radii(self):
        """Mirrored centers but different radii → no constraint."""
        sketch = MockSketch(geometry=[
            MockArcOfCircle(MockVector(5, 0), 3.0, MockVector(8, 0), MockVector(5, 3)),
            MockArcOfCircle(MockVector(-5, 0), 5.0, MockVector(-10, 0), MockVector(-5, 5)),
        ])
        add_symmetric_constraints(sketch)
        assert _symmetric_count(sketch) == 0

    def test_circles_symmetric(self):
        """Two circles mirrored about Y-axis."""
        sketch = MockSketch(geometry=[
            MockCircle(MockVector(5, 0), 3.0),
            MockCircle(MockVector(-5, 0), 3.0),
        ])
        add_symmetric_constraints(sketch)
        assert _symmetric_count(sketch) == 1


# ── Points ───────────────────────────────────────────────────────
class TestSymmetricPoints:

    def test_points_symmetric(self):
        """Two points mirrored about Y-axis."""
        sketch = MockSketch(geometry=[
            MockPoint(5, 3),
            MockPoint(-5, 3),
        ])
        add_symmetric_constraints(sketch)
        assert _symmetric_count(sketch) == 1


# ── Mixed types and edge cases ───────────────────────────────────
class TestSymmetricEdgeCases:

    def test_mixed_types_not_matched(self):
        """Line + arc → types differ → not matched."""
        sketch = MockSketch(geometry=[
            _make_line(5, 0, 5, 10),
            MockArcOfCircle(MockVector(-5, 5), 5.0, MockVector(-10, 5), MockVector(0, 5)),
        ])
        add_symmetric_constraints(sketch)
        assert _symmetric_count(sketch) == 0

    def test_already_used_pair(self):
        """Pair matched on Y-axis → not re-checked on X-axis."""
        sketch = MockSketch(geometry=[
            _make_line(5, 0, 5, 10),
            _make_line(-5, 0, -5, 10),
        ])
        add_symmetric_constraints(sketch)
        # Should only be matched once (Y-axis is checked first)
        assert _symmetric_count(sketch) == 2  # 2 constraints for 1 line pair

    def test_custom_tolerance(self):
        """Tolerance parameter respected — tight tolerance rejects near-mirror."""
        sketch = MockSketch(geometry=[
            _make_line(5, 0, 5, 10),
            _make_line(-5.01, 0, -5.01, 10),
        ])
        add_symmetric_constraints(sketch, tol=1e-3)
        assert _symmetric_count(sketch) == 0

    def test_empty_sketch(self):
        sketch = MockSketch(geometry=[])
        add_symmetric_constraints(sketch)
        assert _symmetric_count(sketch) == 0

    def test_single_element(self):
        sketch = MockSketch(geometry=[_make_line(0, 0, 10, 0)])
        add_symmetric_constraints(sketch)
        assert _symmetric_count(sketch) == 0
