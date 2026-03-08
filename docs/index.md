# toSketch Documentation

toSketch is a FreeCAD workbench for reverse-engineering existing 3D models. When you import a STEP file into FreeCAD, you get a viewable model but no parametric properties you can modify. toSketch bridges that gap by extracting 2D sketches from 3D geometry, applying constraints, and exporting reusable macro code.

## Getting Started

| Guide | Description |
|-------|-------------|
| [Installation](installation.md) | Install the workbench and its dependencies |
| [Quick Start](quickstart.md) | Your first STEP import to constrained sketch in 5 minutes |

## Tool Reference

| Tool | Description |
|------|-------------|
| [Face to Sketch](tools/face-to-sketch.md) | Convert a planar face to a 2D sketch |
| [Create Plane](tools/create-plane.md) | Create a parametric cutting plane |
| [Section to Sketch](tools/section-to-sketch.md) | Cross-section objects with a plane to produce a sketch |
| [Remove Outer Box](tools/remove-outer-box.md) | Remove bounding box edges from a sketch |
| [Export to Macro](tools/export-to-macro.md) | Export a sketch as a Python macro (.FCMacro) |
| [Line Curve Fit](tools/to-line-curve-fit.md) | Merge collinear lines and fit B-spline curves (Alpha) |
| [Curve Fit](tools/to-curve-fit.md) | Fit B-splines to line endpoints (Alpha) |
| [Constraints](tools/constraints.md) | Auto-detect and add coincident, horizontal, vertical, parallel, and symmetry constraints |
| [Scale](tools/to-scale.md) | Scale objects imported from STEP files |
| [Reset Origin](tools/reset-origin.md) | Fix origin placement for correct rotation of STEP imports |
| [Plane to Part Plane](tools/plane-to-part-plane.md) | Convert a toPlane to a standard Part::Plane |
| [BSpline to Arc](tools/bspline-to-arc.md) | Replace B-splines with circular arcs (Future) |

## Workflows

| Workflow | Description |
|----------|-------------|
| [STEP Reverse Engineering](workflows/step-reverse-engineering.md) | Full workflow: STEP import to parametric model |
| [Mesh Cross-Section](workflows/mesh-cross-section.md) | Extract and fit curves from mesh cross-sections |

## Developer Guide

| Guide | Description |
|-------|-------------|
| [Architecture](developer/architecture.md) | Code structure, objects, and extension points |

## Dependencies

- **FreeCAD** >= 0.19.0
- **geomdl** (NURBS-Python) -- for curve fitting operations
- **scipy** -- for B-spline interpolation

## License

GPL-2.0-or-later. See [LICENSE](../LICENSE).
