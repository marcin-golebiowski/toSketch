# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for addHorizontalConstraints module."""
import math
import pytest
from conftest import MockVector, MockLineSegment, MockArcOfCircle, MockSketch, MockConstraint

from freecad.toSketch.addHorizontalConstraints import add_horizontal_constraints


# ── Helpers ──────────────────────────────────────────────────────
def _horizontal_count(sketch):
    return sum(1 for c in sketch.added_constraints if c.Type == 'Horizontal')


def _make_line(x1, y1, x2, y2):
    return MockLineSegment(MockVector(x1, y1), MockVector(x2, y2))


def _make_angled_line(angle_deg, length=10.0):
    """Create a line at a given angle from origin."""
    rad = math.radians(angle_deg)
    return MockLineSegment(
        MockVector(0, 0),
        MockVector(length * math.cos(rad), length * math.sin(rad)),
    )


# ── Basic detection ──────────────────────────────────────────────
class TestHorizontalBasic:

    def test_perfectly_horizontal_line(self):
        """dy=0 → Horizontal constraint."""
        sketch = MockSketch(geometry=[_make_line(0, 0, 10, 0)])
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 1

    def test_nearly_horizontal_within_tolerance(self):
        """0.3° off horizontal → constrained (default tol 0.5°)."""
        sketch = MockSketch(geometry=[_make_angled_line(0.3)])
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 1

    def test_nearly_horizontal_outside_tolerance(self):
        """1° off → no constraint."""
        sketch = MockSketch(geometry=[_make_angled_line(1.0)])
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 0

    def test_180_degree_line(self):
        """Right-to-left horizontal → still constrained."""
        sketch = MockSketch(geometry=[_make_line(10, 0, 0, 0)])
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 1

    def test_vertical_line_ignored(self):
        """90° line → not horizontal."""
        sketch = MockSketch(geometry=[_make_line(0, 0, 0, 10)])
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 0

    def test_diagonal_line_ignored(self):
        """45° line → not horizontal."""
        sketch = MockSketch(geometry=[_make_angled_line(45)])
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 0


# ── Multiple and mixed ───────────────────────────────────────────
class TestHorizontalMultiple:

    def test_multiple_horizontal_lines(self):
        """3 horizontal lines → 3 constraints."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(0, 5, 10, 5),
            _make_line(0, 10, 10, 10),
        ])
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 3

    def test_mixed_geometry(self):
        """Lines + arcs → only horizontal lines constrained."""
        arc = MockArcOfCircle(MockVector(5, 5), 5.0, MockVector(10, 5), MockVector(0, 5))
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),  # horizontal
            arc,                       # not a line
            _make_line(0, 0, 0, 10),  # vertical
        ])
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 1


# ── Tolerance and duplicates ─────────────────────────────────────
class TestHorizontalTolerance:

    def test_custom_tolerance(self):
        """Wider tolerance (2°) catches a 1.5° line."""
        sketch = MockSketch(geometry=[_make_angled_line(1.5)])
        add_horizontal_constraints(sketch, angle_tolerance_deg=2.0)
        assert _horizontal_count(sketch) == 1

    def test_duplicate_avoidance(self):
        """Pre-existing Horizontal → not re-added."""
        existing = MockConstraint('Horizontal', 0)
        sketch = MockSketch(
            geometry=[_make_line(0, 0, 10, 0)],
            constraints=[existing],
        )
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 0

    def test_idempotent(self):
        """Running twice adds nothing the second time."""
        sketch = MockSketch(geometry=[_make_line(0, 0, 10, 0)])
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 1
        sketch.added_constraints.clear()
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 0


# ── Edge cases ───────────────────────────────────────────────────
class TestHorizontalEdgeCases:

    def test_empty_sketch(self):
        sketch = MockSketch(geometry=[])
        add_horizontal_constraints(sketch)
        assert _horizontal_count(sketch) == 0

    def test_invalid_sketch_type(self):
        with pytest.raises(ValueError):
            add_horizontal_constraints(None)
