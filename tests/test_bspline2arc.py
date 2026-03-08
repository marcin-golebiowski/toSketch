# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for bspline2arc module."""
import math
import pytest
from conftest import (MockVector, MockLineSegment, MockArcOfCircle, MockCircle,
                      MockBSplineCurve, MockSketch, MockConstraint)

from freecad.toSketch.bspline2arc import (
    check_bspline_close_to_circle,
    _create_arc_from_bspline,
    _snapshot_constraints,
    _remap_and_add_constraints,
    replace_bsplines_with_arcs,
)

V = MockVector


# ── Helpers ──────────────────────────────────────────────────────
def _arc_points(cx, cy, r, start_deg, end_deg, n=20):
    """Generate points along a circular arc."""
    points = []
    for i in range(n):
        t = start_deg + i * (end_deg - start_deg) / (n - 1)
        rad = math.radians(t)
        points.append(V(cx + r * math.cos(rad), cy + r * math.sin(rad)))
    return points


def _make_arc_bspline(cx, cy, r, start_deg, end_deg, n=20):
    """Create a MockBSplineCurve that traces a circular arc."""
    pts = _arc_points(cx, cy, r, start_deg, end_deg, n)
    return MockBSplineCurve(pts)


def _make_line(x1, y1, x2, y2):
    return MockLineSegment(V(x1, y1), V(x2, y2))


# ── check_bspline_close_to_circle ────────────────────────────────
class TestCheckBspline:
    """Tests require Part.Circle().fitThroughPoints() which isn't available
    in the mock environment.  These tests verify the function handles errors
    gracefully when the mock Part.Circle lacks fitThroughPoints."""

    def test_check_returns_false_without_fit(self):
        """Mock Circle has no fitThroughPoints → returns False with error."""
        bspline = _make_arc_bspline(0, 0, 5, 0, 90)
        is_arc, details = check_bspline_close_to_circle(bspline)
        # Since MockCircle doesn't have fitThroughPoints, this should
        # return False with an error
        assert is_arc is False
        assert "error" in details


# ── _create_arc_from_bspline ─────────────────────────────────────
class TestCreateArc:

    def test_first_quadrant_arc(self):
        """Arc in Q1: start at (r,0), end at (0,r)."""
        bspline = _make_arc_bspline(0, 0, 5, 0, 90)
        arc = _create_arc_from_bspline(bspline, V(0, 0), 5.0)
        assert isinstance(arc, MockArcOfCircle)

    def test_crossing_pi_boundary(self):
        """Arc crossing the +/-pi boundary."""
        bspline = _make_arc_bspline(0, 0, 5, 170, 190)
        arc = _create_arc_from_bspline(bspline, V(0, 0), 5.0)
        assert isinstance(arc, MockArcOfCircle)

    def test_nearly_full_circle(self):
        """Arc spanning nearly 360° — still an arc, not a circle."""
        bspline = _make_arc_bspline(0, 0, 5, 1, 359)
        arc = _create_arc_from_bspline(bspline, V(0, 0), 5.0)
        assert isinstance(arc, MockArcOfCircle)

    def test_closed_bspline_becomes_circle(self):
        """Closed B-spline (start ≈ end) → Part.Circle."""
        pts = _arc_points(0, 0, 5, 0, 360, n=30)
        # Make start and end coincide
        pts[-1] = V(pts[0].x, pts[0].y)
        bspline = MockBSplineCurve(pts)
        result = _create_arc_from_bspline(bspline, V(0, 0), 5.0)
        assert isinstance(result, MockCircle)


# ── _snapshot_constraints ────────────────────────────────────────
class TestSnapshotConstraints:

    def test_captures_referencing_constraints(self):
        """Constraints touching geo_index are captured."""
        sketch = MockSketch(
            geometry=[_make_line(0, 0, 10, 0), _make_line(10, 0, 20, 0)],
            constraints=[
                MockConstraint('Coincident', 0, 2, 1, 1),
                MockConstraint('Horizontal', 0),
            ],
        )
        snaps = _snapshot_constraints(sketch, 0)
        assert len(snaps) == 2
        assert snaps[0]["Type"] == "Coincident"
        assert snaps[1]["Type"] == "Horizontal"

    def test_ignores_unrelated_constraints(self):
        """Constraints not touching geo_index are ignored."""
        sketch = MockSketch(
            geometry=[_make_line(0, 0, 10, 0), _make_line(10, 0, 20, 0),
                       _make_line(20, 0, 30, 0)],
            constraints=[MockConstraint('Equal', 1, 2)],
        )
        snaps = _snapshot_constraints(sketch, 0)
        assert len(snaps) == 0


# ── _remap_and_add_constraints ───────────────────────────────────
class TestRemapConstraints:

    def test_remap_old_to_new_index(self):
        """Old index in constraint gets replaced with new index."""
        sketch = MockSketch(geometry=[_make_line(0, 0, 10, 0)] * 3)
        snaps = [{"Type": "Equal", "First": 1, "Second": 0}]
        _remap_and_add_constraints(sketch, snaps, old_index=1, new_index=5)
        assert len(sketch.added_constraints) == 1
        c = sketch.added_constraints[0]
        assert c.First == 5   # was 1 (old_index), remapped to 5 (new_index)
        assert c.Second == 0  # was 0, unchanged (not > old_index)

    def test_remap_shifts_partner_above_deleted(self):
        """Partner index > old_index gets decremented by 1."""
        sketch = MockSketch(geometry=[_make_line(0, 0, 10, 0)] * 3)
        snaps = [{"Type": "Equal", "First": 0, "Second": 2}]
        _remap_and_add_constraints(sketch, snaps, old_index=1, new_index=5)
        assert len(sketch.added_constraints) == 1
        c = sketch.added_constraints[0]
        assert c.First == 0
        assert c.Second == 1  # was 2, decremented because > old_index=1


# ── replace_bsplines_with_arcs (integration) ─────────────────────
class TestReplaceBsplines:

    def test_no_bsplines(self):
        """Sketch with only lines → returns 0."""
        sketch = MockSketch(geometry=[
            _make_line(0, 0, 10, 0),
            _make_line(10, 0, 20, 0),
        ])
        count = replace_bsplines_with_arcs(sketch)
        assert count == 0
        assert sketch.GeometryCount == 2

    def test_skip_short_bspline(self):
        """Degenerate B-spline (start ≈ end) → skipped."""
        pts = [V(5, 5), V(5, 5)]  # zero-length
        bspline = MockBSplineCurve(pts)
        sketch = MockSketch(geometry=[bspline])
        count = replace_bsplines_with_arcs(sketch)
        assert count == 0

    def test_bspline_without_fit_skipped(self):
        """B-spline that fails circle fit → not replaced."""
        # Random non-arc points
        pts = [V(0, 0), V(3, 7), V(8, 2), V(12, 9), V(15, 1)]
        bspline = MockBSplineCurve(pts)
        sketch = MockSketch(geometry=[bspline])
        count = replace_bsplines_with_arcs(sketch)
        # fitThroughPoints not available in mock → always fails → 0 replacements
        assert count == 0
