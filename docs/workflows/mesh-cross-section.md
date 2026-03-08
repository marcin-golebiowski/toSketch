# Workflow: Mesh Cross-Section to Sketch

This workflow covers extracting 2D curves from mesh objects (OBJ, STL, etc.) rather than solid STEP models.

## Prerequisites

- A mesh object loaded in FreeCAD.
- Dependencies: `geomdl`, `scipy` (see [Installation](../installation.md)).

## Steps

### 1. Load or Create a Mesh

Import a mesh file via **File > Import** (supports `.obj`, `.stl`, `.ply`, etc.).

### 2. Create a Cross-Section

1. Switch to the **Mesh Design** workbench.
2. Go to **Meshes > Cutting > Cross-Sections**.
3. Position the cutting plane and create the cross-section.
4. A `Mesh Cross-Section` object appears in the Model tree.

### 3. Convert to Raw Sketch

1. Switch to the **toSketch** workbench.
2. Select the Cross-Section object in the Model tree.
3. Click the **toSketch** icon.
4. A raw sketch is created from the cross-section points.

The raw sketch typically contains many small line segments approximating curves.

### 4. Fit Curves

1. Select the raw sketch.
2. Click the **toCurveFit** icon.
3. A new sketch is created with B-spline curves fitted to the line endpoints.

For more control over the curve fitting:

1. Open the raw sketch and add single points where curves should break.
2. Add coincident constraints at those break points.
3. Click **toCurveFit** and select **"Break at Coincident Constraints"**.

See [Curve Fit](../tools/to-curve-fit.md) for detailed instructions.

### 5. Add Constraints

Apply [Constraints](../tools/constraints.md) to the resulting sketch for parametric editing.

## Notes

- Mesh cross-sections produce lower-quality geometry than STEP sections since meshes are approximations.
- Lower mesh resolution = fewer line segments but less accuracy.
- The curve fitting step is important to reduce the number of geometry elements and produce smoother results.

[Back to Index](../index.md)
