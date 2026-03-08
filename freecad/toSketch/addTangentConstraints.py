# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileNotice: Part of the ToSketch addon.

import FreeCAD
import Sketcher
import Part
import math


def _point_on_arc(point, arc, tolerance):
    """Check if a point lies on an arc/circle within tolerance."""
    dist_to_center = (point - arc.Center).Length
    return abs(dist_to_center - arc.Radius) < tolerance


def _arc_tangent_at_point(arc, point):
    """Return the tangent direction vector of an arc/circle at a given point."""
    radial = point - arc.Center
    # Tangent is perpendicular to radial direction (in 2D, rotate 90 degrees)
    return FreeCAD.Vector(-radial.y, radial.x, 0).normalize()


def _line_direction(line):
    """Return the normalized direction vector of a line segment."""
    return (line.EndPoint - line.StartPoint).normalize()


def _endpoint_pos_and_point(geo):
    """Yield (pos_index, point) for start and end of a geometry element."""
    if hasattr(geo, 'StartPoint'):
        yield 1, geo.StartPoint
    if hasattr(geo, 'EndPoint'):
        yield 2, geo.EndPoint


def add_tangent_constraints(sketch, tolerance=1e-3, angle_tolerance=1e-3):
    """
    Scan a FreeCAD Sketch and add Tangent constraints where:
    - A line endpoint touches an arc/circle and the line is tangent there
    - Two arcs share an endpoint and are tangent at that point

    Parameters
    ----------
    sketch : Sketcher::SketchObject
    tolerance : float
        Distance tolerance for detecting shared endpoints.
    angle_tolerance : float
        Angle tolerance (radians) for tangency direction check.
    """
    if sketch is None or sketch.TypeId != 'Sketcher::SketchObject':
        raise ValueError("Must pass a valid Sketcher::SketchObject")

    geo_list = sketch.Geometry
    constraints = sketch.Constraints

    # Build set of existing Tangent constraint pairs
    existing_tangent = set()
    for c in constraints:
        if c.Type == 'Tangent' and hasattr(c, 'First') and hasattr(c, 'Second'):
            existing_tangent.add((min(c.First, c.Second), max(c.First, c.Second)))

    added = 0

    # Classify geometry
    lines = []
    arcs = []
    for i, g in enumerate(geo_list):
        if isinstance(g, Part.LineSegment):
            lines.append((i, g))
        elif isinstance(g, (Part.ArcOfCircle, Part.Circle)):
            arcs.append((i, g))

    # --- Case A: Line-to-Arc tangency ---
    for line_idx, line in lines:
        line_dir = _line_direction(line)
        for arc_idx, arc in arcs:
            pair = (min(line_idx, arc_idx), max(line_idx, arc_idx))
            if pair in existing_tangent:
                continue

            for line_pos, line_point in _endpoint_pos_and_point(line):
                if not _point_on_arc(line_point, arc, tolerance):
                    continue

                # Check tangency: line direction should be parallel to arc tangent
                arc_tan = _arc_tangent_at_point(arc, line_point)
                angle = abs(line_dir.getAngle(arc_tan))
                if angle < angle_tolerance or abs(angle - math.pi) < angle_tolerance:
                    # Find which arc endpoint matches
                    arc_pos = None
                    if hasattr(arc, 'StartPoint') and \
                       line_point.distanceToPoint(arc.StartPoint) < tolerance:
                        arc_pos = 1
                    elif hasattr(arc, 'EndPoint') and \
                         line_point.distanceToPoint(arc.EndPoint) < tolerance:
                        arc_pos = 2

                    if arc_pos is not None:
                        sketch.addConstraint(
                            Sketcher.Constraint('Tangent',
                                                line_idx, line_pos,
                                                arc_idx, arc_pos))
                    else:
                        # Point on arc but not at an endpoint
                        sketch.addConstraint(
                            Sketcher.Constraint('Tangent', line_idx, arc_idx))

                    existing_tangent.add(pair)
                    added += 1
                    print(f"Added Tangent constraint between line {line_idx} "
                          f"and arc {arc_idx}")
                    break  # Only one tangent per line-arc pair

    # --- Case B: Arc-to-Arc tangency ---
    for a in range(len(arcs)):
        arc_idx_a, arc_a = arcs[a]
        for b in range(a + 1, len(arcs)):
            arc_idx_b, arc_b = arcs[b]
            pair = (min(arc_idx_a, arc_idx_b), max(arc_idx_a, arc_idx_b))
            if pair in existing_tangent:
                continue

            # Check shared endpoints
            for pos_a, pt_a in _endpoint_pos_and_point(arc_a):
                found = False
                for pos_b, pt_b in _endpoint_pos_and_point(arc_b):
                    if pt_a.distanceToPoint(pt_b) > tolerance:
                        continue

                    # Shared endpoint found — check tangency
                    tan_a = _arc_tangent_at_point(arc_a, pt_a)
                    tan_b = _arc_tangent_at_point(arc_b, pt_b)
                    angle = abs(tan_a.getAngle(tan_b))
                    if angle < angle_tolerance or \
                       abs(angle - math.pi) < angle_tolerance:
                        sketch.addConstraint(
                            Sketcher.Constraint('Tangent',
                                                arc_idx_a, pos_a,
                                                arc_idx_b, pos_b))
                        existing_tangent.add(pair)
                        added += 1
                        print(f"Added Tangent constraint between arcs "
                              f"{arc_idx_a} and {arc_idx_b}")
                        found = True
                        break
                if found:
                    break

            # Also check center-distance based tangency (no shared endpoint)
            if pair not in existing_tangent:
                center_dist = (arc_a.Center - arc_b.Center).Length
                r_sum = arc_a.Radius + arc_b.Radius
                r_diff = abs(arc_a.Radius - arc_b.Radius)
                if abs(center_dist - r_sum) < tolerance or \
                   abs(center_dist - r_diff) < tolerance:
                    sketch.addConstraint(
                        Sketcher.Constraint('Tangent', arc_idx_a, arc_idx_b))
                    existing_tangent.add(pair)
                    added += 1
                    print(f"Added Tangent constraint between arcs "
                          f"{arc_idx_a} and {arc_idx_b} (center-distance)")

    if added == 0:
        print("No new Tangent constraints added.")
    else:
        print(f"{added} Tangent constraint(s) added.")

    FreeCAD.ActiveDocument.recompute()
