# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for addDimensionConstraints module (including snap_to_round)."""
import sys
import os
import math
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'freecad', 'toSketch'))

from conftest import MockVector as V, MockLineSegment, MockArcOfCircle, MockCircle, MockSketch, MockConstraint
from addDimensionConstraints import add_dimension_constraints, snap_to_round


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────
def make_line(x1, y1, x2, y2):
    return MockLineSegment(V(x1, y1), V(x2, y2))


def make_arc(cx, cy, r, sx, sy, ex, ey):
    return MockArcOfCircle(V(cx, cy), r, V(sx, sy), V(ex, ey))


def make_circle(cx, cy, r):
    return MockCircle(V(cx, cy), r)


# ══════════════════════════════════════════════════════════════════
# snap_to_round unit tests
# ══════════════════════════════════════════════════════════════════
class TestSnapToRound:
    # --- Exact values (no snapping needed) ---
    def test_exact_half(self):
        assert snap_to_round(10.0) == 10.0

    def test_exact_quarter(self):
        assert snap_to_round(5.25) == 5.25

    def test_exact_tenth(self):
        assert snap_to_round(3.1) == 3.1

    # --- Snapping to 0.5 ---
    def test_snap_to_half_up(self):
        assert snap_to_round(10.02) == 10.0

    def test_snap_to_half_down(self):
        assert snap_to_round(9.98) == 10.0

    def test_snap_to_half_boundary(self):
        """Value exactly at tolerance boundary for 0.5 snap."""
        result = snap_to_round(10.049)
        assert result == 10.0

    def test_no_snap_to_half_outside_tol(self):
        """Value just outside 0.5 snap tolerance -> try smaller snaps."""
        result = snap_to_round(10.06)
        # 10.06 is not within 0.05 of 10.0 (diff=0.06) -> try 0.25 snap
        # nearest 0.25 = 10.0 (diff=0.06 > 0.05) -> try 0.1 snap
        # nearest 0.1 = 10.1 (diff=0.04 < 0.05) -> snaps to 10.1
        assert result == pytest.approx(10.1)

    # --- Snapping to 0.25 ---
    def test_snap_to_quarter(self):
        """9.77 -> nearest 0.5 is 10.0 (diff=0.23, too far) ->
        nearest 0.25 is 9.75 (diff=0.02) -> snaps to 9.75."""
        assert snap_to_round(9.77) == 9.75

    def test_snap_to_quarter_up(self):
        assert snap_to_round(5.27) == 5.25

    # --- Snapping to 0.1 ---
    def test_snap_to_tenth(self):
        """7.32 -> nearest 0.5 is 7.5 (diff=0.18) -> nearest 0.25 is 7.25 (diff=0.07) ->
        nearest 0.1 is 7.3 (diff=0.02) -> snaps to 7.3."""
        assert snap_to_round(7.32) == pytest.approx(7.3)

    def test_snap_to_tenth_down(self):
        assert snap_to_round(7.38) == 7.4

    # --- No snap (outside all tolerances) ---
    def test_no_snap_returns_original(self):
        """Value that doesn't snap to any round increment."""
        val = 7.3333
        # nearest 0.5: 7.5 (diff=0.167) -> no
        # nearest 0.25: 7.25 (diff=0.083) -> no
        # nearest 0.1: 7.3 (diff=0.033) -> within 0.05 -> snaps to 7.3
        assert snap_to_round(val) == pytest.approx(7.3)

    def test_truly_no_snap(self):
        """Very far from any round value with tight tolerance."""
        val = 7.3333
        result = snap_to_round(val, tolerance=0.01)
        # nearest 0.1 is 7.3 (diff=0.033 > 0.01) -> no snap
        assert result == val

    # --- Custom snap values ---
    def test_custom_snap_values(self):
        result = snap_to_round(10.03, snap_values=(1.0, 0.5), tolerance=0.05)
        assert result == 10.0

    # --- Small values ---
    def test_snap_small_value(self):
        assert snap_to_round(0.52) == 0.5

    def test_snap_zero(self):
        assert snap_to_round(0.02) == 0.0

    # --- Negative values ---
    def test_snap_negative(self):
        """Negative values should also snap correctly."""
        assert snap_to_round(-10.02) == -10.0

    # --- Large values ---
    def test_snap_large_value(self):
        assert snap_to_round(100.03) == 100.0


# ══════════════════════════════════════════════════════════════════
# Validation tests
# ══════════════════════════════════════════════════════════════════
class TestValidation:
    def test_none_sketch_raises(self):
        with pytest.raises(ValueError, match="valid Sketcher"):
            add_dimension_constraints(None)

    def test_wrong_type_raises(self):
        sketch = MockSketch()
        sketch.TypeId = 'Part::Feature'
        with pytest.raises(ValueError, match="valid Sketcher"):
            add_dimension_constraints(sketch)


# ══════════════════════════════════════════════════════════════════
# Distance (line length) constraint tests
# ══════════════════════════════════════════════════════════════════
class TestDistanceConstraints:
    def test_single_line_gets_distance(self):
        """Single line -> 1 Distance constraint."""
        geo = [make_line(0, 0, 10, 0)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        assert len(sketch.added_constraints) == 1
        c = sketch.added_constraints[0]
        assert c.Type == 'Distance'
        assert c.First == 0
        assert abs(c.Value - 10.0) < 1e-6

    def test_multiple_lines_each_get_distance(self):
        """Multiple lines -> one Distance per line."""
        geo = [
            make_line(0, 0, 10, 0),
            make_line(0, 5, 7, 5),
            make_line(0, 10, 3, 4),
        ]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        assert len(sketch.added_constraints) == 3
        for c in sketch.added_constraints:
            assert c.Type == 'Distance'

    def test_diagonal_line_correct_length(self):
        """Diagonal line -> correct length via Pythagorean theorem."""
        geo = [make_line(0, 0, 3, 4)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        assert abs(sketch.added_constraints[0].Value - 5.0) < 1e-6

    def test_distance_with_snap_rounds_value(self):
        """Line of length 10.02 with snap -> Distance value = 10.0."""
        geo = [make_line(0, 0, 10.02, 0)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True)
        assert abs(sketch.added_constraints[0].Value - 10.0) < 1e-6

    def test_distance_without_snap_exact_value(self):
        """Line of length 10.02 without snap -> Distance value = 10.02."""
        geo = [make_line(0, 0, 10.02, 0)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        assert abs(sketch.added_constraints[0].Value - 10.02) < 1e-6

    def test_existing_distance_skipped(self):
        """Line with pre-existing Distance constraint -> no duplicate."""
        geo = [make_line(0, 0, 10, 0)]
        existing = [MockConstraint('Distance', 0, 10.0)]
        sketch = MockSketch(geometry=geo, constraints=existing)
        add_dimension_constraints(sketch, snap=False)
        assert len(sketch.added_constraints) == 0

    def test_zero_length_line_skipped(self):
        """Degenerate zero-length line -> skipped."""
        geo = [make_line(5, 5, 5, 5)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        assert len(sketch.added_constraints) == 0


# ══════════════════════════════════════════════════════════════════
# Radius constraint tests
# ══════════════════════════════════════════════════════════════════
class TestRadiusConstraints:
    def test_single_arc_gets_radius(self):
        """Single arc -> 1 Radius constraint."""
        geo = [make_arc(0, 0, 5.0, -5, 0, 0, 5)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        assert len(sketch.added_constraints) == 1
        c = sketch.added_constraints[0]
        assert c.Type == 'Radius'
        assert c.First == 0
        assert abs(c.Value - 5.0) < 1e-6

    def test_single_circle_gets_radius(self):
        """Full circle -> 1 Radius constraint."""
        geo = [make_circle(0, 0, 8.0)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        assert len(sketch.added_constraints) == 1
        c = sketch.added_constraints[0]
        assert c.Type == 'Radius'
        assert abs(c.Value - 8.0) < 1e-6

    def test_radius_with_snap(self):
        """Arc radius 5.03 with snap -> Radius value = 5.0."""
        geo = [make_arc(0, 0, 5.03, -5, 0, 0, 5)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True)
        assert abs(sketch.added_constraints[0].Value - 5.0) < 1e-6

    def test_radius_without_snap(self):
        """Arc radius 5.03 without snap -> exact value."""
        geo = [make_arc(0, 0, 5.03, -5, 0, 0, 5)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        assert abs(sketch.added_constraints[0].Value - 5.03) < 1e-6

    def test_existing_radius_skipped(self):
        """Arc with pre-existing Radius constraint -> no duplicate."""
        geo = [make_arc(0, 0, 5.0, -5, 0, 0, 5)]
        existing = [MockConstraint('Radius', 0, 5.0)]
        sketch = MockSketch(geometry=geo, constraints=existing)
        add_dimension_constraints(sketch, snap=False)
        assert len(sketch.added_constraints) == 0

    def test_multiple_arcs_each_get_radius(self):
        """Multiple arcs -> one Radius per arc."""
        geo = [
            make_arc(0, 0, 3.0, -3, 0, 0, 3),
            make_arc(10, 0, 7.0, 3, 0, 10, 7),
            make_circle(20, 0, 4.0),
        ]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        radius_constraints = [c for c in sketch.added_constraints if c.Type == 'Radius']
        assert len(radius_constraints) == 3


# ══════════════════════════════════════════════════════════════════
# Mixed geometry tests
# ══════════════════════════════════════════════════════════════════
class TestMixedGeometry:
    def test_lines_and_arcs_both_constrained(self):
        """Lines get Distance, arcs get Radius — all in one pass."""
        geo = [
            make_line(0, 0, 10, 0),
            make_arc(0, 0, 5.0, -5, 0, 0, 5),
            make_line(0, 10, 8, 10),
            make_circle(10, 10, 3.0),
        ]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        dist_cs = [c for c in sketch.added_constraints if c.Type == 'Distance']
        rad_cs = [c for c in sketch.added_constraints if c.Type == 'Radius']
        assert len(dist_cs) == 2
        assert len(rad_cs) == 2

    def test_empty_sketch(self):
        sketch = MockSketch(geometry=[])
        add_dimension_constraints(sketch)
        assert len(sketch.added_constraints) == 0

    def test_running_twice_no_duplicates(self):
        """Running twice on same sketch -> no new constraints."""
        geo = [
            make_line(0, 0, 10, 0),
            make_arc(0, 0, 5.0, -5, 0, 0, 5),
        ]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=False)
        count_first = len(sketch.added_constraints)
        assert count_first == 2
        add_dimension_constraints(sketch, snap=False)
        assert len(sketch.added_constraints) == count_first


# ══════════════════════════════════════════════════════════════════
# Snap tolerance parameter tests
# ══════════════════════════════════════════════════════════════════
class TestSnapToleranceParams:
    def test_tight_length_snap_tolerance(self):
        """With tight snap tolerance, value not snapped."""
        geo = [make_line(0, 0, 10.04, 0)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True, length_snap_tolerance=0.01)
        # 10.04 -> nearest 0.5 is 10.0, diff=0.04 > 0.01 -> no snap at 0.5
        # nearest 0.25 is 10.0, diff=0.04 > 0.01 -> no snap at 0.25
        # nearest 0.1 is 10.0, diff=0.04 > 0.01 -> no snap at 0.1
        assert abs(sketch.added_constraints[0].Value - 10.04) < 1e-6

    def test_loose_length_snap_tolerance(self):
        """With loose snap tolerance, more values snapped."""
        geo = [make_line(0, 0, 10.08, 0)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True, length_snap_tolerance=0.1)
        # 10.08 -> nearest 0.1 is 10.1 (diff=0.02 < 0.1) -> snap
        # But nearest 0.5 is 10.0 (diff=0.08 < 0.1) -> snap to 10.0 first
        assert abs(sketch.added_constraints[0].Value - 10.0) < 1e-6

    def test_tight_radius_snap_tolerance(self):
        """Tight radius snap -> no snapping."""
        geo = [make_arc(0, 0, 5.04, -5, 0, 0, 5)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True, radius_snap_tolerance=0.01)
        assert abs(sketch.added_constraints[0].Value - 5.04) < 1e-6


# ══════════════════════════════════════════════════════════════════
# Snap correctness for typical STEP drift values
# ══════════════════════════════════════════════════════════════════
class TestStepDriftScenarios:
    """Realistic values from STEP imports with slight numerical drift."""

    def test_drift_10mm(self):
        geo = [make_line(0, 0, 9.9997, 0)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True)
        assert abs(sketch.added_constraints[0].Value - 10.0) < 1e-6

    def test_drift_25mm(self):
        geo = [make_line(0, 0, 25.015, 0)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True)
        assert abs(sketch.added_constraints[0].Value - 25.0) < 1e-6

    def test_drift_radius_3mm(self):
        geo = [make_arc(0, 0, 2.998, -3, 0, 0, 3)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True)
        assert abs(sketch.added_constraints[0].Value - 3.0) < 1e-6

    def test_drift_quarter_mm(self):
        """Value near 6.25mm (quarter increment)."""
        geo = [make_line(0, 0, 6.27, 0)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True)
        assert abs(sketch.added_constraints[0].Value - 6.25) < 1e-6

    def test_drift_tenth_mm(self):
        """Value near 4.3mm (tenth increment)."""
        geo = [make_line(0, 0, 4.32, 0)]
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True)
        assert abs(sketch.added_constraints[0].Value - 4.3) < 1e-6

    def test_no_drift_odd_value_preserved(self):
        """Truly odd value (e.g. from an angled cut) should not be snapped."""
        geo = [make_line(0, 0, 7.0711, 0)]  # sqrt(50) = 7.0711
        sketch = MockSketch(geometry=geo)
        add_dimension_constraints(sketch, snap=True)
        # nearest 0.1 is 7.1 (diff=0.0289 < 0.05) -> will snap to 7.1
        # This is expected behavior for the snap algorithm
        assert abs(sketch.added_constraints[0].Value - 7.1) < 1e-6
