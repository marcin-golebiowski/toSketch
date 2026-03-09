# Developer Guide: Architecture

This document describes the code structure of the toSketch workbench for developers who want to understand, modify, or extend it.

## File Layout

```
freecad/toSketch/
├── __init__.py                    Package init
├── init_gui.py                    Workbench registration, toolbar, and menu setup
├── toSCommands.py                 All GUI command implementations (~2050 lines)
├── toSObjects.py                  Custom FeaturePython objects (~380 lines)
├── toSharedFunc.py                Shared utility functions (~295 lines)
├── faceAnalysis.py                Algorithmic face scoring, grouping, and duplicate detection
├── smartSelectDialog.py           AI-assisted face selection dialog with direct sketch creation
├── ollamaClient.py                Ollama REST API client (preferences, prompts, annotations)
├── ollamaConfigDialog.py          Ollama configuration UI (model, temperature, system prompt)
├── addCoincidentConstraints.py    Coincident constraint detection
├── addHorizontalConstraints.py    Horizontal constraint detection
├── addVerticalConstraints.py      Vertical constraint detection
├── addParallelConstraints.py      Parallel constraint detection
├── symmetricConstraints.py        Symmetry constraint detection (~190 lines)
├── interpolate.py                 B-spline fitting with scipy
├── correction.py                  Geometry correction algorithms
├── interFCBSpline.py              FreeCAD B-spline interaction
├── vectors2np2d.py                Vector to NumPy 2D conversion
└── Resources/
    ├── icons/                     17 SVG toolbar icons
    └── translations/              Language files
```

## Workbench Registration (init_gui.py)

The workbench is registered as a `FreeCADGui.Workbench` subclass called `toSketch_Workbench`.

### Command Registration

Commands are registered in `Initialize()` via `FreeCADGui.addCommand()`:

| Command Name | Class | Description |
|-------------|-------|-------------|
| `toSketch` | `toSketchFeature` | Face/section to sketch |
| `section2Sketch` | `section2SketchFeature` | Cross-section to sketch |
| `removeOuterBox` | `removeOuterBoxFeature` | Remove bounding box |
| `addBbox` | `addBboxFeature` | Create bbox sketch |
| `toLineCurveFit` | `toLineCurveFitFeature` | Line + curve fitting |
| `toCurveFit` | `toCurveFitFeature` | B-spline curve fitting |
| `toMacro` | `toMacroFeature` | Export to macro |
| `toPlane2Part` | `toPlane2PartFeature` | toPlane to Part::Plane |
| `toSPlane` | `toSPlaneFeature` | Create parametric plane |
| `bSpline2Arc` | `bSpline2ArcFeature` | B-spline to arc (future) |
| `toScale` | `toScaleFeature` | Scale objects |
| `toResetOrigin` | `toResetOriginFeature` | Fix origin placement |
| `addConstraints` | `ConstraintsGroupFeature` | Constraint command group |
| `SmartSelect` | `SmartSelectFeature` | AI-assisted face selection and sketch creation |
| `OllamaConfig` | `OllamaConfigFeature` | Ollama AI configuration dialog |

### Toolbar Layout

Two toolbars are created:

- **toSketch_Tools**: toSketch, section2Sketch, toSPlane, removeOuterBox, addBbox, toCurveFit, toLineCurveFit, toMacro, addConstraints
- **toSketch_Tools Part Tools**: toScale, toResetOrigin, bSpline2Arc, toPlane2Part

## Command Pattern (toSCommands.py)

Each command follows this structure:

```python
class SomeFeature:
    def Activated(self):
        # Main action -- called when user clicks the button
        pass

    def IsActive(self):
        # Returns True if the command should be enabled
        return FreeCAD.ActiveDocument is not None

    def GetResources(self):
        return {
            'Pixmap': os.path.join(path, 'icons', 'icon.svg'),
            'MenuText': 'Menu Label',
            'ToolTip': 'Tooltip description'
        }
```

### Key Command Internals

**toSketchFeature.Activated()** handles three modes based on selection:
1. **Single face selected** -- converts face to sketch via `Draft.makeSketch()`
2. **Plane + objects selected** -- sections objects with the plane, creates sketch from section edges
3. **Mesh selected** -- converts mesh cross-section to sketch

**toMacroFeature.actionToMacro()** iterates over sketch geometry and writes Python code for each element type. Constraint export is handled by `processConstraints()`.

## Custom Objects (toSObjects.py)

Three `FeaturePython` objects are defined:

### toSPlane

A parametric cutting plane with these properties:

- `Axis` (Enum: XY, XZ, YZ, Custom)
- `Offset` (Float)
- `Length`, `Width` (Float)
- `XDir`, `YDir`, `ZDir` (Float -- for custom axis)

The `onChanged()` method rebuilds the plane shape when properties change. The shape is a `Part.makePlane()` with positioning computed from the axis and offset.

### toScale

Stores a copy of the original shape and applies scaling:

- `ScaleX`, `ScaleY`, `ScaleZ` (Float, default 1.0)
- `BaseShape` (hidden) -- the original unscaled shape

`onChanged()` applies a transformation matrix with the scale factors.

### toResetOrigin

Recalculates placement from the bounding box:

- `Type` (Enum: min x/y/z, Center of Mass, Original)
- Read-only bounding box properties (MinX, MaxX, LengthX, etc.)
- `BaseShape` (hidden) -- the original shape

`onChanged()` recomputes placement based on the selected Type.

## Shared Utilities (toSharedFunc.py)

Key functions:

| Function | Purpose |
|----------|---------|
| `shapes2Sketch(shapes, plane)` | Convert a list of shapes to a Draft sketch on the given plane |
| `reportSketchGeometry(sketch)` | Debug: print all geometry in a sketch |
| `are_contiguous(seg1, seg2)` | Check if two line segments share an endpoint |
| `angle_between_lines(p1, p2, p3)` | Angle at p2 between segments p1-p2 and p2-p3 |
| `check3PointsOneLine(p1, p2, p3)` | Check if three points are collinear |
| `vectors_to_numpy(vectors)` | Convert FreeCAD Vector list to NumPy array |
| `remove_duplicates(points)` | Remove duplicate points within tolerance |
| `fit_bspline_to_geom(points)` | Fit B-spline with error control using geomdl |
| `scripy_fit_bspline(points)` | Fit B-spline using scipy.splprep |

## Constraint Modules

Each constraint module exports a main function that takes a sketch and applies constraints:

| Module | Function | Tolerance |
|--------|----------|-----------|
| `addCoincidentConstraints` | `add_coincident_constraints(sketch)` | ~1e-5 |
| `addHorizontalConstraints` | `add_horizontal_constraints(sketch)` | < 0.5 degrees |
| `addVerticalConstraints` | `add_vertical_constraints(sketch)` | < 0.5 degrees |
| `addParallelConstraints` | `add_parallel_constraints(sketch)` | angle comparison |
| `symmetricConstraints` | `check_symmetry(sketch)` | ~1e-5 |

The symmetry module is more complex -- it tests symmetry about X-axis, Y-axis, and each construction line, showing a preview dialog before applying.

## AI-Assisted Face Selection (Smart Select)

The Smart Select feature uses a multi-stage pipeline:

### Data Flow

```
Shape → faceAnalysis.py → FaceInfo[] → ollamaClient.py → Ollama API
                                              ↓
                          smartSelectDialog.py ← annotated FaceInfo[]
                                              ↓
                                    Draft.makeSketch() → Named Sketches
```

### Key Data Structures

**FaceInfo** (`faceAnalysis.py`) stores per-face data:

| Field | Type | Description |
|-------|------|-------------|
| `algo_score` | float | Algorithmic score 0–100 |
| `ai_sketch_score` | float | AI sketch priority 0–100 (-1 = not scored) |
| `ai_sketch_name` | str | Suggested sketch name from AI (CamelCase) |
| `ai_name` | str | Descriptive face name from AI |
| `ai_group` | str | Functional group from AI |
| `ai_recommended` | bool | True if sketch_score >= 60 |

### Ollama Prompt Schema

The prompt requests per-face JSON annotations:

```json
{
  "face_annotations": [{
    "index": 0,
    "name": "descriptive name",
    "group": "functional group",
    "sketch_score": 85,
    "sketch_name": "TopProfile",
    "reason": "why this score"
  }],
  "part_description": "...",
  "extraction_strategy": "..."
}
```

Score blending: `combined = 0.4 * algo_score + 0.6 * ai_sketch_score`

### Sketch Creation

`SmartSelectDialog._on_create_sketches()` creates sketches directly:

1. Iterates checked faces ordered by score (highest first)
2. Skips non-planar faces with a warning
3. Creates each sketch via `Draft.makeSketch()` with the AI/user-provided name
4. Attaches each sketch to its source face (`FlatFace` map mode)
5. Positions the sketch at the face's plane location

## Curve Fitting Pipeline

The curve fitting uses two approaches:

1. **geomdl** (NURBS-Python): Used in `fit_bspline_to_geom()` for advanced fitting with degree 3, centripetal parameterization, and Hausdorff distance error evaluation.
2. **scipy**: Used in `scripy_fit_bspline()` via `scipy.interpolate.splprep` and `splev` for B-spline interpolation.

The `_lineBuffer` class in `toSCommands.py` manages the line-to-curve conversion:
- Buffers consecutive line segments
- Groups lines by slope similarity (threshold: 0.012 radians)
- Flushes buffered lines as either merged straight lines or fitted curves

## Extension Points

### Adding a New Command

1. Create a new class in `toSCommands.py` following the command pattern above.
2. Register it in `init_gui.py`:
   ```python
   FreeCADGui.addCommand('commandName', toSCommands.YourFeature())
   ```
3. Add it to the toolbar list in `Initialize()`.
4. Create an SVG icon in `Resources/icons/`.

### Adding a New Constraint Type

1. Create a new module (e.g., `addTangentConstraints.py`).
2. Implement a function that iterates over sketch geometry, detects the pattern, and calls `sketch.addConstraint()`.
3. Create a command class in `toSCommands.py` that calls your function.
4. Register the command and add it to the `ConstraintsGroupFeature` command list.

### Adding a New Geometry Type to toMacro

In `toMacroFeature.actionToMacro()`, add a new `elif` branch for the geometry type:
```python
elif geom_type == 'YourGeomType':
    macro_file.write(f'sketch.addGeometry(...)\n')
```

## Dependencies

| Package | Used By | Purpose |
|---------|---------|---------|
| `geomdl` | `toSharedFunc.py` | NURBS curve fitting |
| `scipy` | `interpolate.py`, `toSharedFunc.py` | B-spline interpolation (`splprep`/`splev`) |
| `numpy` | `vectors2np2d.py`, `toSharedFunc.py` | Array operations, distance calculations |

All three are only required for curve fitting features. Core sketch extraction and constraint features work without them.

[Back to Index](../index.md)
