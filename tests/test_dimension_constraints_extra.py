# SPDX-License-Identifier: GPL-2.0-or-later
"""Additional edge-case tests for addDimensionConstraints."""
import pytest
from conftest import MockVector, MockLineSegment, MockArcOfCircle, MockCircle, MockSketch

from freecad.toSketch.addDimensionConstraints import (
    add_dimension_constraints,
    snap_to_round,
)


def _make_line(x1, y1, x2, y2):
    return MockLineSegment(MockVector(x1, y1), MockVector(x2, y2))


class TestSnapHierarchy:

    def test_snap_values_hierarchy(self):
        """0.5 preferred over 0.25 over 0.1."""
        assert snap_to_round(10.02) == 10.0       # snaps to 0.5 (nearest 10.0)
        # 10.13: not within 0.05 of nearest 0.5 or 0.25, but within 0.05 of 10.1
        assert abs(snap_to_round(10.13) - 10.1) < 1e-10

    def test_snap_disabled(self):
        """snap=False → raw values used."""
        line = _make_line(0, 0, 10.02, 0)
        sketch = MockSketch(geometry=[line])
        add_dimension_constraints(sketch, snap=False)
        assert len(sketch.added_constraints) == 1
        # Value should be the raw length, not snapped
        import math
        raw_length = math.hypot(10.02, 0)
        assert abs(sketch.added_constraints[0].Value - raw_length) < 1e-10


class TestNegativeCoordinates:

    def test_negative_coordinates(self):
        """Lines in negative quadrant → correct positive length."""
        line = _make_line(-10, -5, -3, -5)
        sketch = MockSketch(geometry=[line])
        add_dimension_constraints(sketch, snap=False)
        assert abs(sketch.added_constraints[0].Value - 7.0) < 1e-10


class TestSmallGeometry:

    def test_arc_near_zero_radius(self):
        """Very small arc → still gets Radius constraint."""
        arc = MockArcOfCircle(MockVector(0, 0), 0.05, MockVector(0.05, 0), MockVector(0, 0.05))
        sketch = MockSketch(geometry=[arc])
        add_dimension_constraints(sketch, snap=False)
        assert len(sketch.added_constraints) == 1
        assert sketch.added_constraints[0].Type == 'Radius'


class TestMixed:

    def test_mixed_lines_and_circles(self):
        """Both Distance and Radius constraints in single pass."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            MockCircle(MockVector(5, 5), 3.0),
        ])
        add_dimension_constraints(sketch, snap=False)
        types = [c.Type for c in sketch.added_constraints]
        assert 'Distance' in types
        assert 'Radius' in types
