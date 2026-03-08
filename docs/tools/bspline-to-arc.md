# BSpline to Arc

> **Status: Future** -- This feature is planned but not yet implemented.

## Planned Functionality

Test each B-spline curve in a sketch and, if the curve fits a circular arc within tolerance, replace it with an `ArcOfCircle`. This would simplify sketches and produce more useful parametric geometry.

## Why This Matters

Cross-sections of cylindrical features often produce B-spline approximations of what should be simple arcs. Replacing these with true arcs makes the sketch easier to constrain and modify.

[Back to Index](../index.md)
