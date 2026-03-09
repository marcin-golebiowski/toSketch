# SPDX-License-Identifier: GPL-2.0-or-later
"""Ollama REST API client for AI-assisted face analysis."""
import json
import urllib.request
import urllib.error


# Default preferences
_DEFAULTS = {
    "url": "http://localhost:11434",
    "model": "llama3.2",
    "timeout": 360,
    "enabled": True,
    "temperature": 0.3,
    "system_prompt": (
        "You are a CAD geometry analyst specializing in sketch extraction from "
        "STEP files. Your task is to evaluate each face and assign a sketch_score "
        "(0-100) indicating how useful that face is for creating a 2D sketch.\n\n"
        "High sketch_score criteria (70-100):\n"
        "- Complex profiles: planar faces with many edges that capture the part's cross-section\n"
        "- Feature-defining faces: holes, slots, pockets, mounting patterns\n"
        "- Faces perpendicular to principal axes with meaningful geometry\n"
        "- Unique faces (not duplicated elsewhere on the part)\n\n"
        "Low sketch_score criteria (0-30):\n"
        "- Simple rectangular/circular faces that are just enclosure walls\n"
        "- Duplicate faces (e.g., matching pairs of identical fillets)\n"
        "- Tiny chamfer or fillet faces with minimal geometric content\n"
        "- Cylindrical/spherical faces that don't define useful profiles\n\n"
        "Respond ONLY with valid JSON."
    ),
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
            "temperature": grp.GetFloat("OllamaTemperature", _DEFAULTS["temperature"]),
            "system_prompt": grp.GetString("OllamaSystemPrompt", _DEFAULTS["system_prompt"]),
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
        grp.SetFloat("OllamaTemperature", prefs.get("temperature", _DEFAULTS["temperature"]))
        grp.SetString("OllamaSystemPrompt", prefs.get("system_prompt", _DEFAULTS["system_prompt"]))
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


def get_model_info(model_name, prefs=None):
    """Get details about a specific model from Ollama.

    Returns:
        Dict with keys like 'name', 'size', 'parameter_size', 'family',
        or empty dict on failure.
    """
    if prefs is None:
        prefs = get_preferences()
    url = prefs["url"].rstrip("/") + "/api/show"
    try:
        payload = json.dumps({"name": model_name}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, method="POST",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            details = data.get("details", {})
            model_info = data.get("model_info", {})
            return {
                "name": model_name,
                "family": details.get("family", ""),
                "parameter_size": details.get("parameter_size", ""),
                "quantization": details.get("quantization_level", ""),
                "format": details.get("format", ""),
            }
    except Exception:
        return {}


def build_prompt(faces, groups):
    """Build the user prompt for Ollama from face analysis data.

    Args:
        faces: List of FaceInfo objects.
        groups: Dict mapping group name to face indices.

    Returns:
        Prompt string (user portion — system prompt is sent separately).
    """
    lines = [
        "Analyze the following faces and respond ONLY with valid JSON.",
        "",
        "Required JSON structure:",
        '{',
        '  "face_annotations": [',
        '    {',
        '      "index": 0,',
        '      "name": "descriptive name",',
        '      "group": "functional group name",',
        '      "sketch_score": 85,',
        '      "sketch_name": "MainProfile_Top",',
        '      "reason": "why this score - what makes this face good/bad for sketch extraction"',
        '    }, ...',
        '  ],',
        '  "part_description": "brief description of what this part appears to be",',
        '  "extraction_strategy": "overall strategy: which faces to prioritize for sketch extraction and why"',
        '}',
        "",
        "IMPORTANT: sketch_score (0-100) must reflect how valuable each face is for 2D sketch extraction.",
        "Score high: complex profiles, feature-defining faces, cross-sections, mounting patterns.",
        "Score low: simple walls, duplicate fillets, tiny chamfers, featureless cylinders.",
        "",
        "sketch_name: A concise, descriptive name for the sketch if this face were extracted.",
        "Use CamelCase with no spaces, e.g. 'TopProfile', 'MountingHoles', 'BearingSeat', 'FrontCrossSection'.",
        "For low-scoring faces that shouldn't become sketches, use an empty string.",
        "",
        "Faces:",
    ]

    for fi in faces:
        parts = [f"Face {fi.index}: {fi.surface_type}"]
        parts.append(f"area={fi.area:.1f}mm\u00b2")
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
    body = {
        "model": prefs["model"],
        "prompt": prompt,
        "stream": False,
        "think": True,
        "format": "json",
    }
    system_prompt = prefs.get("system_prompt", _DEFAULTS["system_prompt"])
    if system_prompt:
        body["system"] = system_prompt
    temperature = prefs.get("temperature", _DEFAULTS["temperature"])
    if temperature is not None:
        body["options"] = {"temperature": temperature}
    payload = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json"})

    try:
        import FreeCAD as _fc
        _log = _fc.Console.PrintMessage
        _warn = _fc.Console.PrintWarning
    except Exception:
        _log = _warn = lambda m: None

    _log(f"[Ollama] POST {url} model={body['model']}\n")
    try:
        with urllib.request.urlopen(req, timeout=prefs["timeout"]) as resp:
            raw = resp.read().decode()
            data = json.loads(raw)
            response_text = data.get("response", "")
            thinking_text = data.get("thinking", "")
            # Some models (e.g. Qwen3.5) put content in "thinking" field
            if not response_text and thinking_text:
                response_text = thinking_text
            _log(f"[Ollama] Response: {response_text[:500]}\n")
            if thinking_text:
                _log(f"[Ollama] Thinking: {thinking_text[:500]}\n")
            return json.loads(response_text)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        _warn(f"[Ollama] Connection error: {e}\n")
        return None
    except json.JSONDecodeError as e:
        _warn(f"[Ollama] JSON parse error: {e}\n")
        return None
    except Exception as e:
        _warn(f"[Ollama] Error: {e}\n")
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

    # Apply face annotations (name, group, sketch_score)
    annotations = ollama_result.get("face_annotations", [])
    face_map = {fi.index: fi for fi in faces}
    for ann in annotations:
        idx = ann.get("index")
        if idx is not None and idx in face_map:
            fi = face_map[idx]
            fi.ai_name = ann.get("name", "")
            fi.ai_group = ann.get("group", "")
            fi.ai_sketch_name = ann.get("sketch_name", "")

            # Apply sketch_score from AI
            sketch_score = ann.get("sketch_score")
            if sketch_score is not None:
                fi.ai_sketch_score = max(0.0, min(100.0, float(sketch_score)))
                # Blend AI sketch score into algo_score: 40% algo + 60% AI
                fi.ai_score_boost = fi.ai_sketch_score - fi.algo_score
                fi.algo_score = max(0.0, min(100.0,
                    0.4 * fi.algo_score + 0.6 * fi.ai_sketch_score))

    # Backward compat: also handle old-style scoring_adjustments
    adjustments = ollama_result.get("scoring_adjustments", [])
    for adj in adjustments:
        idx = adj.get("index")
        boost = adj.get("boost", 0)
        if idx is not None and idx in face_map:
            fi = face_map[idx]
            # Only apply boost if no sketch_score was set for this face
            if fi.ai_sketch_score < 0:
                fi.ai_score_boost = float(boost)
                fi.algo_score = max(
                    0.0, min(100.0, fi.algo_score + float(boost)))

    # Mark AI-recommended: faces with sketch_score >= 60
    has_sketch_scores = any(fi.ai_sketch_score >= 0 for fi in faces)
    if has_sketch_scores:
        for fi in faces:
            if fi.ai_sketch_score >= 60:
                fi.ai_recommended = True
    else:
        # Fallback: check extraction strategy text for face mentions
        strategy = ollama_result.get("extraction_strategy", "")
        if strategy:
            for fi in faces:
                if (f"face {fi.index}" in strategy.lower()
                        or f"face{fi.index}" in strategy.lower()):
                    fi.ai_recommended = True

    return ollama_result.get("extraction_strategy", "")
