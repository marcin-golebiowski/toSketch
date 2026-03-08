# Export to Macro (toMacro)

Exports a sketch as a Python macro (`.FCMacro`) file that can recreate the sketch geometry and constraints.

## How to Use

1. Select a `Sketcher::SketchObject` in the Model tree.
2. Click the **toMacro** icon in the toolbar.
3. A macro file named `<SketchLabel>.FCMacro` is written to the FreeCAD macro directory.

The macro directory is determined by `User parameter: BaseApp/Preferences/Macro > MacroPath`.

## Supported Geometry

| Type | Status |
|------|--------|
| Points | Supported |
| Lines | Supported |
| Circles | Supported |
| ArcOfCircle | Supported |
| Ellipse | Supported |
| ArcOfEllipse | Supported |
| BSplineCurve | Supported |

## Exported Constraints

The following constraint types are exported if present in the source sketch:

- Coincident
- Vertical
- Horizontal
- Equal
- Angle

## Running the Macro

When you execute the generated macro:

- If there is an **ActiveObject** that is a sketch (i.e., the sketch editor is open), the geometry is **added to that sketch**.
- Otherwise, a **new sketch is created**.

This makes it possible to merge geometry from multiple sketches by opening a target sketch, then running the macro.

## Use Cases

- **Portability**: Share sketch definitions as Python scripts.
- **Templates**: Generate reusable sketch templates from existing geometry.
- **Automation**: Integrate sketch creation into larger FreeCAD scripting workflows.

[Back to Index](../index.md)
