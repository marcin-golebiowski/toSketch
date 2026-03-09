# Smart Face Selection

## Overview

When importing a STEP file containing many objects and faces, manually browsing to find the right faces for sketch extraction is tedious. Smart Face Selection uses **algorithmic analysis + Ollama AI** to automatically score, name, group, and recommend faces — presenting an interactive dialog where you review and adjust the selection before creating sketches directly.

## Prerequisites

- A **Part object** with a Shape (e.g. an imported STEP file).
- **Ollama** installed locally (optional, for AI features). Download from [ollama.com](https://ollama.com).

## Usage

1. Select a STEP object (solid or compound) in the model tree.
2. Click **Smart Face Selection** in the toSketch toolbar.
3. The dialog opens with:
   - **Algorithmic scores** for every face (available immediately).
   - Click **Analyze with AI** to get AI annotations from Ollama.
4. Review the face table:
   - Sort by score, area, type, or edge count.
   - Hover over a row to highlight that face in the 3D view.
   - Double-click a row to zoom to that face.
   - Use **Select All**, **Deselect All**, or **AI Recommended** buttons.
   - Adjust the **Threshold** spinner to auto-check faces above a score.
5. Optionally edit **Sketch Name** values in the table (double-click the cell).
6. Click **Create Sketches** to create named FreeCAD sketches from the checked planar faces.

## Scoring Algorithm

Faces are scored 0–100 based on:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Area | 30% | Mid-range area preferred (Gaussian around median) |
| Edge count | 25% | More edges = more interesting profile |
| Surface type | 20% | Plane > Cylinder > Cone > Sphere > BSpline |
| Profile likelihood | 15% | Bonus for axis-perpendicular planar faces with many edges |
| Uniqueness | 10% | Duplicate faces penalized |

## AI Features (Ollama)

When Ollama is running, click **Analyze with AI** to send face geometry data to your local LLM. You can optionally provide context in the **Context** field (e.g. "bearing housing", "gear mount plate") to help the AI understand the part.

The AI provides:

- **Sketch scores** (0–100) — per-face priority for sketch extraction, blended with the algorithmic score (40% algo + 60% AI)
- **Sketch names** — suggested CamelCase names like `TopProfile`, `MountingHoles`, `BearingSeat` (shown in the editable Sketch Name column)
- **Face names** — descriptive names like "Top mounting plate", "Main bore"
- **Face groups** — logical groupings like "Mounting features", "Bore features"
- **Part description** — what the part appears to be
- **Extraction strategy** — which faces to prioritize and why

Faces with `sketch_score >= 60` are automatically marked as **AI Recommended**.

### Sketch Name Column

After AI analysis, the **Sketch Name** column is populated with suggested names. These names are used when creating sketches:

- **Double-click** a Sketch Name cell to edit it before creating sketches.
- Faces without a sketch name get a default name like `Sketch_Face5`.
- Only planar faces can be converted to sketches; non-planar faces are skipped with a warning.

### Direct Sketch Creation

Clicking **Create Sketches** creates FreeCAD `Sketcher::SketchObject` objects directly:

- Sketches are created in score order (highest first).
- Each sketch is attached to its source face with `FlatFace` map mode.
- Sketches are named using the AI-suggested name or `Sketch_FaceN` as fallback.
- The faces are also selected in FreeCAD for any follow-up operations.

### Configuration

Click **Ollama Settings...** to configure:

| Setting | Default | Description |
|---------|---------|-------------|
| Ollama Model | llama3.2 | Which model to use (dropdown shows installed models) |
| URL | localhost:11434 | Ollama server address |
| Temperature | 0.3 | Lower = more consistent, higher = more creative |
| System Prompt | (built-in) | Customizable prompt with sketch scoring criteria |
| Enable AI | checked | Toggle AI features on/off |

Settings are saved in FreeCAD preferences and persist across sessions.

### Ollama Not Available

If Ollama is not installed or not running, the dialog still works with algorithmic scoring only. The Sketch Name column shows "(none)" and the status bar indicates Ollama is unavailable. You can still manually type sketch names by double-clicking the cells.

## Table Columns

| Column | Description |
|--------|-------------|
| (checkbox) | Check faces to include in sketch creation |
| # | Face index |
| Score | Combined score (hover for breakdown: algo / AI sketch / combined) |
| Sketch Name | Editable — name for the created sketch (from AI or manual) |
| AI Name | Descriptive face name from AI |
| Group | Face grouping (AI or normal-based) |
| Type | Surface type with icon |
| Area | Face area in mm² |
| Edges | Number of edges |
| Normal | Face normal direction vector |

## Tips

- Start with the default threshold of 60 — this typically selects the most interesting faces.
- Use **AI Recommended** after Ollama analysis to see what the AI suggests.
- Provide **Context** (e.g. "bearing housing") before clicking Analyze with AI for better results.
- For complex parts with many faces, use a capable model like `llama3.2` or `mistral`.
- Edit sketch names before clicking Create Sketches to organize your model tree.
- Hover over the Score column to see the breakdown of algorithmic vs AI scores.
- Right-click a row for quick-select options (same type, same group, similar area).

[Back to Index](../index.md)
