# Curve Fit (toCurveFit)

> **Status: Alpha** -- This feature is under development.

Fits B-spline curves to all straight-line endpoints in a sketch. Optionally breaks curves at user-defined points using coincident constraints.

## Prerequisites

- A sketch with line segments.
- Dependencies: `scipy` (see [Installation](../installation.md)).

## Basic Usage

1. Select a sketch in the Model tree.
2. Click the **toCurveFit** icon in the toolbar.
3. A panel opens. Click **OK** to fit a single B-spline through all line endpoints.

## Controlled Curve Breaks

To control where new curves begin and end:

1. **Open** the target sketch in the sketch editor.
2. **Add single points** at positions where you want curves to break.
3. **Add a coincident constraint** between an existing line endpoint and each added point:
   - Select the line endpoint **first**, then click on the single point.
   - This order prevents the line from moving.
4. **Close** the sketch editor.
5. Select the sketch and click **toCurveFit**.
6. In the panel, select **"Break at Coincident Constraints"**.
7. Click **OK**.

The result is multiple B-spline curves, each starting/ending at the points you marked.

## Technical Details

- Uses `Part.BSplineCurve.approximate()` with DegMin=3, DegMax=5.
- Falls back to line segments if fewer than 4 points are available in a segment.
- The original sketch is preserved; a new sketch is created.

## See Also

- [Line Curve Fit](to-line-curve-fit.md) -- automatic collinear detection and curve fitting

[Back to Index](../index.md)
