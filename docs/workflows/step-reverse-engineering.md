# Workflow: STEP Reverse Engineering

This guide walks through the complete process of taking an imported STEP file and recreating it as a parametric FreeCAD model using toSketch.

## Overview

| Step | Tool | Purpose |
|------|------|---------|
| 1 | FreeCAD Import | Load the STEP file |
| 2 | [Reset Origin](../tools/reset-origin.md) | Fix rotation behavior |
| 3 | [Scale](../tools/to-scale.md) | Fix units if needed |
| 4 | [Face to Sketch](../tools/face-to-sketch.md) | Extract planar faces |
| 5 | [Create Plane](../tools/create-plane.md) + [Section to Sketch](../tools/section-to-sketch.md) | Create cross-sections |
| 6 | [Remove Outer Box](../tools/remove-outer-box.md) | Clean up sections |
| 7 | [Line Curve Fit](../tools/to-line-curve-fit.md) | Simplify dense geometry |
| 8 | [Constraints](../tools/constraints.md) | Add parametric constraints |
| 9 | [Export to Macro](../tools/export-to-macro.md) | Save as reusable script |
| 10 | PartDesign | Rebuild the parametric model |

---

## Step 1: Import the STEP File

1. **File > Import**, select your `.step` / `.stp` file.
2. The model appears in the viewport as one or more `Part::Feature` objects.
3. Inspect the geometry -- identify which faces and cross-sections you'll need.

## Step 2: Fix Origin (Optional but Recommended)

STEP imports set all Placements to zero, making rotation behave incorrectly.

1. Select the imported object.
2. Click **Reset Origin**.
3. The object's Placement is recalculated. It looks the same but now rotates correctly.

## Step 3: Fix Scale (If Needed)

If the model is in the wrong units (e.g., inches instead of mm):

1. Select the object.
2. Click **toScale**.
3. Set ScaleX/Y/Z to the conversion factor (e.g., 25.4 for inches to mm).

## Step 4: Extract Planar Faces

For each important face:

1. Click on the planar face in the 3D viewport.
2. Click **toSketch**.
3. A sketch is created from that face's outline.
4. Close the sketch editor.

This works well for flat features: flanges, mounting plates, profiles.

## Step 5: Create Cross-Sections

For internal geometry or profiles at specific locations:

1. Click **toPlane** to create a cutting plane.
2. Set the plane's **Axis** and **Offset** to position it through the area of interest.
3. **Ctrl+click** to select both the plane and the target objects.
4. Click **toSketch**.
5. Accept the mesh parameters (or adjust for accuracy).

Repeat with different plane positions to capture the full geometry.

## Step 6: Clean Up Sketches

1. If a sketch has a bounding rectangle, select it and click **Remove Outer Box**.
2. If a sketch has many tiny line segments (from mesh tessellation), use **toLineCurveFit** to merge collinear lines and fit curves.
3. For precise control of curve fitting, use **toCurveFit** with coincident constraint breaks.

## Step 7: Add Constraints

For each sketch, apply constraints in this order:

1. **Add Coincident** -- connects endpoints that should be joined.
2. **Add Horizontal** -- constrains horizontal lines.
3. **Add Vertical** -- constrains vertical lines.
4. **Add Parallel** -- constrains parallel pairs.
5. **Check Symmetry** -- detects mirror symmetry.

After constraints, open the sketch editor to verify. Add remaining dimensions manually to fully constrain each sketch.

## Step 8: Export Macros (Optional)

For sketches you want to reuse or share:

1. Select the sketch.
2. Click **toMacro**.
3. The macro is saved to your FreeCAD macro directory.

## Step 9: Rebuild in PartDesign

With constrained sketches in hand:

1. Switch to **PartDesign** workbench.
2. Create a new **Body**.
3. Use **Pad**, **Pocket**, **Revolve**, **Loft**, etc. with your extracted sketches.
4. Build up the parametric model feature by feature.

The result is a fully parametric model that you can modify by changing sketch dimensions and constraints.

## Which Tool When?

| Situation | Tool |
|-----------|------|
| Flat face visible in the model | Face to Sketch |
| Need an internal cross-section | Create Plane + Section to Sketch |
| Sketch has a bounding rectangle | Remove Outer Box |
| Too many small line segments | Line Curve Fit |
| Want controlled B-spline fitting | Curve Fit |
| Sketch needs parametric constraints | Constraints (Coincident first) |
| Object rotates wrong | Reset Origin |
| Object is wrong size | Scale |
| Want to save sketch as script | Export to Macro |

[Back to Index](../index.md)
