# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for addCoincidentConstraints module."""
import pytest
from conftest import MockVector, MockLineSegment, MockArcOfCircle, MockCircle, MockSketch, MockConstraint

from freecad.toSketch.addCoincidentConstraints import add_coincident_constraints


# ── Helpers ──────────────────────────────────────────────────────
def _coincident_count(sketch):
    return sum(1 for c in sketch.added_constraints if c.Type == 'Coincident')


def _make_line(x1, y1, x2, y2):
    return MockLineSegment(MockVector(x1, y1), MockVector(x2, y2))


# ── Basic functionality ─────────────────────────────────────────
class TestCoincidentBasic:

    def test_two_lines_sharing_endpoint(self):
        """End of line 0 == Start of line 1 → 1 Coincident."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(10, 0, 10, 10),
        ])
        add_coincident_constraints(sketch)
        assert _coincident_count(sketch) == 1

    def test_lines_not_touching(self):
        """Endpoints far apart → no constraint."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 5, 0),
            _make_line(20, 20, 30, 20),
        ])
        add_coincident_constraints(sketch)
        assert _coincident_count(sketch) == 0

    def test_nearly_coincident_within_tolerance(self):
        """Points within 1e-5 → Coincident added."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(10 + 5e-6, 0, 20, 0),
        ])
        add_coincident_constraints(sketch, tolerance=1e-5)
        assert _coincident_count(sketch) == 1

    def test_nearly_coincident_outside_tolerance(self):
        """Points at 1e-4 apart → no Coincident with default tolerance."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(10.0001, 0, 20, 0),
        ])
        add_coincident_constraints(sketch, tolerance=1e-5)
        assert _coincident_count(sketch) == 0

    def test_custom_tolerance(self):
        """Wider tolerance captures more coincidences."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(10.05, 0, 20, 0),
        ])
        add_coincident_constraints(sketch, tolerance=0.1)
        assert _coincident_count(sketch) == 1


# ── Chain and star patterns ──────────────────────────────────────
class TestCoincidentPatterns:

    def test_three_lines_chain(self):
        """A→B→C chain: 2 coincident constraints."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(10, 0, 20, 5),
            _make_line(20, 5, 30, 0),
        ])
        add_coincident_constraints(sketch)
        assert _coincident_count(sketch) == 2

    def test_star_pattern(self):
        """Three lines sharing one point → 3 pairwise coincident constraints."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 5, 5),
            _make_line(10, 0, 5, 5),
            _make_line(5, 10, 5, 5),
        ])
        add_coincident_constraints(sketch)
        assert _coincident_count(sketch) == 3

    def test_arc_endpoint_to_line(self):
        """Arc endpoint coincident with line endpoint."""
        arc = MockArcOfCircle(
            MockVector(5, 0), 5.0,
            MockVector(10, 0), MockVector(0, 0)
        )
        line = _make_line(10, 0, 20, 0)
        sketch = MockSketch(geometry=[arc, line])
        add_coincident_constraints(sketch)
        assert _coincident_count(sketch) == 1


# ── Duplicate avoidance ──────────────────────────────────────────
class TestCoincidentDuplicates:

    def test_duplicate_avoidance(self):
        """Pre-existing Coincident constraint → not re-added."""
        existing = MockConstraint('Coincident', 0, 2, 1, 1)
        sketch = MockSketch(
            geometry=[
                _make_line(0, 0, 10, 0),
                _make_line(10, 0, 20, 0),
            ],
            constraints=[existing],
        )
        add_coincident_constraints(sketch)
        assert _coincident_count(sketch) == 0

    def test_idempotent(self):
        """Running twice adds no new constraints the second time."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(10, 0, 20, 0),
        ])
        add_coincident_constraints(sketch)
        first_count = _coincident_count(sketch)
        sketch.added_constraints.clear()
        add_coincident_constraints(sketch)
        assert _coincident_count(sketch) == 0
        assert first_count == 1


# ── Edge cases ───────────────────────────────────────────────────
class TestCoincidentEdgeCases:

    def test_empty_sketch(self):
        """No geometry → no crash, no constraints."""
        sketch = MockSketch(geometry=[])
        add_coincident_constraints(sketch)
        assert _coincident_count(sketch) == 0

    def test_single_line(self):
        """One line → no constraint (nothing to pair with)."""
        sketch = MockSketch(geometry=[_make_line(0, 0, 10, 0)])
        add_coincident_constraints(sketch)
        assert _coincident_count(sketch) == 0

    def test_invalid_sketch_type(self):
        """Non-sketch object → ValueError."""
        with pytest.raises(ValueError):
            add_coincident_constraints(None)
        with pytest.raises(ValueError):
            bad = MockSketch()
            bad.TypeId = 'Part::Feature'
            add_coincident_constraints(bad)
