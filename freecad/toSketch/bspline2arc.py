# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileNotice: Part of the ToSketch addon.
"""
Convert B-spline curves in a Sketch to circular arcs where the fit is
close enough.  Standalone module so the logic can be unit-tested without
a running FreeCAD GUI.
"""

import math
import Part
import Sketcher


# ──────────────────────────────────────────────────────────────────
# Circle-fit check
# ──────────────────────────────────────────────────────────────────
def check_bspline_close_to_circle(bspline, tolerance=1e-3):
    """
    Test whether *bspline* is well-approximated by a circular arc.

    Returns (is_arc, details) where *details* is a dict containing
    ``center``, ``radius``, ``deviation`` on success, or ``error``/
    ``max_deviation`` on failure.
    """
    num_samples = 100
    p0, p1 = bspline.ParameterRange
    points = [
        bspline.value(p0 + i * (p1 - p0) / (num_samples - 1))
        for i in range(num_samples)
    ]

    try:
        circle = Part.Circle()
        circle.fitThroughPoints(points)
    except Exception as e:
        return False, {"error": str(e)}

    deviations = [
        abs(circle.Center.distanceToPoint(p) - circle.Radius)
        for p in points
    ]
    max_dev = max(deviations)
    if max_dev <= tolerance:
        return True, {
            "center": circle.Center,
            "radius": circle.Radius,
            "deviation": max_dev,
        }
    return False, {"max_deviation": max_dev}


# ──────────────────────────────────────────────────────────────────
# Arc creation with orientation check
# ──────────────────────────────────────────────────────────────────
def _create_arc_from_bspline(bspline, center, radius):
    """
    Build a ``Part.ArcOfCircle`` that follows the same path as *bspline*.

    The arc orientation is verified by comparing the midpoints of the
    B-spline and the candidate arc.
    """
    import FreeCAD

    start_pt = bspline.value(bspline.ParameterRange[0])
    end_pt = bspline.value(bspline.ParameterRange[1])

    start_angle = math.atan2(start_pt.y - center.y, start_pt.x - center.x)
    end_angle = math.atan2(end_pt.y - center.y, end_pt.x - center.x)

    # Check for closed B-spline (full circle)
    if start_pt.distanceToPoint(end_pt) < 1e-6:
        return Part.Circle(center, FreeCAD.Vector(0, 0, 1), radius)

    circle_geom = Part.Circle(center, FreeCAD.Vector(0, 0, 1), radius)
    arc = Part.ArcOfCircle(circle_geom, start_angle, end_angle)

    # Verify orientation via midpoint
    mid_param = (bspline.ParameterRange[0] + bspline.ParameterRange[1]) / 2.0
    bspline_mid = bspline.value(mid_param)

    arc_mid_angle = (start_angle + end_angle) / 2.0
    arc_mid = FreeCAD.Vector(
        center.x + radius * math.cos(arc_mid_angle),
        center.y + radius * math.sin(arc_mid_angle),
        0,
    )

    if arc_mid.distanceToPoint(bspline_mid) > radius:
        # Wrong direction — swap angles
        arc = Part.ArcOfCircle(circle_geom, end_angle, start_angle)

    return arc


# ──────────────────────────────────────────────────────────────────
# Constraint snapshot / remap
# ──────────────────────────────────────────────────────────────────
def _snapshot_constraints(sketch, geo_index):
    """Return a list of dicts describing every constraint that references
    *geo_index* (via ``First`` or ``Second``)."""
    snaps = []
    for c in sketch.Constraints:
        first = getattr(c, 'First', None)
        second = getattr(c, 'Second', None)
        if first == geo_index or second == geo_index:
            d = {"Type": c.Type, "First": first, "Second": second}
            for attr in ("FirstPos", "SecondPos", "Value"):
                if hasattr(c, attr):
                    d[attr] = getattr(c, attr)
            snaps.append(d)
    return snaps


def _remap_and_add_constraints(sketch, snaps, old_index, new_index):
    """Re-create constraints from *snaps*, replacing *old_index* →
    *new_index* and decrementing any partner index that was above
    *old_index* (because the deletion shifted them down by 1)."""
    for d in snaps:
        first = d["First"]
        second = d["Second"]

        # Remap
        if first == old_index:
            first = new_index
        elif first is not None and first > old_index:
            first = first - 1

        if second == old_index:
            second = new_index
        elif second is not None and second > old_index:
            second = second - 1

        ctype = d["Type"]
        args = [first]

        if "FirstPos" in d and d["FirstPos"] is not None:
            args.append(d["FirstPos"])

        if second is not None:
            args.append(second)
            if "SecondPos" in d and d["SecondPos"] is not None:
                args.append(d["SecondPos"])

        if "Value" in d and d["Value"] is not None and ctype in ("Distance", "Radius", "Angle"):
            args.append(d["Value"])

        try:
            sketch.addConstraint(Sketcher.Constraint(ctype, *args))
        except Exception:
            pass  # skip constraints that cannot be re-created


# ──────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────
MAX_ARC_RADIUS = 1e6
MIN_BSPLINE_LENGTH = 1e-6


def replace_bsplines_with_arcs(sketch, tolerance=1e-3):
    """
    Scan *sketch* for B-spline curves that approximate circular arcs and
    replace them in-place.

    Returns the number of replacements made.
    """
    # 1. Identify replaceable B-splines
    candidates = []  # list of (index, center, radius)
    for i, geo in enumerate(sketch.Geometry):
        if not hasattr(geo, 'TypeId'):
            continue
        if geo.TypeId != 'Part::GeomBSplineCurve':
            continue

        # Skip degenerate / straight-line B-splines
        if hasattr(geo, 'StartPoint') and hasattr(geo, 'EndPoint'):
            if geo.StartPoint.distanceToPoint(geo.EndPoint) < MIN_BSPLINE_LENGTH:
                continue

        is_arc, details = check_bspline_close_to_circle(geo, tolerance)
        if not is_arc:
            continue
        if details["radius"] > MAX_ARC_RADIUS:
            continue  # effectively a straight line

        candidates.append((i, details["center"], details["radius"]))

    if not candidates:
        return 0

    # 2. Process in reverse index order
    replaced = 0
    for idx, center, radius in reversed(candidates):
        geo = sketch.Geometry[idx]

        # Snapshot constraints before deletion
        snaps = _snapshot_constraints(sketch, idx)

        # Build replacement arc (or circle for closed B-spline)
        new_geo = _create_arc_from_bspline(geo, center, radius)

        # Delete old, add new
        sketch.delGeometry(idx)
        new_idx = sketch.addGeometry(new_geo, False)

        # Re-add constraints
        _remap_and_add_constraints(sketch, snaps, idx, new_idx)

        replaced += 1

    sketch.recompute()
    return replaced


# TODO: integrate subdivide_bspline() for partial-arc replacement of
# complex B-splines (deferred to a future PR).
