# Scale (toScale)

Scales objects imported from STEP files. Creates a new `toScale` object with adjustable ScaleX, ScaleY, and ScaleZ properties.

## When to Use

STEP imports sometimes have incorrect units (e.g., millimeters vs. inches). This tool lets you rescale the object without re-importing.

## How to Use

1. Select the object to scale in the Model tree.
2. Click the **toScale** icon in the toolbar.
3. A new `toScale` object is created, storing a copy of the original shape.
4. The **original object is deleted**.
5. In the Properties panel, adjust **ScaleX**, **ScaleY**, **ScaleZ** (default: 1.0 each).
6. The shape updates to reflect the new scale.

## Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| ScaleX | Float | 1.0 | Scale factor along X axis |
| ScaleY | Float | 1.0 | Scale factor along Y axis |
| ScaleZ | Float | 1.0 | Scale factor along Z axis |

## Notes

- The scaling is applied about the object's bounding box center.
- This is a non-uniform scale -- you can set different values for each axis.
- The original object is **removed** after the toScale object is created.
- For uniform scaling, set all three values to the same number (e.g., 25.4 to convert inches to mm).

[Back to Index](../index.md)
