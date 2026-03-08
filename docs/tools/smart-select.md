# Smart Face Selection

## Overview

When importing a STEP file containing many objects and faces, manually browsing to find the right faces for sketch extraction is tedious. Smart Face Selection uses **algorithmic analysis + Ollama AI** to automatically score, name, group, and recommend faces — presenting an interactive dialog where you review and adjust the selection before proceeding.

## Prerequisites

- A **Part object** with a Shape (e.g. an imported STEP file).
- **Ollama** installed locally (optional, for AI features). Download from [ollama.com](https://ollama.com).

## Usage

1. Select a STEP object (solid or compound) in the model tree.
2. Click **Smart Face Selection** in the toSketch toolbar.
3. The dialog opens with:
   - **Algorithmic scores** for every face (available immediately).
   - **AI annotations** from Ollama (names, groups, recommendations — loads in background).
4. Review the face table:
   - Sort by score, area, type, or edge count.
   - Hover over a row to highlight that face in the 3D view.
   - Use **Select All**, **Deselect All**, or **AI Recommended** buttons.
   - Adjust the **Threshold** spinner to auto-check faces above a score.
5. Click **Create Sketches** to select the checked faces in FreeCAD.
6. Use the selected faces with **Face to Sketch** or other toSketch tools.

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

When Ollama is running, the tool sends face geometry data to your local LLM which provides:

- **Face names** — descriptive names like "Top mounting plate", "Main bore"
- **Face groups** — logical groupings like "Mounting features", "Bore features"
- **Score adjustments** — AI boosts or penalizes scores based on engineering significance
- **Part description** — what the part appears to be
- **Extraction strategy** — which faces to extract and why

### Configuration

In the Settings panel at the bottom of the dialog:

| Setting | Default | Description |
|---------|---------|-------------|
| Ollama Model | llama3.2 | Which model to use (dropdown shows installed models) |
| URL | localhost:11434 | Ollama server address |
| Enable AI | checked | Toggle AI features on/off |

Settings are saved in FreeCAD preferences and persist across sessions.

### Ollama Not Available

If Ollama is not installed or not running, the dialog still works with algorithmic scoring only. AI columns show "—" and the status bar indicates Ollama is unavailable.

## Tips

- Start with the default threshold of 60 — this typically selects the most interesting faces.
- Use **AI Recommended** after Ollama finishes to see what the AI suggests.
- For complex parts with many faces, use a capable model like `llama3.2` or `mistral`.
- Run Smart Face Selection before Face to Sketch to quickly identify the faces you need.

[Back to Index](../index.md)
