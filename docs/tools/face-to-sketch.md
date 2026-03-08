# Face to Sketch

Converts a selected planar face from a 3D solid into a 2D `Sketcher::SketchObject`. The sketch is mapped to the face and positioned using the face's normal vector.

## Prerequisites

- A 3D object with at least one planar face (typically a STEP import or Part solid).

## How to Use

1. In the 3D viewport, select a **single planar face** by clicking on it.
2. Click the **toSketch** icon in the toolbar.
3. A new Sketch object is created and the sketch editor opens.

## What Gets Created

The sketch contains all the edges of the selected face, converted to sketch geometry:

- **Lines** (straight edges)
- **Circles** and **arcs of circles**
- **Ellipses** and **arcs of ellipses**
- **B-spline curves**
- **Points**

## Notes

- Only **planar** faces are supported. Non-planar faces (curved surfaces) cannot be converted.
- The resulting sketch has **geometry but no constraints**. Use the [Constraints](constraints.md) tools to add them.
- The sketch's `MapMode` is set to `FlatFace`, attached to the selected face.
- If you need a cross-section rather than a face outline, use [Section to Sketch](section-to-sketch.md) instead.

## Tips

- To extract multiple faces, repeat the process for each face. Each creates a separate sketch.
- After extracting, consider running [Add Coincident](constraints.md) constraints first to fix the sketch topology.

[Back to Index](../index.md)
