# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for addParallelConstraints module."""
import math
import pytest
from conftest import MockVector, MockLineSegment, MockArcOfCircle, MockSketch, MockConstraint

from freecad.toSketch.addParallelConstraints import add_parallel_constraints


# ── Helpers ──────────────────────────────────────────────────────
def _parallel_count(sketch):
    return sum(1 for c in sketch.added_constraints if c.Type == 'Parallel')


def _make_line(x1, y1, x2, y2):
    return MockLineSegment(MockVector(x1, y1), MockVector(x2, y2))


# ── Basic detection ──────────────────────────────────────────────
class TestParallelBasic:

    def test_two_parallel_horizontal_lines(self):
        """Both horizontal → Parallel constraint."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(0, 5, 10, 5),
        ])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 1

    def test_two_parallel_vertical_lines(self):
        """Both vertical → Parallel constraint."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 0, 10),
            _make_line(5, 0, 5, 10),
        ])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 1

    def test_two_parallel_diagonal_lines(self):
        """Same slope → Parallel constraint."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 10),
            _make_line(5, 0, 15, 10),
        ])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 1

    def test_antiparallel_lines(self):
        """Opposite direction (angle = pi) → still parallel."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(10, 5, 0, 5),
        ])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 1

    def test_perpendicular_lines(self):
        """90° difference → no constraint."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(0, 0, 0, 10),
        ])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 0


# ── Tolerance ────────────────────────────────────────────────────
class TestParallelTolerance:

    def test_nearly_parallel_within_tolerance(self):
        """Angle diff < 1e-3 rad → Parallel."""
        angle = 0.0005  # well within 1e-3
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(0, 5, 10, 5 + 10 * math.sin(angle)),
        ])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 1

    def test_nearly_parallel_outside_tolerance(self):
        """Angle diff > 1e-3 rad → no constraint."""
        angle = 0.01  # well beyond 1e-3
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(0, 5, 10, 5 + 10 * math.sin(angle)),
        ])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 0


# ── Multiple lines ───────────────────────────────────────────────
class TestParallelMultiple:

    def test_three_parallel_lines(self):
        """3 parallel lines → 3 pairwise constraints."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(0, 5, 10, 5),
            _make_line(0, 10, 10, 10),
        ])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 3

    def test_two_groups_of_parallel(self):
        """Horizontal pair + 45° pair → 2 constraints."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(0, 5, 10, 5),
            _make_line(0, 0, 10, 10),
            _make_line(5, 0, 15, 10),
        ])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 2


# ── Existing constraints ─────────────────────────────────────────
class TestParallelExisting:

    def test_skip_if_any_constraint_exists(self):
        """Pair with existing constraint → skipped."""
        existing = MockConstraint('Equal', 0, 1)
        sketch = MockSketch(
            geometry=[
                _make_line(0, 0, 10, 0),
                _make_line(0, 5, 10, 5),
            ],
            constraints=[existing],
        )
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 0


# ── Mixed geometry and edge cases ────────────────────────────────
class TestParallelEdgeCases:

    def test_mixed_geometry(self):
        """Lines + arcs → only line pairs checked."""
        arc = MockArcOfCircle(MockVector(5, 5), 5.0, MockVector(10, 5), MockVector(0, 5))
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            arc,
            _make_line(0, 5, 10, 5),
        ])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 1

    def test_empty_sketch(self):
        sketch = MockSketch(geometry=[])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 0

    def test_single_line(self):
        sketch = MockSketch(geometry=[_make_line(0, 0, 10, 0)])
        add_parallel_constraints(sketch)
        assert _parallel_count(sketch) == 0
