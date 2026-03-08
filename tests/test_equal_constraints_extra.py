# SPDX-License-Identifier: GPL-2.0-or-later
"""Additional edge-case tests for addEqualConstraints."""
import pytest
from conftest import MockVector, MockLineSegment, MockArcOfCircle, MockCircle, MockSketch

from freecad.toSketch.addEqualConstraints import add_equal_constraints


def _make_line(x1, y1, x2, y2):
    return MockLineSegment(MockVector(x1, y1), MockVector(x2, y2))


class TestEqualExtra:

    def test_four_equal_lines(self):
        """4 equal lines → 6 pairwise constraints (n*(n-1)/2)."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(0, 5, 10, 5),
            _make_line(0, 10, 10, 10),
            _make_line(0, 15, 10, 15),
        ])
        add_equal_constraints(sketch)
        equal_count = sum(1 for c in sketch.added_constraints if c.Type == 'Equal')
        assert equal_count == 6

    def test_tolerance_boundary(self):
        """Values at exact tolerance boundary."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),           # length 10.0
            _make_line(0, 5, 10.001, 5),        # length ~10.001 (within 1e-3)
        ])
        add_equal_constraints(sketch, length_tolerance=1e-3)
        equal_count = sum(1 for c in sketch.added_constraints if c.Type == 'Equal')
        assert equal_count == 1

    def test_zero_length_lines(self):
        """Two zero-length (degenerate) lines → Equal (both length 0)."""
        sketch = MockSketch(geometry=[
            _make_line(5, 5, 5, 5),
            _make_line(10, 10, 10, 10),
        ])
        add_equal_constraints(sketch)
        equal_count = sum(1 for c in sketch.added_constraints if c.Type == 'Equal')
        assert equal_count == 1

    def test_circles_and_arcs_mixed(self):
        """Circle + Arc with same radius → Equal."""
        sketch = MockSketch(geometry=[
            MockCircle(MockVector(0, 0), 5.0),
            MockArcOfCircle(MockVector(10, 0), 5.0, MockVector(15, 0), MockVector(10, 5)),
        ])
        add_equal_constraints(sketch)
        equal_count = sum(1 for c in sketch.added_constraints if c.Type == 'Equal')
        assert equal_count == 1
