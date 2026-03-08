# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for toSharedFunc utility functions."""
import math
import pytest
import numpy as np
from conftest import MockVector, MockLineSegment

from freecad.toSketch.toSharedFunc import (
    are_contiguous,
    angle_between_lines,
    check3PointsOneLine,
    vectors_to_numpy,
    remove_duplicates,
    create_line_segments_from_vectors,
)


# ── Helpers ──────────────────────────────────────────────────────
V = MockVector


def _make_line(x1, y1, x2, y2):
    return MockLineSegment(V(x1, y1), V(x2, y2))


# ── are_contiguous ───────────────────────────────────────────────
class TestAreContiguous:

    def test_touching_end_to_start(self):
        """End of line 1 == Start of line 2."""
        l1 = _make_line(0, 0, 10, 0)
        l2 = _make_line(10, 0, 20, 0)
        assert are_contiguous(l1, l2) is True

    def test_gap_between_lines(self):
        """Lines with a gap → not contiguous."""
        l1 = _make_line(0, 0, 5, 0)
        l2 = _make_line(10, 0, 20, 0)
        assert are_contiguous(l1, l2) is False

    def test_reversed_touching(self):
        """Start of line 1 == End of line 2."""
        l1 = _make_line(10, 0, 20, 0)
        l2 = _make_line(0, 0, 10, 0)
        assert are_contiguous(l1, l2) is True

    def test_custom_tolerance(self):
        """Points within custom tolerance → contiguous."""
        l1 = _make_line(0, 0, 10, 0)
        l2 = _make_line(10.05, 0, 20, 0)
        assert are_contiguous(l1, l2, tolerance=0.1) is True
        assert are_contiguous(l1, l2, tolerance=0.01) is False


# ── angle_between_lines ─────────────────────────────────────────
class TestAngleBetweenLines:

    def test_right_angle(self):
        """90° corner: v1→v2 horizontal, v2→v3 vertical."""
        angle = angle_between_lines(V(0, 0), V(10, 0), V(10, 10))
        # The function returns |arccos(dot) - pi|
        # For perpendicular lines: arccos(0) = pi/2, |pi/2 - pi| = pi/2
        assert abs(angle - math.pi / 2) < 0.01

    def test_straight_line(self):
        """Collinear same-direction → |arccos(1) - pi| = pi."""
        angle = angle_between_lines(V(0, 0), V(5, 0), V(10, 0))
        # arccos(1.0)=0, |0 - pi| = pi
        assert abs(angle - math.pi) < 0.02

    def test_acute_angle(self):
        """45° turn."""
        angle = angle_between_lines(V(0, 0), V(10, 0), V(20, 10))
        # dir1=(1,0), dir2=(1,1)/sqrt(2), dot = 1/sqrt(2), arccos = pi/4
        # |pi/4 - pi| = 3pi/4... hmm, let's check actual behavior
        expected = abs(math.acos(1.0 / math.sqrt(2.0)) - math.pi)
        assert abs(angle - expected) < 0.01


# ── check3PointsOneLine ─────────────────────────────────────────
class TestCheck3PointsOneLine:

    def test_collinear(self):
        """Three points on a straight line → True."""
        assert check3PointsOneLine([V(0, 0), V(5, 0), V(10, 0)]) is True

    def test_not_collinear(self):
        """Three points forming a right angle → False."""
        assert check3PointsOneLine([V(0, 0), V(10, 0), V(10, 10)]) is False

    def test_nearly_collinear(self):
        """Three points almost collinear (within delta=0.012) → True."""
        assert check3PointsOneLine([V(0, 0), V(5, 0), V(10, 0.05)]) is True


# ── vectors_to_numpy ────────────────────────────────────────────
class TestVectorsToNumpy:

    def test_basic_conversion(self):
        """Converts list of vectors to (n, 3) array."""
        vecs = [V(1, 2, 3), V(4, 5, 6)]
        arr = vectors_to_numpy(vecs)
        assert arr.shape == (2, 3)
        np.testing.assert_allclose(arr[0], [1, 2, 3])
        np.testing.assert_allclose(arr[1], [4, 5, 6])

    def test_empty_list(self):
        """Empty list → empty array."""
        arr = vectors_to_numpy([])
        assert arr.shape == (0,)  # np.array([]) gives shape (0,)


# ── remove_duplicates ───────────────────────────────────────────
class TestRemoveDuplicates:

    def test_no_duplicates(self):
        """Distinct points → all kept."""
        pts = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]])
        result = remove_duplicates(pts)
        assert len(result) == 3

    def test_with_duplicates(self):
        """Consecutive duplicate points → removed."""
        pts = np.array([[0, 0, 0], [0, 0, 0], [1, 0, 0]])
        result = remove_duplicates(pts)
        assert len(result) == 2

    def test_tolerance(self):
        """Custom tolerance changes result."""
        pts = np.array([[0, 0, 0], [0.0001, 0, 0], [1, 0, 0]])
        result_tight = remove_duplicates(pts, tolerance=1e-6)
        result_loose = remove_duplicates(pts, tolerance=1e-3)
        assert len(result_tight) == 3  # all kept with tight tolerance
        assert len(result_loose) == 2  # near-duplicate removed


# ── create_line_segments_from_vectors ────────────────────────────
class TestCreateLineSegments:

    def test_basic(self):
        """N vectors → N-1 line segments."""
        vecs = [V(0, 0), V(5, 0), V(10, 5)]
        segments = create_line_segments_from_vectors(vecs)
        assert len(segments) == 2

    def test_two_points(self):
        """Minimum case → 1 segment."""
        vecs = [V(0, 0), V(10, 0)]
        segments = create_line_segments_from_vectors(vecs)
        assert len(segments) == 1

    def test_insufficient_points(self):
        """Less than 2 points → ValueError."""
        with pytest.raises(ValueError):
            create_line_segments_from_vectors([V(0, 0)])
