# BSpline to Arc

## Overview

Test each B-spline curve in a sketch and, if the curve fits a circular arc within tolerance, replace it with an `ArcOfCircle`. This simplifies sketches and produces more useful parametric geometry.

## Why This Matters

Cross-sections of cylindrical features often produce B-spline approximations of what should be simple arcs. Replacing these with true arcs makes the sketch easier to constrain and modify.

## Prerequisites

- A **Sketcher::SketchObject** containing one or more B-spline curves (e.g. from Section to Sketch or Face to Sketch).

## Usage

1. Select a sketch in the model tree.
2. Click **BSpline to Arc** in the toSketch toolbar.
3. The tool scans every B-spline in the sketch:
   - Samples 100 points along the curve.
   - Fits a circle through the sample points.
   - If the maximum deviation is within tolerance (default 1 mm), replaces the B-spline with a `Part.ArcOfCircle` (or `Part.Circle` for closed curves).
4. Existing constraints referencing replaced B-splines are automatically remapped to the new arcs.
5. The operation is wrapped in a FreeCAD transaction — use **Ctrl+Z** to undo.

## What Gets Replaced

| B-spline type | Replacement |
|---------------|-------------|
| Open curve fitting a circular arc | `Part.ArcOfCircle` |
| Closed curve fitting a full circle | `Part.Circle` |
| Curve that does not fit (deviation > tolerance) | Left unchanged |
| Very short curve (length < 1e-6) | Skipped |
| Near-straight curve (radius > 1e6) | Skipped |

## Tips

- Run **Add Coincident** constraints before BSpline to Arc so that endpoint connections are already established and can be remapped.
- After conversion, run **Add Tangent** and **Add Equal** constraints to further constrain the new arcs.
- If some B-splines are not replaced, they may be genuinely non-circular curves.

[Back to Index](../index.md)
