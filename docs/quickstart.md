# Quick Start: STEP File to Constrained Sketch

This tutorial walks through the most common toSketch workflow: importing a STEP file, extracting a face as a sketch, and adding constraints.

## Step 1: Import a STEP File

1. Open FreeCAD.
2. Go to **File > Import** and select a `.step` or `.stp` file.
3. The 3D model appears in the viewport, but it has no parametric history -- just raw geometry.

## Step 2: Switch to toSketch Workbench

Select **toSketch** from the workbench dropdown in the toolbar.

## Step 3: Extract a Face as a Sketch

1. In the 3D viewport, click on a **flat (planar) face** of the imported model. The face highlights when selected.
2. Click the **toSketch** icon in the toolbar.
3. A new `Sketch` object appears in the Model tree, and the sketch editor opens automatically.
4. You can see the 2D outline of that face -- lines, arcs, circles, etc.
5. Close the sketch editor (click **Close** in the Tasks panel).

## Step 4: Add Constraints

The sketch has correct geometry but no constraints. Let's fix that:

1. Select the sketch you just created in the Model tree.
2. Click the **Constraints** dropdown button in the toolbar.
3. Click **Add Coincident** -- this finds endpoints at the same position and constrains them together.
4. Click the dropdown again and select **Add Horizontal** -- this constrains nearly-horizontal lines.
5. Repeat for **Add Vertical** and **Add Parallel** as needed.

> **Recommended order**: Coincident first (fixes topology), then Horizontal/Vertical, then Parallel, then Symmetry.

## Step 5: Verify

Double-click the sketch to re-open the sketch editor. You should see constraint icons on the geometry. The sketch is now partially constrained and ready for further parametric modeling with PartDesign (Pad, Pocket, Revolve, etc.).

## Next Steps

- [Create cross-sections](tools/section-to-sketch.md) using a cutting plane
- [Export to macro](tools/export-to-macro.md) for reusable Python code
- [Full STEP reverse-engineering workflow](workflows/step-reverse-engineering.md) for the complete process

[Back to Index](index.md)
