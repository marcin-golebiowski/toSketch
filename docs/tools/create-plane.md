# Create Plane (toPlane)

Creates a parametric `toPlane` object that serves as a cutting plane for cross-sectioning 3D objects.

## How to Use

1. Click the **toPlane** icon in the toolbar.
2. A 500x500 plane appears on the XY plane at offset 0.
3. Adjust properties in the **Properties panel** to position the plane.

## Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| Axis | Enum | XY | Plane orientation: XY, XZ, YZ, or Custom |
| Offset | Float | 0.0 | Distance from origin along the plane's normal |
| Length | Float | 500.0 | Plane width |
| Width | Float | 500.0 | Plane height |
| XDir | Float | 0.0 | X component of custom normal (only when Axis = Custom) |
| YDir | Float | 0.0 | Y component of custom normal (only when Axis = Custom) |
| ZDir | Float | 1.0 | Z component of custom normal (only when Axis = Custom) |

## Custom Axis

To create a plane at an arbitrary angle:

1. Set **Axis** to **Custom** in the Properties panel.
2. Set **XDir**, **YDir**, **ZDir** to define the plane's normal direction.
3. Adjust **Offset** to move the plane along that normal.

## Typical Usage

The toPlane is primarily used as input for [Section to Sketch](section-to-sketch.md):

1. Create a toPlane and position it where you want to cut.
2. Select the plane and the target objects.
3. Click toSketch to generate the cross-section.

## See Also

- [Section to Sketch](section-to-sketch.md) -- uses this plane to create cross-sections
- [Plane to Part Plane](plane-to-part-plane.md) -- converts this to a standard Part::Plane

[Back to Index](../index.md)
