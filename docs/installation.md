# Installation

## Requirements

- FreeCAD 0.19.0 or later
- Python packages: `geomdl`, `scipy` (only needed for curve fitting features)

## Method 1: Addon Manager (Recommended)

1. Open FreeCAD.
2. Go to **Tools > Addon Manager**.
3. Search for **toSketch** and click **Install**.
4. Restart FreeCAD.

## Method 2: Manual Installation

1. Find your FreeCAD Mod directory:
   - **Windows**: `%APPDATA%\FreeCAD\Mod\`
   - **Linux**: `~/.FreeCAD/Mod/` or `~/.local/share/FreeCAD/Mod/`
   - **macOS**: `~/Library/Preferences/FreeCAD/Mod/`
2. Open a terminal in that directory and run:
   ```
   git clone https://github.com/KeithSloan/toSketch.git
   ```
3. Restart FreeCAD.

## Installing Python Dependencies

The curve fitting features (`toLineCurveFit`, `toCurveFit`) require `geomdl` and `scipy`. To install them for FreeCAD's bundled Python:

1. Open FreeCAD's Python console (**View > Panels > Python console**).
2. Find a library path:
   ```python
   import os
   print(os.environ)
   ```
   Note one of the library paths listed (e.g., the `site-packages` directory).
3. Install the packages:
   ```
   pip3 install geomdl -t [path]
   pip3 install scipy -t [path]
   ```

> **Note**: `numpy` is already bundled with FreeCAD and does not need separate installation.

## Verification

1. Open FreeCAD.
2. Switch to the **toSketch** workbench using the workbench selector dropdown.
3. You should see the toSketch toolbar with icons for each tool.

[Back to Index](index.md)
