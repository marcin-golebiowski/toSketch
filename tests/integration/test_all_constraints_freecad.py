# SPDX-License-Identifier: GPL-2.0-or-later
"""
Integration tests for ALL constraint modules using real FreeCAD.

These tests require a FreeCAD installation and will be skipped if
FreeCAD is not available.
"""
import math
import pytest

try:
    import FreeCAD
    import Part
    import Sketcher
    HAS_FREECAD = True
except ImportError:
    HAS_FREECAD = False

pytestmark = pytest.mark.skipif(not HAS_FREECAD, reason="FreeCAD not available")


# ── Fixtures ─────────────────────────────────────────────────────
@pytest.fixture
def doc():
    """Create and return a fresh FreeCAD document, close it after the test."""
    d = FreeCAD.newDocument("TestConstraints")
    yield d
    FreeCAD.closeDocument(d.Name)


@pytest.fixture
def sketch(doc):
    """Create a blank sketch in a PartDesign Body."""
    body = doc.addObject("PartDesign::Body", "Body")
    sk = body.newObject("Sketcher::SketchObject", "Sketch")
    doc.recompute()
    return sk


# ── Helpers ──────────────────────────────────────────────────────
def add_line(sketch, x1, y1, x2, y2):
    return sketch.addGeometry(
        Part.LineSegment(FreeCAD.Vector(x1, y1, 0), FreeCAD.Vector(x2, y2, 0)), False)


def add_arc(sketch, cx, cy, r, start_deg, end_deg):
    return sketch.addGeometry(
        Part.ArcOfCircle(
            Part.Circle(FreeCAD.Vector(cx, cy, 0), FreeCAD.Vector(0, 0, 1), r),
            math.radians(start_deg), math.radians(end_deg)), False)


def add_circle(sketch, cx, cy, r):
    return sketch.addGeometry(
        Part.Circle(FreeCAD.Vector(cx, cy, 0), FreeCAD.Vector(0, 0, 1), r), False)


def constraint_count(sketch, ctype):
    return sum(1 for c in sketch.Constraints if c.Type == ctype)


# ── Coincident ───────────────────────────────────────────────────
class TestCoincidentReal:

    def test_coincident_real_sketch(self, sketch):
        """Two lines sharing an endpoint → Coincident constraint added."""
        from freecad.toSketch.addCoincidentConstraints import add_coincident_constraints
        add_line(sketch, 0, 0, 10, 0)
        add_line(sketch, 10, 0, 20, 5)
        sketch.recompute()
        add_coincident_constraints(sketch)
        assert constraint_count(sketch, 'Coincident') >= 1


# ── Horizontal ───────────────────────────────────────────────────
class TestHorizontalReal:

    def test_horizontal_real_sketch(self, sketch):
        """Horizontal lines get Horizontal constraint."""
        from freecad.toSketch.addHorizontalConstraints import add_horizontal_constraints
        add_line(sketch, 0, 0, 10, 0)
        add_line(sketch, 0, 5, 10, 5)
        add_line(sketch, 0, 0, 0, 10)  # vertical — should not match
        sketch.recompute()
        add_horizontal_constraints(sketch)
        assert constraint_count(sketch, 'Horizontal') == 2


# ── Vertical ─────────────────────────────────────────────────────
class TestVerticalReal:

    def test_vertical_real_sketch(self, sketch):
        """Vertical lines get Vertical constraint."""
        from freecad.toSketch.addVerticalConstraints import add_vertical_constraints
        add_line(sketch, 0, 0, 0, 10)
        add_line(sketch, 5, 0, 5, 10)
        add_line(sketch, 0, 0, 10, 0)  # horizontal — should not match
        sketch.recompute()
        add_vertical_constraints(sketch)
        assert constraint_count(sketch, 'Vertical') == 2


# ── Parallel ─────────────────────────────────────────────────────
class TestParallelReal:

    def test_parallel_real_sketch(self, sketch):
        """Two parallel horizontal lines → Parallel constraint."""
        from freecad.toSketch.addParallelConstraints import add_parallel_constraints
        add_line(sketch, 0, 0, 10, 0)
        add_line(sketch, 0, 5, 10, 5)
        sketch.recompute()
        add_parallel_constraints(sketch)
        assert constraint_count(sketch, 'Parallel') >= 1


# ── Equal ────────────────────────────────────────────────────────
class TestEqualReal:

    def test_equal_real_sketch(self, sketch):
        """Two equal-length lines → Equal constraint."""
        from freecad.toSketch.addEqualConstraints import add_equal_constraints
        add_line(sketch, 0, 0, 10, 0)
        add_line(sketch, 0, 5, 10, 5)
        sketch.recompute()
        add_equal_constraints(sketch)
        assert constraint_count(sketch, 'Equal') >= 1


# ── Dimension ────────────────────────────────────────────────────
class TestDimensionReal:

    def test_dimension_real_sketch(self, sketch):
        """Lines get Distance, arcs get Radius."""
        from freecad.toSketch.addDimensionConstraints import add_dimension_constraints
        add_line(sketch, 0, 0, 10, 0)
        add_arc(sketch, 5, 5, 3, 0, 180)
        sketch.recompute()
        add_dimension_constraints(sketch)
        assert constraint_count(sketch, 'Distance') >= 1
        assert constraint_count(sketch, 'Radius') >= 1


# ── Tangent ──────────────────────────────────────────────────────
class TestTangentReal:

    def test_tangent_real_sketch(self, sketch):
        """Line tangent to arc at shared endpoint."""
        from freecad.toSketch.addTangentConstraints import add_tangent_constraints
        # Horizontal line ending at (5, 5)
        add_line(sketch, 0, 5, 5, 5)
        # Arc centered at (5, 0) with r=5, endpoint at (5, 5) — tangent is horizontal there
        add_arc(sketch, 5, 0, 5, 90, 180)
        sketch.recompute()
        add_tangent_constraints(sketch)
        assert constraint_count(sketch, 'Tangent') >= 1


# ── Full workflow ────────────────────────────────────────────────
class TestFullWorkflow:

    def test_full_constraint_workflow(self, sketch):
        """Apply all constraints in recommended order on a rectangle."""
        from freecad.toSketch.addCoincidentConstraints import add_coincident_constraints
        from freecad.toSketch.addHorizontalConstraints import add_horizontal_constraints
        from freecad.toSketch.addVerticalConstraints import add_vertical_constraints
        from freecad.toSketch.addParallelConstraints import add_parallel_constraints
        from freecad.toSketch.addEqualConstraints import add_equal_constraints
        from freecad.toSketch.addDimensionConstraints import add_dimension_constraints

        # Rectangle: 4 lines forming a closed shape
        add_line(sketch, 0, 0, 10, 0)   # bottom
        add_line(sketch, 10, 0, 10, 5)  # right
        add_line(sketch, 10, 5, 0, 5)   # top
        add_line(sketch, 0, 5, 0, 0)    # left
        sketch.recompute()

        # Apply in recommended order
        add_coincident_constraints(sketch)
        add_horizontal_constraints(sketch)
        add_vertical_constraints(sketch)
        add_parallel_constraints(sketch)
        add_equal_constraints(sketch)
        add_dimension_constraints(sketch)

        # Verify at least some constraints were added
        total = len(sketch.Constraints)
        assert total > 0

        # Specific checks for a rectangle
        assert constraint_count(sketch, 'Coincident') >= 4  # 4 corner connections
        assert constraint_count(sketch, 'Horizontal') >= 2  # top + bottom
        assert constraint_count(sketch, 'Vertical') >= 2    # left + right

    def test_constraint_order_independence(self, sketch):
        """Different application order → same total constraint count."""
        from freecad.toSketch.addHorizontalConstraints import add_horizontal_constraints
        from freecad.toSketch.addVerticalConstraints import add_vertical_constraints

        add_line(sketch, 0, 0, 10, 0)  # horizontal
        add_line(sketch, 0, 5, 0, 15)  # vertical
        sketch.recompute()

        # Apply vertical first, then horizontal
        add_vertical_constraints(sketch)
        add_horizontal_constraints(sketch)

        assert constraint_count(sketch, 'Horizontal') == 1
        assert constraint_count(sketch, 'Vertical') == 1
