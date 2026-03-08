# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileNotice: Part of the ToSketch addon.

import FreeCAD
import Sketcher
import Part


def snap_to_round(value, snap_values=(0.5, 0.25, 0.1), tolerance=0.05):
    """
    Snap a value to the nearest round increment if within tolerance.

    Tries each snap granularity in order (coarsest first).
    Returns the snapped value, or the original if no snap is close enough.
    """
    for snap in snap_values:
        rounded = round(value / snap) * snap
        if abs(value - rounded) < tolerance:
            return rounded
    return value


def add_dimension_constraints(sketch, snap=True, length_snap_tolerance=0.05,
                               radius_snap_tolerance=0.05):
    """
    Add dimension constraints to a FreeCAD Sketch:
    - Distance (length) constraints on line segments
    - Radius constraints on arcs and circles

    When snap=True, values are rounded to the nearest 0.5/0.25/0.1 mm
    if within the snap tolerance — compensating for STEP import drift.

    Parameters
    ----------
    sketch : Sketcher::SketchObject
    snap : bool
        Enable round-number snapping.
    length_snap_tolerance : float
        Max deviation (mm) for snapping line lengths.
    radius_snap_tolerance : float
        Max deviation (mm) for snapping radii.
    """
    if sketch is None or sketch.TypeId != 'Sketcher::SketchObject':
        raise ValueError("Must pass a valid Sketcher::SketchObject")

    geo_list = sketch.Geometry
    constraints = sketch.Constraints

    # Find geometry indices that already have a Distance or Radius constraint
    has_distance = set()
    has_radius = set()
    for c in constraints:
        if c.Type == 'Distance' and hasattr(c, 'First'):
            has_distance.add(c.First)
        elif c.Type == 'Radius' and hasattr(c, 'First'):
            has_radius.add(c.First)

    added = 0

    # --- Line length (Distance) constraints ---
    for i, geo in enumerate(geo_list):
        if not isinstance(geo, Part.LineSegment):
            continue
        if i in has_distance:
            continue

        length = (geo.EndPoint - geo.StartPoint).Length
        if length == 0:
            continue

        if snap:
            snapped = snap_to_round(length, tolerance=length_snap_tolerance)
        else:
            snapped = length

        sketch.addConstraint(Sketcher.Constraint('Distance', i, snapped))
        added += 1
        if snap and snapped != length:
            print(f"Added Distance constraint to line {i}: "
                  f"{length:.4f} -> {snapped:.4f} (snapped)")
        else:
            print(f"Added Distance constraint to line {i}: {length:.4f}")

    # --- Radius constraints on arcs and circles ---
    for i, geo in enumerate(geo_list):
        if not isinstance(geo, (Part.ArcOfCircle, Part.Circle)):
            continue
        if i in has_radius:
            continue

        radius = geo.Radius

        if snap:
            snapped = snap_to_round(radius, tolerance=radius_snap_tolerance)
        else:
            snapped = radius

        sketch.addConstraint(Sketcher.Constraint('Radius', i, snapped))
        added += 1
        if snap and snapped != radius:
            print(f"Added Radius constraint to geo {i}: "
                  f"{radius:.4f} -> {snapped:.4f} (snapped)")
        else:
            print(f"Added Radius constraint to geo {i}: {radius:.4f}")

    if added == 0:
        print("No new Dimension constraints added.")
    else:
        print(f"{added} Dimension constraint(s) added.")

    FreeCAD.ActiveDocument.recompute()
