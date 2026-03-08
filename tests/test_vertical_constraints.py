# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for addVerticalConstraints module."""
import math
import pytest
from conftest import MockVector, MockLineSegment, MockArcOfCircle, MockSketch, MockConstraint

from freecad.toSketch.addVerticalConstraints import add_vertical_constraints


# ── Helpers ──────────────────────────────────────────────────────
def _vertical_count(sketch):
    return sum(1 for c in sketch.added_constraints if c.Type == 'Vertical')


def _make_line(x1, y1, x2, y2):
    return MockLineSegment(MockVector(x1, y1), MockVector(x2, y2))


def _make_angled_line(angle_deg, length=10.0):
    rad = math.radians(angle_deg)
    return MockLineSegment(
        MockVector(0, 0),
        MockVector(length * math.cos(rad), length * math.sin(rad)),
    )


# ── Basic detection ──────────────────────────────────────────────
class TestVerticalBasic:

    def test_perfectly_vertical_line(self):
        """dx=0 → Vertical constraint."""
        sketch = MockSketch(geometry=[_make_line(0, 0, 0, 10)])
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 1

    def test_nearly_vertical_within_tolerance(self):
        """0.3° off vertical → constrained."""
        sketch = MockSketch(geometry=[_make_angled_line(90 - 0.3)])
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 1

    def test_nearly_vertical_outside_tolerance(self):
        """1° off vertical → no constraint."""
        sketch = MockSketch(geometry=[_make_angled_line(90 - 1.0)])
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 0

    def test_downward_vertical(self):
        """Top-to-bottom vertical → still constrained."""
        sketch = MockSketch(geometry=[_make_line(0, 10, 0, 0)])
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 1

    def test_horizontal_line_ignored(self):
        """0° line → not vertical."""
        sketch = MockSketch(geometry=[_make_line(0, 0, 10, 0)])
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 0

    def test_diagonal_line_ignored(self):
        """45° line → not vertical."""
        sketch = MockSketch(geometry=[_make_angled_line(45)])
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 0


# ── Multiple and mixed ───────────────────────────────────────────
class TestVerticalMultiple:

    def test_multiple_vertical_lines(self):
        """3 vertical lines → 3 constraints."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 0, 10),
            _make_line(5, 0, 5, 10),
            _make_line(10, 0, 10, 10),
        ])
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 3

    def test_mixed_geometry(self):
        """Lines + arcs → only vertical lines constrained."""
        arc = MockArcOfCircle(MockVector(5, 5), 5.0, MockVector(10, 5), MockVector(0, 5))
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 0, 10),  # vertical
            arc,                       # not a line
            _make_line(0, 0, 10, 0),  # horizontal
        ])
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 1


# ── Tolerance and duplicates ─────────────────────────────────────
class TestVerticalTolerance:

    def test_custom_tolerance(self):
        """Wider tolerance (2°) catches a 1.5° off-vertical line."""
        sketch = MockSketch(geometry=[_make_angled_line(90 - 1.5)])
        add_vertical_constraints(sketch, angle_tolerance_deg=2.0)
        assert _vertical_count(sketch) == 1

    def test_duplicate_avoidance(self):
        """Pre-existing Vertical → not re-added."""
        existing = MockConstraint('Vertical', 0)
        sketch = MockSketch(
            geometry=[_make_line(0, 0, 0, 10)],
            constraints=[existing],
        )
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 0

    def test_idempotent(self):
        """Running twice adds nothing the second time."""
        sketch = MockSketch(geometry=[_make_line(0, 0, 0, 10)])
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 1
        sketch.added_constraints.clear()
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 0


# ── Edge cases ───────────────────────────────────────────────────
class TestVerticalEdgeCases:

    def test_empty_sketch(self):
        sketch = MockSketch(geometry=[])
        add_vertical_constraints(sketch)
        assert _vertical_count(sketch) == 0

    def test_invalid_sketch_type(self):
        with pytest.raises(ValueError):
            add_vertical_constraints(None)
