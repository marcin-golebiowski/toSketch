# Plane to Part Plane

Converts a custom `toPlane` (FeaturePython) to a standard `Part::Plane` object.

## When to Use

Some FreeCAD operations require a standard `Part::Plane` rather than the custom `toPlane` object. This command creates a compatible conversion.

## How to Use

1. Select a `toPlane` object in the Model tree.
2. Click the **toPlane to PartPlane** icon in the toolbar.
3. A new `Part::Plane` is created with the same position and orientation.

## See Also

- [Create Plane](create-plane.md) -- how to create the source toPlane

[Back to Index](../index.md)
