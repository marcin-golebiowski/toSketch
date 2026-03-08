# Line Curve Fit (toLineCurveFit)

> **Status: Alpha** -- This feature is under development.

Takes a sketch and creates a new simplified sketch where collinear lines are merged and sequences of non-collinear lines are replaced with B-spline curves.

## Prerequisites

- A sketch with ordered line segments (as produced by [Face to Sketch](face-to-sketch.md) or [Section to Sketch](section-to-sketch.md)).
- Dependencies: `geomdl`, `scipy` (see [Installation](../installation.md)).

## How to Use

1. Select a sketch in the Model tree.
2. Click the **toLineCurveFit** icon in the toolbar.
3. A new sketch is created with simplified geometry.

## How It Works

The algorithm processes line segments in order:

1. **Collinear lines** (within 0.012 radians of each other) are **merged** into a single line.
2. **Three or more non-collinear lines** in sequence are replaced with a fitted **B-spline curve**.
3. **Fewer than three** non-collinear lines are transferred as-is to the new sketch.

## Important Notes

- The items in the source sketch **must be in order** (consecutive edges). This is the case for sketches created by the toSketch command.
- The original sketch is preserved; a new sketch is created.
- For more control over where curves start and end, use [Curve Fit](to-curve-fit.md) instead.

[Back to Index](../index.md)
