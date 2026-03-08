# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for faceAnalysis module."""
import math
import pytest
from conftest import MockVector, MockFace, MockShape, MockSolid, MockSurface, MockBoundBox

from freecad.toSketch.faceAnalysis import (
    classify_surface,
    analyze_face,
    analyze_shape,
    group_by_normal,
    detect_duplicates,
    detect_profile_faces,
    score_faces,
    full_analysis,
    FaceInfo,
    AnalysisResult,
)


# ── classify_surface ──────────────────────────────────────────────
class TestClassifySurface:

    def test_classify_plane(self):
        face = MockFace(surface_type="Plane")
        assert classify_surface(face) == "Plane"

    def test_classify_cylinder(self):
        face = MockFace(surface_type="Cylinder")
        assert classify_surface(face) == "Cylinder"

    def test_classify_cone(self):
        face = MockFace(surface_type="Cone")
        assert classify_surface(face) == "Cone"

    def test_classify_sphere(self):
        face = MockFace(surface_type="Sphere")
        assert classify_surface(face) == "Sphere"

    def test_classify_bspline(self):
        face = MockFace(surface_type="BSpline")
        assert classify_surface(face) == "BSpline"

    def test_classify_toroid(self):
        face = MockFace(surface_type="Toroid")
        assert classify_surface(face) == "Toroid"

    def test_classify_unknown(self):
        face = MockFace(surface_type="SomeWeirdSurface")
        assert classify_surface(face) == "Other"


# ── analyze_face ──────────────────────────────────────────────────
class TestAnalyzeFace:

    def test_basic_properties(self):
        face = MockFace(surface_type="Plane", area=50.0, edge_count=6,
                        normal=(0, 0, 1), center=(5, 3, 0))
        fi = analyze_face(face, index=3, solid_index=1)
        assert fi.index == 3
        assert fi.surface_type == "Plane"
        assert fi.area == 50.0
        assert fi.edge_count == 6
        assert fi.normal == (0, 0, 1)
        assert fi.is_planar is True
        assert fi.center_of_mass == (5, 3, 0)
        assert fi.parent_solid_index == 1
        assert fi.algo_score == 0.0  # not scored yet

    def test_cylinder_not_planar(self):
        face = MockFace(surface_type="Cylinder")
        fi = analyze_face(face, index=0)
        assert fi.is_planar is False


# ── analyze_shape ─────────────────────────────────────────────────
class TestAnalyzeShape:

    def test_shape_with_faces(self):
        faces = [MockFace(area=10), MockFace(area=20), MockFace(area=30)]
        shape = MockShape(faces=faces)
        result = analyze_shape(shape)
        assert len(result) == 3
        assert result[0].area == 10
        assert result[2].area == 30

    def test_shape_with_solids(self):
        s1 = MockSolid(faces=[MockFace(area=100), MockFace(area=200)])
        s2 = MockSolid(faces=[MockFace(area=300)])
        shape = MockShape(solids=[s1, s2])
        result = analyze_shape(shape)
        assert len(result) == 3
        assert result[0].parent_solid_index == 0
        assert result[2].parent_solid_index == 1

    def test_empty_shape(self):
        shape = MockShape(faces=[])
        result = analyze_shape(shape)
        assert len(result) == 0


# ── group_by_normal ───────────────────────────────────────────────
class TestGroupByNormal:

    def test_axis_aligned_groups(self):
        faces = [
            FaceInfo(0, "Plane", 10, (0, 0, 1), 4, (), True, (), 0),
            FaceInfo(1, "Plane", 10, (0, 0, 1), 4, (), True, (), 0),
            FaceInfo(2, "Plane", 10, (0, 0, -1), 4, (), True, (), 0),
        ]
        groups = group_by_normal(faces)
        assert "Top (Z+)" in groups
        assert len(groups["Top (Z+)"]) == 2
        assert "Bottom (Z-)" in groups

    def test_tolerance(self):
        # Normal slightly off Z+ axis (within 5 degrees)
        angle_rad = math.radians(3)
        normal = (math.sin(angle_rad), 0, math.cos(angle_rad))
        faces = [FaceInfo(0, "Plane", 10, normal, 4, (), True, (), 0)]
        groups = group_by_normal(faces, angle_tol=5.0)
        assert "Top (Z+)" in groups

    def test_non_planar_excluded(self):
        faces = [
            FaceInfo(0, "Cylinder", 10, (0, 0, 1), 4, (), False, (), 0),
        ]
        groups = group_by_normal(faces)
        assert len(groups) == 0

    def test_oblique_normal(self):
        # 45-degree normal — doesn't match any axis
        normal = (0.707, 0, 0.707)
        faces = [FaceInfo(0, "Plane", 10, normal, 4, (), True, (), 0)]
        groups = group_by_normal(faces)
        assert "Other planar" in groups


# ── detect_duplicates ─────────────────────────────────────────────
class TestDetectDuplicates:

    def test_identical_faces(self):
        faces = [
            FaceInfo(0, "Plane", 100.0, (0, 0, 1), 4, (), True, (), 0),
            FaceInfo(1, "Plane", 100.0, (0, 0, 1), 4, (), True, (), 0),
            FaceInfo(2, "Plane", 200.0, (0, 0, 1), 4, (), True, (), 0),
        ]
        dups = detect_duplicates(faces)
        assert len(dups) == 1
        assert {0, 1} == dups[0]

    def test_no_duplicates(self):
        faces = [
            FaceInfo(0, "Plane", 100.0, (0, 0, 1), 4, (), True, (), 0),
            FaceInfo(1, "Cylinder", 100.0, (0, 0, 1), 4, (), False, (), 0),
        ]
        dups = detect_duplicates(faces)
        assert len(dups) == 0

    def test_different_edge_counts(self):
        faces = [
            FaceInfo(0, "Plane", 100.0, (0, 0, 1), 4, (), True, (), 0),
            FaceInfo(1, "Plane", 100.0, (0, 0, 1), 6, (), True, (), 0),
        ]
        dups = detect_duplicates(faces)
        assert len(dups) == 0


# ── detect_profile_faces ─────────────────────────────────────────
class TestDetectProfileFaces:

    def test_complex_planar_face(self):
        faces = [
            FaceInfo(0, "Plane", 50.0, (0, 0, 1), 12, (), True, (), 0),
            FaceInfo(1, "Plane", 50.0, (0, 0, 1), 3, (), True, (), 0),
        ]
        profiles = detect_profile_faces(faces)
        assert 0 in profiles
        assert 1 not in profiles

    def test_non_planar_excluded(self):
        faces = [
            FaceInfo(0, "Cylinder", 50.0, (0, 0, 1), 12, (), False, (), 0),
        ]
        profiles = detect_profile_faces(faces)
        assert len(profiles) == 0

    def test_empty_faces(self):
        assert detect_profile_faces([]) == []


# ── score_faces ───────────────────────────────────────────────────
class TestScoreFaces:

    def test_scores_in_range(self):
        faces = [
            FaceInfo(0, "Plane", 50.0, (0, 0, 1), 8, (), True, (), 0),
            FaceInfo(1, "Cylinder", 20.0, (1, 0, 0), 4, (), False, (), 0),
            FaceInfo(2, "BSpline", 200.0, (0, 1, 0), 3, (), False, (), 0),
        ]
        scored = score_faces(faces)
        for fi in scored:
            assert 0.0 <= fi.algo_score <= 100.0

    def test_plane_scores_higher_than_bspline(self):
        faces = [
            FaceInfo(0, "Plane", 50.0, (0, 0, 1), 8, (), True, (), 0),
            FaceInfo(1, "BSpline", 50.0, (0, 0, 1), 8, (), False, (), 0),
        ]
        scored = score_faces(faces)
        assert scored[0].algo_score > scored[1].algo_score

    def test_more_edges_scores_higher(self):
        faces = [
            FaceInfo(0, "Plane", 50.0, (0, 0, 1), 12, (), True, (), 0),
            FaceInfo(1, "Plane", 50.0, (0, 0, 1), 2, (), True, (), 0),
        ]
        scored = score_faces(faces)
        assert scored[0].algo_score > scored[1].algo_score

    def test_duplicate_penalized(self):
        faces = [
            FaceInfo(0, "Plane", 50.0, (0, 0, 1), 8, (), True, (), 0),
            FaceInfo(1, "Plane", 50.0, (0, 0, 1), 8, (), True, (), 0),
            FaceInfo(2, "Plane", 100.0, (0, 0, 1), 8, (), True, (), 0),
        ]
        scored = score_faces(faces)
        # Face 2 is unique, faces 0 and 1 are duplicates
        assert scored[2].algo_score > scored[0].algo_score

    def test_empty_list(self):
        assert score_faces([]) == []

    def test_mid_area_preferred(self):
        # Face with median area should score higher than extreme
        faces = [
            FaceInfo(0, "Plane", 1.0, (0, 0, 1), 8, (), True, (), 0),
            FaceInfo(1, "Plane", 50.0, (0, 0, 1), 8, (), True, (), 0),
            FaceInfo(2, "Plane", 5000.0, (0, 0, 1), 8, (), True, (), 0),
        ]
        scored = score_faces(faces)
        # Median is 50, so face 1 should score highest on area component
        # (though other factors may also differ)
        assert scored[1].algo_score >= scored[0].algo_score


# ── full_analysis ─────────────────────────────────────────────────
class TestFullAnalysis:

    def test_returns_analysis_result(self):
        faces = [MockFace(area=50, edge_count=8, normal=(0, 0, 1)),
                 MockFace(surface_type="Cylinder", area=30, edge_count=4)]
        shape = MockShape(faces=faces)
        result = full_analysis(shape)
        assert isinstance(result, AnalysisResult)
        assert len(result.faces) == 2
        assert all(fi.algo_score >= 0 for fi in result.faces)

    def test_empty_shape(self):
        shape = MockShape(faces=[])
        result = full_analysis(shape)
        assert len(result.faces) == 0
        assert len(result.groups) == 0
