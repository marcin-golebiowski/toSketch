# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for addEqualConstraints module."""
import sys
import os
import math
import pytest

# Ensure conftest mocks are loaded and source is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'freecad', 'toSketch'))

from conftest import MockVector as V, MockLineSegment, MockArcOfCircle, MockCircle, MockSketch, MockConstraint
from addEqualConstraints import add_equal_constraints


# ──────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────
def make_line(x1, y1, x2, y2):
    return MockLineSegment(V(x1, y1), V(x2, y2))


def make_arc(cx, cy, r, sx, sy, ex, ey):
    return MockArcOfCircle(V(cx, cy), r, V(sx, sy), V(ex, ey))


def make_circle(cx, cy, r):
    return MockCircle(V(cx, cy), r)


# ──────────────────────────────────────────────────────────────────
# Validation tests
# ──────────────────────────────────────────────────────────────────
class TestValidation:
    def test_none_sketch_raises(self):
        with pytest.raises(ValueError, match="valid Sketcher"):
            add_equal_constraints(None)

    def test_wrong_type_raises(self):
        sketch = MockSketch()
        sketch.TypeId = 'Part::Feature'
        with pytest.raises(ValueError, match="valid Sketcher"):
            add_equal_constraints(sketch)


# ──────────────────────────────────────────────────────────────────
# Equal-length line tests
# ──────────────────────────────────────────────────────────────────
class TestEqualLines:
    def test_two_equal_length_lines(self):
        """Two lines of exactly equal length -> 1 Equal constraint."""
        geo = [
            make_line(0, 0, 10, 0),  # length=10
            make_line(0, 5, 10, 5),  # length=10
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 1
        c = sketch.added_constraints[0]
        assert c.Type == 'Equal'
        assert {c.First, c.Second} == {0, 1}

    def test_two_different_length_lines(self):
        """Two lines of clearly different length -> no constraint."""
        geo = [
            make_line(0, 0, 10, 0),  # length=10
            make_line(0, 5, 5, 5),   # length=5
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_nearly_equal_length_within_tolerance(self):
        """Lines within 1e-3 tolerance -> Equal constraint added."""
        geo = [
            make_line(0, 0, 10, 0),          # length=10.0
            make_line(0, 5, 10.0005, 5),      # length≈10.0005, diff < 1e-3
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 1

    def test_nearly_equal_length_outside_tolerance(self):
        """Lines just outside 1e-3 tolerance -> no constraint."""
        geo = [
            make_line(0, 0, 10, 0),        # length=10.0
            make_line(0, 5, 10.002, 5),     # length≈10.002, diff > 1e-3
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_three_equal_lines_pairwise(self):
        """Three equal-length lines -> 3 pairwise Equal constraints."""
        geo = [
            make_line(0, 0, 10, 0),
            make_line(0, 5, 10, 5),
            make_line(0, 10, 10, 10),
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 3  # (0,1), (0,2), (1,2)

    def test_diagonal_lines_equal(self):
        """Diagonal lines with equal length -> Equal constraint."""
        geo = [
            make_line(0, 0, 3, 4),   # length=5
            make_line(5, 5, 8, 9),   # length=5
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 1

    def test_mixed_lengths_partial_match(self):
        """Four lines: two of length 10, two of length 5 -> 2 Equal constraints."""
        geo = [
            make_line(0, 0, 10, 0),  # 10
            make_line(0, 5, 5, 5),   # 5
            make_line(0, 10, 10, 10), # 10
            make_line(0, 15, 5, 15),  # 5
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 2
        types_and_pairs = [(c.Type, frozenset({c.First, c.Second}))
                           for c in sketch.added_constraints]
        assert ('Equal', frozenset({0, 2})) in types_and_pairs
        assert ('Equal', frozenset({1, 3})) in types_and_pairs

    def test_custom_tolerance(self):
        """Custom tolerance allows wider matching."""
        geo = [
            make_line(0, 0, 10, 0),      # length=10
            make_line(0, 5, 10.05, 5),    # length≈10.05
        ]
        sketch = MockSketch(geometry=geo)
        # Default tolerance (1e-3) should miss this
        add_equal_constraints(sketch, length_tolerance=1e-3)
        assert len(sketch.added_constraints) == 0

        sketch2 = MockSketch(geometry=geo)
        # Wider tolerance should catch it
        add_equal_constraints(sketch2, length_tolerance=0.1)
        assert len(sketch2.added_constraints) == 1


# ──────────────────────────────────────────────────────────────────
# Equal-radius arc/circle tests
# ──────────────────────────────────────────────────────────────────
class TestEqualArcs:
    def test_two_equal_radius_arcs(self):
        """Two arcs with same radius -> 1 Equal constraint."""
        geo = [
            make_arc(0, 0, 5.0, -5, 0, 0, 5),
            make_arc(10, 0, 5.0, 5, 0, 10, 5),
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 1
        assert sketch.added_constraints[0].Type == 'Equal'

    def test_two_different_radius_arcs(self):
        """Two arcs with different radii -> no constraint."""
        geo = [
            make_arc(0, 0, 5.0, -5, 0, 0, 5),
            make_arc(10, 0, 8.0, 2, 0, 10, 8),
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_two_equal_circles(self):
        """Two circles with same radius -> 1 Equal constraint."""
        geo = [
            make_circle(0, 0, 3.0),
            make_circle(10, 10, 3.0),
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 1

    def test_circle_and_arc_equal_radius(self):
        """A circle and an arc with equal radius -> 1 Equal constraint."""
        geo = [
            make_circle(0, 0, 5.0),
            make_arc(10, 0, 5.0, 5, 0, 10, 5),
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 1

    def test_nearly_equal_radius_within_tolerance(self):
        """Arcs with radii within 1e-3 -> Equal constraint."""
        geo = [
            make_arc(0, 0, 5.0, -5, 0, 0, 5),
            make_arc(10, 0, 5.0005, 4.9995, 0, 10, 5.0005),
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 1

    def test_three_equal_radius_circles(self):
        """Three equal circles -> 3 pairwise constraints."""
        geo = [
            make_circle(0, 0, 4.0),
            make_circle(10, 0, 4.0),
            make_circle(20, 0, 4.0),
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 3


# ──────────────────────────────────────────────────────────────────
# Mixed geometry tests
# ──────────────────────────────────────────────────────────────────
class TestMixedGeometry:
    def test_lines_and_arcs_independent(self):
        """Equal lines and equal arcs are constrained independently (no cross-type)."""
        geo = [
            make_line(0, 0, 10, 0),   # line length=10
            make_line(0, 5, 10, 5),   # line length=10
            make_arc(0, 0, 10.0, -10, 0, 0, 10),   # arc radius=10
            make_arc(20, 0, 10.0, 10, 0, 20, 10),  # arc radius=10
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 2
        # One for lines, one for arcs
        line_pair = [c for c in sketch.added_constraints if c.First in (0, 1)]
        arc_pair = [c for c in sketch.added_constraints if c.First in (2, 3)]
        assert len(line_pair) == 1
        assert len(arc_pair) == 1

    def test_empty_sketch(self):
        """Empty sketch -> no constraints, no errors."""
        sketch = MockSketch(geometry=[])
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_single_line_no_constraint(self):
        """Single line -> no Equal constraint possible."""
        geo = [make_line(0, 0, 10, 0)]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 0


# ──────────────────────────────────────────────────────────────────
# Duplicate-avoidance tests
# ──────────────────────────────────────────────────────────────────
class TestDuplicateAvoidance:
    def test_existing_equal_constraint_skipped(self):
        """Pre-existing Equal constraint between pair -> no duplicate."""
        geo = [
            make_line(0, 0, 10, 0),
            make_line(0, 5, 10, 5),
        ]
        existing = [MockConstraint('Equal', 0, 1)]
        sketch = MockSketch(geometry=geo, constraints=existing)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_existing_equal_reversed_pair_skipped(self):
        """Existing Equal(1, 0) should still prevent adding Equal(0, 1)."""
        geo = [
            make_line(0, 0, 10, 0),
            make_line(0, 5, 10, 5),
        ]
        existing = [MockConstraint('Equal', 1, 0)]
        sketch = MockSketch(geometry=geo, constraints=existing)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_other_constraint_type_does_not_block(self):
        """Existing Parallel constraint between pair does NOT block Equal."""
        geo = [
            make_line(0, 0, 10, 0),
            make_line(0, 5, 10, 5),
        ]
        existing = [MockConstraint('Parallel', 0, 1)]
        sketch = MockSketch(geometry=geo, constraints=existing)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 1

    def test_running_twice_no_duplicates(self):
        """Running add_equal_constraints twice on same sketch -> no new constraints."""
        geo = [
            make_line(0, 0, 10, 0),
            make_line(0, 5, 10, 5),
        ]
        sketch = MockSketch(geometry=geo)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == 1
        first_count = len(sketch.added_constraints)
        add_equal_constraints(sketch)
        assert len(sketch.added_constraints) == first_count  # no new ones
