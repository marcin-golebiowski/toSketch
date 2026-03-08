# SPDX-License-Identifier: GPL-2.0-or-later
"""Ollama REST API client for AI-assisted face analysis."""
import json
import urllib.request
import urllib.error


# Default preferences
_DEFAULTS = {
    "url": "http://localhost:11434",
    "model": "llama3.2",
    "timeout": 60,
    "enabled": True,
}


def get_preferences():
    """Read Ollama preferences from FreeCAD parameter store.

    Returns a dict with keys: url, model, timeout, enabled.
    Falls back to defaults if FreeCAD params are not available.
    """
    try:
        import FreeCAD
        grp = FreeCAD.ParamGet(
            "User parameter:BaseApp/Preferences/Mod/toSketch/SmartSelect")
        return {
            "url": grp.GetString("OllamaUrl", _DEFAULTS["url"]),
            "model": grp.GetString("OllamaModel", _DEFAULTS["model"]),
            "timeout": grp.GetInt("OllamaTimeout", _DEFAULTS["timeout"]),
            "enabled": grp.GetBool("OllamaEnabled", _DEFAULTS["enabled"]),
        }
    except Exception:
        return dict(_DEFAULTS)


def save_preferences(prefs):
    """Save Ollama preferences to FreeCAD parameter store."""
    try:
        import FreeCAD
        grp = FreeCAD.ParamGet(
            "User parameter:BaseApp/Preferences/Mod/toSketch/SmartSelect")
        grp.SetString("OllamaUrl", prefs.get("url", _DEFAULTS["url"]))
        grp.SetString("OllamaModel", prefs.get("model", _DEFAULTS["model"]))
        grp.SetInt("OllamaTimeout", prefs.get("timeout", _DEFAULTS["timeout"]))
        grp.SetBool("OllamaEnabled", prefs.get("enabled", _DEFAULTS["enabled"]))
    except Exception:
        pass


def check_ollama_available(prefs=None):
    """Check if Ollama server is reachable.

    Args:
        prefs: Preferences dict. If None, reads from FreeCAD params.

    Returns:
        True if Ollama is running and responding.
    """
    if prefs is None:
        prefs = get_preferences()
    url = prefs["url"].rstrip("/") + "/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def list_ollama_models(prefs=None):
    """Get list of available model names from Ollama.

    Returns:
        List of model name strings, or empty list on failure.
    """
    if prefs is None:
        prefs = get_preferences()
    url = prefs["url"].rstrip("/") + "/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def build_prompt(faces, groups):
    """Build a structured prompt for Ollama from face analysis data.

    Args:
        faces: List of FaceInfo objects.
        groups: Dict mapping group name to face indices.

    Returns:
        Prompt string.
    """
    lines = [
        "You are a CAD geometry analyst. Analyze the following faces from a "
        "STEP file and respond ONLY with valid JSON (no markdown, no explanation).",
        "",
        "Provide this JSON structure:",
        '{',
        '  "face_annotations": [{"index": 0, "name": "descriptive name", "group": "group name"}, ...],',
        '  "scoring_adjustments": [{"index": 0, "boost": 15, "reason": "why"}, ...],',
        '  "part_description": "brief description of what this part appears to be",',
        '  "extraction_strategy": "which faces to extract as sketches and why"',
        '}',
        "",
        "Faces:",
    ]

    for fi in faces:
        parts = [f"Face {fi.index}: {fi.surface_type}"]
        parts.append(f"area={fi.area:.1f}mm²")
        parts.append(f"{fi.edge_count} edges")
        parts.append(f"normal=({fi.normal[0]:.2f},{fi.normal[1]:.2f},{fi.normal[2]:.2f})")
        parts.append(f"center=({fi.center_of_mass[0]:.1f},{fi.center_of_mass[1]:.1f},{fi.center_of_mass[2]:.1f})")
        parts.append(f"score={fi.algo_score:.0f}")
        lines.append("  " + ", ".join(parts))

    if groups:
        lines.append("")
        lines.append("Normal-based groups:")
        for name, indices in groups.items():
            lines.append(f"  {name}: faces {indices}")

    lines.append("")
    lines.append(
        "Focus on identifying: mounting faces, bore/hole profiles, "
        "structural features, and the best faces for sketch extraction."
    )

    return "\n".join(lines)


def query_ollama(prompt, prefs=None):
    """Send a prompt to Ollama and parse the JSON response.

    Args:
        prompt: The prompt string.
        prefs: Preferences dict. If None, reads from FreeCAD params.

    Returns:
        Parsed JSON dict on success, None on failure.
    """
    if prefs is None:
        prefs = get_preferences()

    url = prefs["url"].rstrip("/") + "/api/generate"
    payload = json.dumps({
        "model": prefs["model"],
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=prefs["timeout"]) as resp:
            data = json.loads(resp.read().decode())
            response_text = data.get("response", "")
            return json.loads(response_text)
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    except Exception:
        return None


def apply_ollama_annotations(faces, ollama_result):
    """Merge Ollama AI annotations into FaceInfo objects.

    Args:
        faces: List of FaceInfo objects (modified in-place).
        ollama_result: Parsed JSON dict from Ollama.

    Returns:
        The extraction_strategy string, or "" if not available.
    """
    if not ollama_result:
        return ""

    # Apply face annotations (name, group)
    annotations = ollama_result.get("face_annotations", [])
    face_map = {fi.index: fi for fi in faces}
    for ann in annotations:
        idx = ann.get("index")
        if idx is not None and idx in face_map:
            face_map[idx].ai_name = ann.get("name", "")
            face_map[idx].ai_group = ann.get("group", "")

    # Apply scoring adjustments
    adjustments = ollama_result.get("scoring_adjustments", [])
    for adj in adjustments:
        idx = adj.get("index")
        boost = adj.get("boost", 0)
        if idx is not None and idx in face_map:
            face_map[idx].ai_score_boost = float(boost)
            face_map[idx].algo_score = max(
                0.0, min(100.0, face_map[idx].algo_score + float(boost)))

    # Mark AI-recommended faces based on extraction strategy
    strategy = ollama_result.get("extraction_strategy", "")
    if strategy:
        for fi in faces:
            # Simple heuristic: if face index is mentioned in strategy text
            if f"face {fi.index}" in strategy.lower() or f"face{fi.index}" in strategy.lower():
                fi.ai_recommended = True

    return strategy
