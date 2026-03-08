# Reset Origin

Fixes the origin placement of objects imported from STEP files so they can be rotated correctly.

## The Problem

When STEP files are imported into FreeCAD, all Placements are set to zero and shapes are positioned using absolute coordinates. This means rotating an imported object produces unexpected results -- it rotates around the world origin instead of its own center.

## How to Use

1. Select an imported object in the Model tree.
2. Click the **Reset Origin** icon in the toolbar.
3. The object's appearance doesn't change, but its Placement is recalculated.
4. The original object is removed and replaced with a new `toResetOrigin` object.

The object can now be rotated correctly using its Placement properties.

## Origin Type

In the Properties panel, change the **Type** property to select the origin reference:

| Type | Description |
|------|-------------|
| min x/y/z | Origin at the minimum corner of the bounding box |
| Center of Mass | Origin at the center of mass |
| Original | Original placement (as created by STEP import) |

> **Note**: When set to "Original", the object reverts to the STEP import behavior and may not rotate correctly.

## Read-Only Properties

The Properties panel shows bounding box information for reference:

- MinX, MaxX, LengthX
- MinY, MaxY, LengthY
- MinZ, MaxZ, LengthZ

## Mesh Support

This command also works on `Mesh::Feature` objects, recentering them to their center of gravity.

[Back to Index](../index.md)
