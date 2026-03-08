# Section to Sketch

Intersects one or more 3D objects with a plane, producing a 2D sketch of the cross-section.

## Prerequisites

- A cutting plane: `toPlane`, `Part::Plane`, or `PartDesign::Plane`.
- One or more 3D objects to section.

## How to Use

1. Create or select a plane (see [Create Plane](create-plane.md)).
2. In the Model tree, **Ctrl+click** to multi-select:
   - The plane
   - One or more 3D objects to cut
3. Click the **toSketch** icon.
4. A dialog appears with mesh parameters:
   - **Linear Deflection** (default: 0.1) -- controls mesh density for curved surfaces
   - **Angular Deflection** (default: 0.523599 radians / 30 degrees)
5. Click **OK**.
6. A new sketch is created containing the cross-section edges.

## Behavior

- If **no target objects** are selected alongside the plane, the plugin sections **all visible objects** in the document (excluding the plane itself).
- Sectioned objects are automatically **hidden** after the operation.
- The cross-section may include a bounding rectangle -- use [Remove Outer Box](remove-outer-box.md) to clean it up.

## Mesh Parameters

The Linear and Angular Deflection parameters control how accurately curved surfaces are tessellated before sectioning:

- **Lower values** = more accurate but slower, more line segments in the resulting sketch.
- **Higher values** = faster but rougher approximation.
- For mechanical parts with tight tolerances, use the defaults or lower.

## Tips

- Position the toPlane so it cuts through interesting features of the model.
- After creating the cross-section sketch, use [Constraints](constraints.md) to add parametric constraints.
- For sketches with many small line segments, use [Line Curve Fit](to-line-curve-fit.md) to simplify.

[Back to Index](../index.md)
