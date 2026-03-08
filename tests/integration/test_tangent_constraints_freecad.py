# SPDX-License-Identifier: GPL-2.0-or-later
"""
Integration tests for addTangentConstraints using the real FreeCAD module.

Run with FreeCAD's bundled Python (from toSketch/ root):
    "C:\\Program Files\\FreeCAD 1.0\\bin\\python.exe" -m pytest tests/integration/test_tangent_constraints_freecad.py -v
"""
import sys
import os
import math
import pytest

# Allow importing the addon source (two levels up from tests/integration/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'freecad', 'toSketch'))

FreeCAD = pytest.importorskip("FreeCAD")
import Part
import Sketcher

from addTangentConstraints import (
    add_tangent_constraints,
    _point_on_arc,
    _arc_tangent_at_point,
    _line_direction,
    _endpoint_pos_and_point,
)


# ──────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────
@pytest.fixture
def doc():
    """Create a fresh FreeCAD document, yield it, then close."""
    d = FreeCAD.newDocument("TestTangent")
    yield d
    FreeCAD.closeDocument(d.Name)


@pytest.fixture
def sketch(doc):
    """Create a blank Sketch inside a Body."""
    body = doc.addObject("PartDesign::Body", "Body")
    sk = doc.addObject("Sketcher::SketchObject", "Sketch")
    body.addObject(sk)
    doc.recompute()
    return sk


def _tangent_count(sketch):
    """Count Tangent constraints currently in the sketch."""
    return sum(1 for c in sketch.Constraints if c.Type == "Tangent")


# ──────────────────────────────────────────────────────────────────
# Geometry helpers — build real Part geometry
# ──────────────────────────────────────────────────────────────────
def add_line(sketch, x1, y1, x2, y2):
    """Add a line and return its geometry index."""
    return sketch.addGeometry(
        Part.LineSegment(FreeCAD.Vector(x1, y1, 0),
                         FreeCAD.Vector(x2, y2, 0)))


def add_arc(sketch, cx, cy, r, start_angle_deg, end_angle_deg):
    """Add an arc (angles in degrees, CCW) and return its geometry index."""
    sa = math.radians(start_angle_deg)
    ea = math.radians(end_angle_deg)
    return sketch.addGeometry(
        Part.ArcOfCircle(
            Part.Circle(FreeCAD.Vector(cx, cy, 0),
                        FreeCAD.Vector(0, 0, 1), r),
            sa, ea))


def add_circle(sketch, cx, cy, r):
    """Add a full circle and return its geometry index."""
    return sketch.addGeometry(
        Part.Circle(FreeCAD.Vector(cx, cy, 0),
                    FreeCAD.Vector(0, 0, 1), r))


# ──────────────────────────────────────────────────────────────────
# Unit tests for helper functions (real FreeCAD types)
# ──────────────────────────────────────────────────────────────────
class TestPointOnArcReal:
    def test_point_exactly_on_arc(self, sketch, doc):
        idx = add_arc(sketch, 0, 0, 5, 0, 90)
        doc.recompute()
        arc = sketch.Geometry[idx]
        # (5, 0) is on a circle of radius 5 centred at origin
        assert _point_on_arc(FreeCAD.Vector(5, 0, 0), arc, 1e-3) is True

    def test_point_off_arc(self, sketch, doc):
        idx = add_arc(sketch, 0, 0, 5, 0, 90)
        doc.recompute()
        arc = sketch.Geometry[idx]
        assert _point_on_arc(FreeCAD.Vector(3, 0, 0), arc, 1e-3) is False


class TestArcTangentAtPointReal:
    def test_tangent_at_right(self, sketch, doc):
        """At (5,0) on circle centred at origin, tangent is (0,1)."""
        idx = add_arc(sketch, 0, 0, 5, 0, 180)
        doc.recompute()
        arc = sketch.Geometry[idx]
        tan = _arc_tangent_at_point(arc, FreeCAD.Vector(5, 0, 0))
        assert abs(tan.x) < 1e-6
        assert abs(tan.y - 1.0) < 1e-6

    def test_tangent_at_top(self, sketch, doc):
        """At (0,5) on circle centred at origin, tangent is (-1,0)."""
        idx = add_arc(sketch, 0, 0, 5, 0, 180)
        doc.recompute()
        arc = sketch.Geometry[idx]
        tan = _arc_tangent_at_point(arc, FreeCAD.Vector(0, 5, 0))
        assert abs(tan.x - (-1.0)) < 1e-6
        assert abs(tan.y) < 1e-6


class TestLineDirectionReal:
    def test_horizontal(self, sketch, doc):
        idx = add_line(sketch, 0, 0, 10, 0)
        doc.recompute()
        line = sketch.Geometry[idx]
        d = _line_direction(line)
        assert abs(d.x - 1.0) < 1e-6
        assert abs(d.y) < 1e-6

    def test_vertical(self, sketch, doc):
        idx = add_line(sketch, 0, 0, 0, 10)
        doc.recompute()
        line = sketch.Geometry[idx]
        d = _line_direction(line)
        assert abs(d.x) < 1e-6
        assert abs(d.y - 1.0) < 1e-6


class TestEndpointPosAndPointReal:
    def test_line_has_two_endpoints(self, sketch, doc):
        idx = add_line(sketch, 1, 2, 3, 4)
        doc.recompute()
        pts = list(_endpoint_pos_and_point(sketch.Geometry[idx]))
        assert len(pts) == 2
        assert pts[0][0] == 1  # StartPoint
        assert pts[1][0] == 2  # EndPoint

    def test_arc_has_two_endpoints(self, sketch, doc):
        idx = add_arc(sketch, 0, 0, 5, 0, 90)
        doc.recompute()
        pts = list(_endpoint_pos_and_point(sketch.Geometry[idx]))
        assert len(pts) == 2

    def test_circle_has_no_endpoints(self, sketch, doc):
        idx = add_circle(sketch, 0, 0, 5)
        doc.recompute()
        pts = list(_endpoint_pos_and_point(sketch.Geometry[idx]))
        assert len(pts) == 0


# ──────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────
class TestValidationReal:
    def test_none_raises(self):
        with pytest.raises(ValueError, match="valid Sketcher"):
            add_tangent_constraints(None)

    def test_wrong_type_raises(self, doc):
        box = doc.addObject("Part::Box", "Box")
        doc.recompute()
        with pytest.raises(ValueError):
            add_tangent_constraints(box)


# ──────────────────────────────────────────────────────────────────
# Line-to-Arc tangency (real geometry)
# ──────────────────────────────────────────────────────────────────
class TestLineToArcTangencyReal:
    def test_horizontal_line_tangent_to_arc_at_top(self, sketch, doc):
        """Horizontal line ending at (0,5) on arc centred at origin, r=5."""
        # Arc from 0° to 180° -> StartPoint ~ (5,0), EndPoint ~ (-5,0)
        # Point (0,5) is on the arc. Tangent there is (-1,0) = horizontal.
        arc_idx = add_arc(sketch, 0, 0, 5, 0, 180)
        line_idx = add_line(sketch, -10, 5, 0, 5)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 1

    def test_vertical_line_tangent_to_arc_at_right(self, sketch, doc):
        """Vertical line ending at (5,0) = arc StartPoint (0° to 90°)."""
        arc_idx = add_arc(sketch, 0, 0, 5, 0, 90)
        line_idx = add_line(sketch, 5, -10, 5, 0)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 1

    def test_line_perpendicular_no_tangent(self, sketch, doc):
        """Line in radial direction at contact point -> NOT tangent."""
        # Arc from 0°-90°, StartPoint at (5,0). Radial direction is (1,0).
        # A horizontal line from origin to (5,0) is radial, not tangent.
        add_arc(sketch, 0, 0, 5, 0, 90)
        add_line(sketch, 0, 0, 5, 0)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 0

    def test_line_far_from_arc(self, sketch, doc):
        """Line endpoint nowhere near arc -> no constraint."""
        add_arc(sketch, 0, 0, 5, 0, 90)
        add_line(sketch, 50, 50, 60, 50)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 0

    def test_two_lines_tangent_to_same_arc(self, sketch, doc):
        """Two lines each tangent to the same arc -> 2 constraints."""
        # Arc 0°-90°: start (5,0), end (0,5)
        # Vertical line ending at (5,0) -> tangent
        # Horizontal line ending at (0,5) -> tangent
        add_arc(sketch, 0, 0, 5, 0, 90)
        add_line(sketch, 5, -10, 5, 0)   # vertical to start
        add_line(sketch, -10, 5, 0, 5)   # horizontal to end
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 2

    def test_constraint_has_correct_type(self, sketch, doc):
        """Verify the constraint type string is 'Tangent'."""
        add_arc(sketch, 0, 0, 5, 0, 90)
        add_line(sketch, 5, -10, 5, 0)
        doc.recompute()
        add_tangent_constraints(sketch)
        tangents = [c for c in sketch.Constraints if c.Type == "Tangent"]
        assert len(tangents) == 1
        assert tangents[0].Type == "Tangent"


# ──────────────────────────────────────────────────────────────────
# Arc-to-Arc tangency (real geometry)
# ──────────────────────────────────────────────────────────────────
class TestArcToArcTangencyReal:
    def test_two_arcs_tangent_at_shared_endpoint(self, sketch, doc):
        """Two arcs sharing a point with matching tangent directions.

        Arc1: centre (0,0), r=5, from 0° to 90° -> end at (0,5)
        Arc2: centre (0,10), r=5, from 270° to 360° -> start at (0,5)
        At (0,5): arc1 tangent = (-1,0), arc2 tangent = (1,0) -> antiparallel = OK
        """
        add_arc(sketch, 0, 0, 5, 0, 90)
        add_arc(sketch, 0, 10, 5, 270, 360)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 1

    def test_two_arcs_perpendicular_at_shared_point(self, sketch, doc):
        """Two arcs share a point but tangents are perpendicular -> no tangent."""
        # Arc1: centre (0,0), r=5, 0°-90°, end at (0,5), tangent (-1,0)
        # Arc2: centre (5,5), r=5, 90°-180°, start at (0,5), tangent (0,1) at 90° from centre
        # Wait — let's verify: Part.ArcOfCircle centre (5,5), r=5 at 90° -> point (5+5*cos90, 5+5*sin90) = (5,10)
        # At 180° -> (5+5*cos180, 5+5*sin180) = (0,5). So StartPoint = at 90° = (5,10), endpoint = (0,5)
        # Tangent at (0,5) on arc2: radial = (0,5)-(5,5) = (-5,0), tangent = perp = (0,-5) norm (0,-1)
        # Arc1 tangent at (0,5): radial = (0,5)-(0,0) = (0,5), tangent = perp = (-5,0) norm (-1,0)
        # Angle between (-1,0) and (0,-1) = 90°  -> NOT tangent
        add_arc(sketch, 0, 0, 5, 0, 90)
        add_arc(sketch, 5, 5, 5, 90, 180)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 0

    def test_external_tangency_by_center_distance(self, sketch, doc):
        """Two arcs with centre distance == r1 + r2 (externally tangent)."""
        # Arc1 at (0,0) r=3, Arc2 at (8,0) r=5 -> distance=8 == 3+5
        add_arc(sketch, 0, 0, 3, 0, 180)
        add_arc(sketch, 8, 0, 5, 90, 270)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 1

    def test_internal_tangency_by_center_distance(self, sketch, doc):
        """Two arcs with centre distance == |r1 - r2| (internally tangent)."""
        # Arc1 at (0,0) r=10, Arc2 at (3,0) r=7 -> distance=3 == |10-7|
        add_arc(sketch, 0, 0, 10, 0, 180)
        add_arc(sketch, 3, 0, 7, 0, 180)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 1

    def test_two_circles_externally_tangent(self, sketch, doc):
        """Two full circles with centre distance == r1 + r2."""
        add_circle(sketch, 0, 0, 4)
        add_circle(sketch, 9, 0, 5)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 1

    def test_non_tangent_arcs(self, sketch, doc):
        """Two arcs far apart -> no tangent constraint."""
        add_arc(sketch, 0, 0, 3, 0, 180)
        add_arc(sketch, 50, 0, 5, 0, 180)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 0


# ──────────────────────────────────────────────────────────────────
# Duplicate avoidance
# ──────────────────────────────────────────────────────────────────
class TestDuplicateAvoidanceReal:
    def test_running_twice_no_duplicates(self, sketch, doc):
        """Running add_tangent_constraints twice must not add duplicates."""
        add_arc(sketch, 0, 0, 5, 0, 90)
        add_line(sketch, 5, -10, 5, 0)
        doc.recompute()
        add_tangent_constraints(sketch)
        count1 = _tangent_count(sketch)
        assert count1 == 1
        add_tangent_constraints(sketch)
        count2 = _tangent_count(sketch)
        assert count2 == count1

    def test_pre_existing_tangent_not_duplicated(self, sketch, doc):
        """Manually added tangent constraint should prevent a duplicate."""
        arc_idx = add_arc(sketch, 0, 0, 5, 0, 90)
        line_idx = add_line(sketch, 5, -10, 5, 0)
        doc.recompute()
        # Manually add a tangent constraint
        sketch.addConstraint(Sketcher.Constraint("Tangent", line_idx, 2, arc_idx, 1))
        doc.recompute()
        assert _tangent_count(sketch) == 1
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 1


# ──────────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────────
class TestEdgeCasesReal:
    def test_empty_sketch(self, sketch, doc):
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 0

    def test_only_lines(self, sketch, doc):
        add_line(sketch, 0, 0, 10, 0)
        add_line(sketch, 0, 5, 10, 5)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 0

    def test_single_arc(self, sketch, doc):
        add_arc(sketch, 0, 0, 5, 0, 180)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 0

    def test_only_circles_no_tangency(self, sketch, doc):
        add_circle(sketch, 0, 0, 2)
        add_circle(sketch, 100, 100, 3)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 0


# ──────────────────────────────────────────────────────────────────
# Compound scenarios (more realistic)
# ──────────────────────────────────────────────────────────────────
class TestCompoundScenariosReal:
    def test_line_arc_line_chain(self, sketch, doc):
        """Line -> arc -> line chain, both tangent at endpoints.

        Line1 ends at (5,0), arc from 0° to 90° (start (5,0), end (0,5)),
        Line2 starts at (0,5) going left.
        """
        add_line(sketch, 5, -10, 5, 0)   # vertical line ending at (5,0)
        add_arc(sketch, 0, 0, 5, 0, 90)  # arc start (5,0), end (0,5)
        add_line(sketch, 0, 5, -10, 5)   # horizontal line starting at (0,5)
        doc.recompute()
        add_tangent_constraints(sketch)
        assert _tangent_count(sketch) == 2

    def test_three_tangent_arcs_in_chain(self, sketch, doc):
        """Three arcs chained tangentially.

        Arc1: (0,0) r=5, 0-90 -> end at (0,5)
        Arc2: (0,10) r=5, 270-360 -> start (0,5), end (5,10)
        Arc3: (5,15) r=5, 270-360 -> start (5,10), end (10,15)

        Actually let's use a simpler setup:
        Arc1 and Arc2 share tangent point, Arc2 and Arc3 share tangent point.
        """
        # Arc1: centre (0,0), r=5, 0°-90°  -> end (0,5), tangent (-1,0)
        # Arc2: centre (0,10), r=5, 270°-360° -> start (0,5), tangent (1,0) -> antiparallel OK
        #        end (5,10), tangent (0,1)
        # Arc3: centre (5,15), r=5, 180°-270° -> start (0,15) .. hmm
        # Simpler: just use external tangency for arc2-arc3
        add_arc(sketch, 0, 0, 5, 0, 90)
        add_arc(sketch, 0, 10, 5, 270, 360)
        # Arc3 externally tangent to arc2: centre (0,10) r=5, arc3 centre (15,10) r=5
        # distance = 15 != 10, so let's use (10,10) r=5, dist=10=5+5
        add_arc(sketch, 10, 10, 5, 90, 270)
        doc.recompute()
        add_tangent_constraints(sketch)
        # Arc1-Arc2 share endpoint tangent, Arc2-Arc3 externally tangent
        assert _tangent_count(sketch) >= 2

    def test_mixed_geometry_realistic(self, sketch, doc):
        """Mix of lines, arcs, and circles — only valid tangencies constrained."""
        # A circle and two far-away lines: no tangent
        add_circle(sketch, 0, 0, 10)
        add_line(sketch, 50, 50, 60, 50)
        add_line(sketch, 50, 60, 60, 60)
        # Two externally tangent circles
        add_circle(sketch, 0, 30, 3)
        add_circle(sketch, 7, 30, 4)  # dist=7 == 3+4
        doc.recompute()
        add_tangent_constraints(sketch)
        # Only the two tangent circles should be constrained
        assert _tangent_count(sketch) == 1
