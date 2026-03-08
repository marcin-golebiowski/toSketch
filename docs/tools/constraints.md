# Constraints

Sketches created by toSketch have correct geometry but **no constraints**. The Constraints toolbar group provides eight auto-detection commands that scan a sketch and add appropriate constraints.

All commands are accessed via the **Constraints dropdown button** in the toolbar.

## Recommended Order

Apply constraints in this order for best results:

1. **Coincident** -- fixes topology (connected endpoints)
2. **Horizontal** -- constrains horizontal lines
3. **Vertical** -- constrains vertical lines
4. **Parallel** -- constrains parallel line pairs
5. **Symmetry** -- detects mirror symmetry
6. **Equal** -- constrains equal-length lines and equal-radius arcs
7. **Tangent** -- constrains line-arc and arc-arc tangencies
8. **Dimension** -- adds length and radius dimensions with round-number snapping

---

## Add Coincident

Finds endpoints at the same position and adds `Coincident` constraints.

**How to use**: Select a sketch, click **Add Coincident** from the Constraints dropdown.

**Behavior**:
- Scans all geometry endpoints for matching positions (tolerance: ~1e-5).
- Skips pairs that are already constrained.
- Reports the number of constraints added in the FreeCAD Report view.

---

## Add Horizontal

Detects lines that are nearly horizontal and adds `Horizontal` constraints.

**How to use**: Select a sketch, click **Add Horizontal** from the Constraints dropdown.

**Behavior**:
- Lines within 0.5 degrees of horizontal are constrained.
- Only applies to `Part::GeomLineSegment` geometry.

---

## Add Vertical

Detects lines that are nearly vertical and adds `Vertical` constraints.

**How to use**: Select a sketch, click **Add Vertical** from the Constraints dropdown.

**Behavior**:
- Lines within 0.5 degrees of vertical are constrained.
- Only applies to `Part::GeomLineSegment` geometry.

---

## Add Parallel

Finds pairs of lines with the same direction and adds `Parallel` constraints.

**How to use**: Select a sketch, click **Add Parallel** from the Constraints dropdown.

**Behavior**:
- Compares all pairs of lines by direction vector angle.
- Skips pairs that already have any constraint between them.
- Reports results in the Report view.

---

## Check Symmetry

Detects mirror symmetry about the X-axis, Y-axis, or any construction line in the sketch.

**How to use**: Select a sketch, click **Check Symmetry** from the Constraints dropdown.

**Behavior**:
- Tests each geometry element for a mirror counterpart.
- Supports lines, arcs/circles, and points.
- Shows a preview with colored highlights and a confirmation dialog before applying.
- For X/Y axis symmetry, uses the sketch's built-in reference axes.
- For construction line symmetry, tests against each construction line in the sketch.

## Add Equal

Finds pairs of lines with equal length, or arcs/circles with equal radius, and adds `Equal` constraints.

**How to use**: Select a sketch, click **Add Equal** from the Constraints dropdown.

**Behavior**:
- Compares all line pairs by length and all arc/circle pairs by radius.
- Tolerance: ~1e-3 mm.
- Skips pairs that already have an Equal constraint between them.

---

## Add Tangent

Detects tangent junctions between lines and arcs, or between two arcs, and adds `Tangent` constraints.

**How to use**: Select a sketch, click **Add Tangent** from the Constraints dropdown.

**Behavior**:
- **Line-to-Arc**: Checks if a line endpoint touches an arc and the line direction matches the arc's tangent at that point.
- **Arc-to-Arc**: Checks shared endpoints and compares tangent directions, or checks center-distance tangency (external/internal).
- Distance tolerance: ~1e-3 mm. Angle tolerance: ~1e-3 radians.

---

## Add Dimension

Adds `Distance` constraints to line segments and `Radius` constraints to arcs and circles, with automatic round-number snapping.

**How to use**: Select a sketch, click **Add Dimension** from the Constraints dropdown.

**Behavior**:
- Measures each line's length and each arc/circle's radius.
- **Round-number snapping**: Values are snapped to the nearest 0.5, 0.25, or 0.1 mm if within 0.05 mm tolerance. This compensates for numerical drift in STEP imports where the original design intent was a round dimension.
- Skips geometry that already has a Distance or Radius constraint.

---

## Notes

- All constraint commands work non-destructively -- they only add constraints, never modify geometry.
- If a sketch is over-constrained after applying, use **Sketcher > Undo** or manually remove excess constraints.
- For sketches that you don't want to constrain parametrically, consider the [SketcherFixAllPoints macro](https://github.com/FreeCAD/FreeCAD-macros) from the Addon Manager instead.

[Back to Index](../index.md)
