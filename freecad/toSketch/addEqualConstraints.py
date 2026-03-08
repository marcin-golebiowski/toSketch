# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileNotice: Part of the ToSketch addon.

import FreeCAD
import Sketcher
import Part
import math


def add_equal_constraints(sketch, length_tolerance=1e-3):
    """
    Scan a FreeCAD Sketch and add Equal constraints between pairs of
    lines with equal length, or arcs/circles with equal radius.
    Skips pairs that already have an Equal constraint between them.
    """
    if sketch is None or sketch.TypeId != 'Sketcher::SketchObject':
        raise ValueError("Must pass a valid Sketcher::SketchObject")

    geo_list = sketch.Geometry
    constraints = sketch.Constraints

    # Build set of existing Equal constraint pairs
    existing_equal = set()
    for c in constraints:
        if c.Type == 'Equal' and hasattr(c, 'First') and hasattr(c, 'Second'):
            existing_equal.add((min(c.First, c.Second), max(c.First, c.Second)))

    added = 0

    # --- Equal-length lines ---
    lines = []
    for i, g in enumerate(geo_list):
        if isinstance(g, Part.LineSegment):
            length = (g.EndPoint - g.StartPoint).Length
            lines.append((i, length))

    for a in range(len(lines)):
        idx_a, len_a = lines[a]
        for b in range(a + 1, len(lines)):
            idx_b, len_b = lines[b]
            pair = (min(idx_a, idx_b), max(idx_a, idx_b))
            if pair in existing_equal:
                continue
            if abs(len_a - len_b) < length_tolerance:
                sketch.addConstraint(Sketcher.Constraint('Equal', idx_a, idx_b))
                existing_equal.add(pair)
                added += 1
                print(f"Added Equal constraint between lines {idx_a} and {idx_b} "
                      f"(lengths {len_a:.4f}, {len_b:.4f})")

    # --- Equal-radius arcs and circles ---
    arcs = []
    for i, g in enumerate(geo_list):
        if isinstance(g, (Part.ArcOfCircle, Part.Circle)):
            arcs.append((i, g.Radius))

    for a in range(len(arcs)):
        idx_a, rad_a = arcs[a]
        for b in range(a + 1, len(arcs)):
            idx_b, rad_b = arcs[b]
            pair = (min(idx_a, idx_b), max(idx_a, idx_b))
            if pair in existing_equal:
                continue
            if abs(rad_a - rad_b) < length_tolerance:
                sketch.addConstraint(Sketcher.Constraint('Equal', idx_a, idx_b))
                existing_equal.add(pair)
                added += 1
                print(f"Added Equal constraint between arcs/circles {idx_a} and {idx_b} "
                      f"(radii {rad_a:.4f}, {rad_b:.4f})")

    if added == 0:
        print("No new Equal constraints added.")
    else:
        print(f"{added} Equal constraint(s) added.")

    FreeCAD.ActiveDocument.recompute()
