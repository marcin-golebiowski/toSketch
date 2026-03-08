# Remove Outer Box

Removes the bounding rectangle that sometimes appears in sketches created by cross-sectioning.

## When to Use

After using [Section to Sketch](section-to-sketch.md), the resulting sketch may contain an outer rectangular box that represents the cutting plane's boundary. This tool removes those extra edges.

## How to Use

1. Select the sketch containing the outer box in the Model tree.
2. Click the **Remove Outer Box** icon in the toolbar.
3. The bounding rectangle edges are removed from the sketch.

## Notes

- Only removes the outermost rectangular edges. Internal geometry is preserved.
- If the sketch doesn't have an outer box, the command has no effect.

[Back to Index](../index.md)
