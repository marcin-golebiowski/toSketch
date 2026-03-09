# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for ollamaClient module (HTTP calls are mocked)."""
import json
import pytest
from unittest.mock import patch, MagicMock

from freecad.toSketch.faceAnalysis import FaceInfo
from freecad.toSketch.ollamaClient import (
    get_preferences,
    build_prompt,
    query_ollama,
    apply_ollama_annotations,
    check_ollama_available,
    list_ollama_models,
    _DEFAULTS,
)


def _make_face_info(index, surface_type="Plane", area=100.0, edge_count=4,
                    normal=(0, 0, 1), center=(0, 0, 0), score=50.0):
    return FaceInfo(
        index=index, surface_type=surface_type, area=area,
        normal=normal, edge_count=edge_count, bounding_box=(0, 0, 0, 10, 10, 0),
        is_planar=(surface_type == "Plane"), center_of_mass=center,
        parent_solid_index=0, algo_score=score,
    )


# ── get_preferences ───────────────────────────────────────────────
class TestGetPreferences:

    def test_defaults_when_no_freecad(self):
        prefs = get_preferences()
        assert prefs["url"] == _DEFAULTS["url"]
        assert prefs["model"] == _DEFAULTS["model"]
        assert prefs["timeout"] == _DEFAULTS["timeout"]
        assert prefs["enabled"] == _DEFAULTS["enabled"]


# ── build_prompt ──────────────────────────────────────────────────
class TestBuildPrompt:

    def test_contains_face_data(self):
        faces = [_make_face_info(0, area=245.3, edge_count=6)]
        prompt = build_prompt(faces, {})
        assert "Face 0" in prompt
        assert "245.3" in prompt
        assert "6 edges" in prompt

    def test_contains_groups(self):
        faces = [_make_face_info(0), _make_face_info(1)]
        groups = {"Top (Z+)": [0, 1]}
        prompt = build_prompt(faces, groups)
        assert "Top (Z+)" in prompt

    def test_all_surface_types(self):
        faces = [
            _make_face_info(0, surface_type="Plane"),
            _make_face_info(1, surface_type="Cylinder"),
            _make_face_info(2, surface_type="Cone"),
        ]
        prompt = build_prompt(faces, {})
        assert "Plane" in prompt
        assert "Cylinder" in prompt
        assert "Cone" in prompt

    def test_json_instruction(self):
        prompt = build_prompt([], {})
        assert "JSON" in prompt


# ── query_ollama ──────────────────────────────────────────────────
class TestQueryOllama:

    def test_success(self):
        mock_response = {
            "response": json.dumps({
                "face_annotations": [{"index": 0, "name": "Top plate", "group": "Plates"}],
                "part_description": "Test part",
                "extraction_strategy": "Extract face 0",
                "scoring_adjustments": [],
            })
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response).encode()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = query_ollama("test prompt", prefs=_DEFAULTS)

        assert result is not None
        assert result["part_description"] == "Test part"
        assert len(result["face_annotations"]) == 1

    def test_connection_error(self):
        import urllib.error
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("Connection refused")):
            result = query_ollama("test prompt", prefs=_DEFAULTS)
        assert result is None

    def test_timeout(self):
        import socket
        with patch("urllib.request.urlopen",
                   side_effect=socket.timeout("Timed out")):
            result = query_ollama("test prompt", prefs=_DEFAULTS)
        assert result is None

    def test_bad_json_response(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"response": "not valid json at all"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = query_ollama("test prompt", prefs=_DEFAULTS)
        assert result is None


# ── check_ollama_available ────────────────────────────────────────
class TestCheckAvailable:

    def test_online(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert check_ollama_available(prefs=_DEFAULTS) is True

    def test_offline(self):
        import urllib.error
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("refused")):
            assert check_ollama_available(prefs=_DEFAULTS) is False


# ── list_ollama_models ────────────────────────────────────────────
class TestListModels:

    def test_returns_model_names(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "models": [
                {"name": "llama3.2"},
                {"name": "mistral"},
            ]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            models = list_ollama_models(prefs=_DEFAULTS)
        assert models == ["llama3.2", "mistral"]

    def test_offline_returns_empty(self):
        import urllib.error
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("refused")):
            models = list_ollama_models(prefs=_DEFAULTS)
        assert models == []


# ── apply_ollama_annotations ─────────────────────────────────────
class TestApplyAnnotations:

    def test_apply_names_and_groups(self):
        faces = [_make_face_info(0), _make_face_info(1)]
        result = {
            "face_annotations": [
                {"index": 0, "name": "Top plate", "group": "Plates"},
                {"index": 1, "name": "Side wall", "group": "Walls"},
            ],
            "scoring_adjustments": [],
            "extraction_strategy": "",
        }
        apply_ollama_annotations(faces, result)
        assert faces[0].ai_name == "Top plate"
        assert faces[0].ai_group == "Plates"
        assert faces[1].ai_name == "Side wall"

    def test_apply_sketch_score(self):
        faces = [_make_face_info(0, score=50.0)]
        result = {
            "face_annotations": [
                {"index": 0, "name": "Top plate", "group": "Plates",
                 "sketch_score": 90, "sketch_name": "TopProfile",
                 "reason": "Complex profile"}
            ],
            "extraction_strategy": "",
        }
        apply_ollama_annotations(faces, result)
        assert faces[0].ai_sketch_score == 90.0
        assert faces[0].ai_sketch_name == "TopProfile"
        # Blended: 0.4 * 50 + 0.6 * 90 = 74
        assert faces[0].algo_score == 74.0
        assert faces[0].ai_recommended is True

    def test_sketch_name_empty_for_low_score(self):
        faces = [_make_face_info(0, score=50.0)]
        result = {
            "face_annotations": [
                {"index": 0, "name": "Wall", "group": "Walls",
                 "sketch_score": 15, "sketch_name": "",
                 "reason": "Simple wall"}
            ],
            "extraction_strategy": "",
        }
        apply_ollama_annotations(faces, result)
        assert faces[0].ai_sketch_name == ""

    def test_sketch_score_low_not_recommended(self):
        faces = [_make_face_info(0, score=50.0)]
        result = {
            "face_annotations": [
                {"index": 0, "name": "Simple wall", "group": "Walls",
                 "sketch_score": 20, "reason": "Featureless"}
            ],
            "extraction_strategy": "",
        }
        apply_ollama_annotations(faces, result)
        assert faces[0].ai_sketch_score == 20.0
        assert faces[0].ai_recommended is False

    def test_legacy_scoring_boost_fallback(self):
        """Old-style scoring_adjustments still work when no sketch_score."""
        faces = [_make_face_info(0, score=50.0)]
        result = {
            "face_annotations": [],
            "scoring_adjustments": [{"index": 0, "boost": 20}],
            "extraction_strategy": "",
        }
        apply_ollama_annotations(faces, result)
        assert faces[0].algo_score == 70.0
        assert faces[0].ai_score_boost == 20.0

    def test_sketch_score_clamped_to_range(self):
        faces = [_make_face_info(0, score=50.0)]
        result = {
            "face_annotations": [
                {"index": 0, "name": "X", "group": "Y",
                 "sketch_score": 150, "reason": "overflow"}
            ],
            "extraction_strategy": "",
        }
        apply_ollama_annotations(faces, result)
        assert faces[0].ai_sketch_score == 100.0

    def test_ai_recommended_from_sketch_score(self):
        faces = [_make_face_info(0), _make_face_info(1)]
        result = {
            "face_annotations": [
                {"index": 0, "name": "Profile", "group": "Main",
                 "sketch_score": 85, "reason": "Complex profile"},
                {"index": 1, "name": "Wall", "group": "Walls",
                 "sketch_score": 25, "reason": "Simple"},
            ],
            "extraction_strategy": "Focus on face 0",
        }
        apply_ollama_annotations(faces, result)
        assert faces[0].ai_recommended is True
        assert faces[1].ai_recommended is False

    def test_ai_recommended_fallback_to_strategy_text(self):
        """When no sketch_scores, fall back to strategy text parsing."""
        faces = [_make_face_info(0), _make_face_info(1)]
        result = {
            "face_annotations": [
                {"index": 0, "name": "Top", "group": "Plates"},
            ],
            "scoring_adjustments": [],
            "extraction_strategy": "Extract Face 0 for the main profile",
        }
        strategy = apply_ollama_annotations(faces, result)
        assert faces[0].ai_recommended is True
        assert faces[1].ai_recommended is False
        assert "Face 0" in strategy

    def test_partial_response(self):
        """Missing keys handled gracefully."""
        faces = [_make_face_info(0)]
        result = {"part_description": "Something"}
        strategy = apply_ollama_annotations(faces, result)
        assert strategy == ""
        assert faces[0].ai_name == ""

    def test_none_result(self):
        faces = [_make_face_info(0)]
        strategy = apply_ollama_annotations(faces, None)
        assert strategy == ""


# ── FaceInfo bounding_box ────────────────────────────────────────
class TestFaceInfoBoundingBox:

    def test_bounding_box_is_6_tuple(self):
        """Regression: bounding_box was empty tuple instead of 6-tuple."""
        fi = _make_face_info(0)
        assert len(fi.bounding_box) == 6
        assert fi.bounding_box == (0, 0, 0, 10, 10, 0)
