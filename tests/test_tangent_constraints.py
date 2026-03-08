# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for addTangentConstraints module."""
import sys
import os
import math
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'freecad', 'toSketch'))

from conftest import MockVector as V, MockLineSegment, MockArcOfCircle, MockCircle, MockSketch, MockConstraint
from addTangentConstraints import (
    add_tangent_constraints,
    _point_on_arc,
    _arc_tangent_at_point,
    _line_direction,
    _endpoint_pos_and_point,
)


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────
def make_line(x1, y1, x2, y2):
    return MockLineSegment(V(x1, y1), V(x2, y2))


def make_arc(cx, cy, r, sx, sy, ex, ey):
    return MockArcOfCircle(V(cx, cy), r, V(sx, sy), V(ex, ey))


def make_circle(cx, cy, r):
    return MockCircle(V(cx, cy), r)


# ──────────────────────────────────────────────────────────────────
# Unit tests for helper functions
# ──────────────────────────────────────────────────────────────────
class TestPointOnArc:
    def test_point_exactly_on_arc(self):
        arc = make_arc(0, 0, 5, -5, 0, 0, 5)
        assert _point_on_arc(V(5, 0), arc, 1e-3) is True

    def test_point_off_arc(self):
        arc = make_arc(0, 0, 5, -5, 0, 0, 5)
        assert _point_on_arc(V(3, 0), arc, 1e-3) is False

    def test_point_nearly_on_arc_within_tol(self):
        arc = make_arc(0, 0, 5, -5, 0, 0, 5)
        assert _point_on_arc(V(5.0005, 0), arc, 1e-3) is True

    def test_point_nearly_on_arc_outside_tol(self):
        arc = make_arc(0, 0, 5, -5, 0, 0, 5)
        assert _point_on_arc(V(5.01, 0), arc, 1e-3) is False


class TestArcTangentAtPoint:
    def test_tangent_at_top_of_circle(self):
        """At (0,5) on a circle centered at origin, tangent should be horizontal."""
        arc = make_arc(0, 0, 5, -5, 0, 0, 5)
        tan = _arc_tangent_at_point(arc, V(0, 5))
        # tangent = perpendicular to radial (0,5) -> (-5,0) normalized = (-1,0)
        assert abs(tan.x - (-1.0)) < 1e-6
        assert abs(tan.y) < 1e-6

    def test_tangent_at_right_of_circle(self):
        """At (5,0) on a circle centered at origin, tangent should be vertical."""
        arc = make_arc(0, 0, 5, -5, 0, 0, 5)
        tan = _arc_tangent_at_point(arc, V(5, 0))
        # radial (5,0) -> tangent = (0,5) normalized = (0,1)
        assert abs(tan.x) < 1e-6
        assert abs(tan.y - 1.0) < 1e-6

    def test_tangent_at_45_degrees(self):
        """At 45 deg on unit circle, tangent direction is (-sin45, cos45)."""
        r = 5
        px = r * math.cos(math.pi / 4)
        py = r * math.sin(math.pi / 4)
        arc = make_arc(0, 0, r, -r, 0, 0, r)
        tan = _arc_tangent_at_point(arc, V(px, py))
        expected = V(-py, px).normalize()
        assert abs(tan.x - expected.x) < 1e-6
        assert abs(tan.y - expected.y) < 1e-6


class TestLineDirection:
    def test_horizontal_line(self):
        line = make_line(0, 0, 10, 0)
        d = _line_direction(line)
        assert abs(d.x - 1.0) < 1e-6
        assert abs(d.y) < 1e-6

    def test_vertical_line(self):
        line = make_line(0, 0, 0, 10)
        d = _line_direction(line)
        assert abs(d.x) < 1e-6
        assert abs(d.y - 1.0) < 1e-6

    def test_diagonal_line(self):
        line = make_line(0, 0, 1, 1)
        d = _line_direction(line)
        expected = 1 / math.sqrt(2)
        assert abs(d.x - expected) < 1e-6
        assert abs(d.y - expected) < 1e-6


class TestEndpointPosAndPoint:
    def test_line_yields_both_endpoints(self):
        line = make_line(1, 2, 3, 4)
        pts = list(_endpoint_pos_and_point(line))
        assert len(pts) == 2
        assert pts[0][0] == 1  # StartPoint pos
        assert pts[1][0] == 2  # EndPoint pos

    def test_arc_yields_both_endpoints(self):
        arc = make_arc(0, 0, 5, -5, 0, 0, 5)
        pts = list(_endpoint_pos_and_point(arc))
        assert len(pts) == 2

    def test_circle_yields_nothing(self):
        """Full circle has no StartPoint/EndPoint."""
        circle = make_circle(0, 0, 5)
        pts = list(_endpoint_pos_and_point(circle))
        assert len(pts) == 0


# ──────────────────────────────────────────────────────────────────
# Validation tests
# ──────────────────────────────────────────────────────────────────
class TestValidation:
    def test_none_sketch_raises(self):
        with pytest.raises(ValueError, match="valid Sketcher"):
            add_tangent_constraints(None)

    def test_wrong_type_raises(self):
        sketch = MockSketch()
        sketch.TypeId = 'Part::Feature'
        with pytest.raises(ValueError, match="valid Sketcher"):
            add_tangent_constraints(sketch)


# ──────────────────────────────────────────────────────────────────
# Line-to-Arc tangency tests
# ──────────────────────────────────────────────────────────────────
class TestLineToArcTangency:
    def test_horizontal_line_tangent_to_arc_at_top(self):
        """Horizontal line ending at top of arc (tangent there)."""
        # Arc centered at (0,0), radius 5, point (0,5) is the top
        # A horizontal line ending at (0,5) is tangent to the arc there
        arc = make_arc(0, 0, 5, 5, 0, 0, 5)
        line = make_line(-10, 5, 0, 5)  # horizontal, endpoint at (0,5)
        geo = [line, arc]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 1
        c = sketch.added_constraints[0]
        assert c.Type == 'Tangent'

    def test_vertical_line_tangent_to_arc_at_right(self):
        """Vertical line ending at right side of arc (tangent there)."""
        arc = make_arc(0, 0, 5, 0, 5, 5, 0)
        line = make_line(5, -10, 5, 0)  # vertical, endpoint at (5,0)
        geo = [line, arc]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 1
        assert sketch.added_constraints[0].Type == 'Tangent'

    def test_line_not_tangent_perpendicular(self):
        """Line perpendicular to arc at contact point -> NOT tangent."""
        # Arc centered at (0,0), radius 5. Point (5,0) is on the arc.
        # A horizontal line at (5,0) would be tangent, but a vertical line is not.
        # Actually: radial at (5,0) is horizontal, tangent at (5,0) is vertical.
        # So a horizontal line at (5,0) is radial = perpendicular, not tangent.
        arc = make_arc(0, 0, 5, 0, 5, 5, 0)
        line = make_line(0, 0, 5, 0)  # radial direction, NOT tangent
        geo = [line, arc]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_line_endpoint_not_on_arc(self):
        """Line endpoint far from arc -> no tangent constraint."""
        arc = make_arc(0, 0, 5, -5, 0, 0, 5)
        line = make_line(20, 20, 30, 20)
        geo = [line, arc]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_line_tangent_at_arc_start_point(self):
        """Line tangent at arc's StartPoint -> constraint uses pos indices."""
        # Arc: center (0,0), r=5, start at (5,0), end at (0,5)
        # Tangent at (5,0) is vertical direction (0,1)
        arc = make_arc(0, 0, 5, 5, 0, 0, 5)
        line = make_line(5, -5, 5, 0)  # vertical line ending at arc.StartPoint
        geo = [line, arc]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 1
        c = sketch.added_constraints[0]
        assert c.Type == 'Tangent'
        # Line endpoint pos=2 (EndPoint), arc pos=1 (StartPoint)
        assert c.FirstPos == 2
        assert c.SecondPos == 1

    def test_line_tangent_at_arc_end_point(self):
        """Line tangent at arc's EndPoint -> correct pos indices."""
        # Arc: center (0,0), r=5, start (5,0), end (0,5)
        # Tangent at (0,5) is horizontal (-1,0)
        arc = make_arc(0, 0, 5, 5, 0, 0, 5)
        line = make_line(-10, 5, 0, 5)  # horizontal line ending at arc.EndPoint
        geo = [line, arc]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 1
        c = sketch.added_constraints[0]
        assert c.Type == 'Tangent'
        assert c.SecondPos == 2  # arc EndPoint

    def test_two_lines_tangent_to_same_arc(self):
        """Two different lines each tangent to the same arc -> 2 constraints."""
        arc = make_arc(0, 0, 5, 5, 0, 0, 5)
        line1 = make_line(5, -5, 5, 0)   # vertical at (5,0) = arc start
        line2 = make_line(-10, 5, 0, 5)  # horizontal at (0,5) = arc end
        geo = [line1, line2, arc]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 2


# ──────────────────────────────────────────────────────────────────
# Arc-to-Arc tangency tests
# ──────────────────────────────────────────────────────────────────
class TestArcToArcTangency:
    def test_two_arcs_tangent_at_shared_endpoint(self):
        """Two arcs sharing an endpoint with matching tangent directions."""
        # Arc1: center (0,0), r=5, ends at (5,0)
        # Arc2: center (10,0), r=5, starts at (5,0)
        # At (5,0): arc1 tangent is (0,1), arc2 tangent is (0,-1) -> antiparallel = tangent
        arc1 = make_arc(0, 0, 5, 0, 5, 5, 0)
        arc2 = make_arc(10, 0, 5, 5, 0, 10, 5)
        geo = [arc1, arc2]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 1
        c = sketch.added_constraints[0]
        assert c.Type == 'Tangent'

    def test_two_arcs_not_tangent_at_shared_endpoint(self):
        """Two arcs share endpoint but tangent directions differ -> no constraint."""
        # Arc1: center (0,0), r=5, ends at (5,0) -> tangent (0,1)
        # Arc2: center (5,5), r=5, starts at (5,0) -> radial (0,-5), tangent (5,0) normalized (1,0)
        # Angle between (0,1) and (1,0) = 90 deg -> NOT tangent
        arc1 = make_arc(0, 0, 5, 0, 5, 5, 0)
        arc2 = make_arc(5, 5, 5, 5, 0, 10, 5)
        geo = [arc1, arc2]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_external_tangency_by_center_distance(self):
        """Two arcs with center_dist == r1 + r2 (externally tangent, no shared point)."""
        arc1 = make_arc(0, 0, 3, -3, 0, 0, 3)
        arc2 = make_arc(10, 0, 7, 3, 0, 10, 7)
        # center_dist = 10, r1 + r2 = 3 + 7 = 10
        geo = [arc1, arc2]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 1

    def test_internal_tangency_by_center_distance(self):
        """Two arcs with center_dist == |r1 - r2| (internally tangent)."""
        arc1 = make_arc(0, 0, 10, -10, 0, 0, 10)
        arc2 = make_arc(3, 0, 7, -4, 0, 3, 7)
        # center_dist = 3, |r1 - r2| = |10 - 7| = 3
        geo = [arc1, arc2]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 1

    def test_non_tangent_arcs_by_center_distance(self):
        """Two arcs that are neither externally nor internally tangent."""
        arc1 = make_arc(0, 0, 3, -3, 0, 0, 3)
        arc2 = make_arc(20, 0, 5, 15, 0, 20, 5)
        # center_dist = 20, r_sum = 8, r_diff = 2 -> not tangent
        geo = [arc1, arc2]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_two_circles_externally_tangent(self):
        """Two full circles externally tangent (center_dist == r1 + r2)."""
        c1 = make_circle(0, 0, 4)
        c2 = make_circle(9, 0, 5)
        geo = [c1, c2]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 1


# ──────────────────────────────────────────────────────────────────
# Duplicate-avoidance tests
# ──────────────────────────────────────────────────────────────────
class TestDuplicateAvoidance:
    def test_existing_tangent_skipped(self):
        """Pre-existing Tangent constraint -> no duplicate."""
        arc = make_arc(0, 0, 5, 5, 0, 0, 5)
        line = make_line(5, -5, 5, 0)
        existing = [MockConstraint('Tangent', 0, 1, 1, 1)]
        geo = [line, arc]
        sketch = MockSketch(geometry=geo, constraints=existing)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_running_twice_no_duplicates(self):
        """Running twice -> no new constraints on second pass."""
        arc = make_arc(0, 0, 5, 5, 0, 0, 5)
        line = make_line(5, -5, 5, 0)
        geo = [line, arc]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        count_after_first = len(sketch.added_constraints)
        assert count_after_first > 0
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == count_after_first


# ──────────────────────────────────────────────────────────────────
# Edge-case tests
# ──────────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_empty_sketch(self):
        sketch = MockSketch(geometry=[])
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_only_lines_no_arcs(self):
        """Only lines in sketch -> no tangent constraints possible."""
        geo = [make_line(0, 0, 10, 0), make_line(0, 5, 10, 5)]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_only_circles_no_tangency(self):
        """Two circles far apart -> no tangent constraint."""
        geo = [make_circle(0, 0, 2), make_circle(100, 100, 3)]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_single_arc_no_constraint(self):
        """Single arc -> no tangent possible."""
        geo = [make_arc(0, 0, 5, -5, 0, 0, 5)]
        sketch = MockSketch(geometry=geo)
        add_tangent_constraints(sketch)
        assert len(sketch.added_constraints) == 0
