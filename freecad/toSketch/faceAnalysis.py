# SPDX-License-Identifier: GPL-2.0-or-later
"""Algorithmic face analysis, scoring, and grouping for smart selection."""
import math
from dataclasses import dataclass, field


@dataclass
class FaceInfo:
    """Geometric properties and scores for a single face."""
    index: int
    surface_type: str
    area: float
    normal: tuple
    edge_count: int
    bounding_box: tuple
    is_planar: bool
    center_of_mass: tuple
    parent_solid_index: int = 0
    algo_score: float = 0.0
    ai_name: str = ""
    ai_group: str = ""
    ai_score_boost: float = 0.0
    ai_recommended: bool = False


@dataclass
class AnalysisResult:
    """Complete analysis of a shape's faces."""
    faces: list = field(default_factory=list)
    groups: dict = field(default_factory=dict)
    ai_description: str = ""
    ai_strategy: str = ""


# Surface type scoring weights
_SURFACE_SCORES = {
    "Plane": 1.0,
    "Cylinder": 0.8,
    "Cone": 0.6,
    "Sphere": 0.4,
    "BSpline": 0.3,
    "Toroid": 0.5,
}

# Principal axis normals for profile detection
_PRINCIPAL_AXES = [
    (1, 0, 0), (-1, 0, 0),
    (0, 1, 0), (0, -1, 0),
    (0, 0, 1), (0, 0, -1),
]


def classify_surface(face):
    """Classify face surface type from str(face.Surface).

    Returns one of: 'Plane', 'Cylinder', 'Cone', 'Sphere', 'BSpline',
    'Toroid', or 'Other'.
    """
    s = str(face.Surface)
    for name in ("Plane", "Cylinder", "Cone", "Sphere", "BSpline", "Toroid"):
        if name in s:
            return name
    return "Other"


def analyze_face(face, index, solid_index=0):
    """Extract geometric properties from a single face.

    Args:
        face: A TopoDS_Face (or MockFace).
        index: Face index within the shape.
        solid_index: Index of the parent solid (for compounds).

    Returns:
        FaceInfo with all geometric fields populated (score not yet set).
    """
    surface_type = classify_surface(face)

    try:
        pr = face.ParameterRange
        u_mid = (pr[0] + pr[1]) / 2.0
        v_mid = (pr[2] + pr[3]) / 2.0
        n = face.normalAt(u_mid, v_mid)
        normal = (n.x, n.y, n.z)
    except Exception:
        normal = (0, 0, 0)

    bb = face.BoundBox
    bounding_box = (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)

    com = face.CenterOfMass
    center_of_mass = (com.x, com.y, com.z)

    return FaceInfo(
        index=index,
        surface_type=surface_type,
        area=face.Area,
        normal=normal,
        edge_count=len(face.Edges),
        bounding_box=bounding_box,
        is_planar=(surface_type == "Plane"),
        center_of_mass=center_of_mass,
        parent_solid_index=solid_index,
    )


def analyze_shape(shape):
    """Analyze all faces in a shape (Compound, Solid, or Shell).

    Returns a list of FaceInfo objects (scores not yet assigned).
    """
    faces = []
    if hasattr(shape, 'Solids') and shape.Solids:
        for si, solid in enumerate(shape.Solids):
            for face in solid.Faces:
                idx = len(faces)
                faces.append(analyze_face(face, idx, solid_index=si))
    elif hasattr(shape, 'Faces'):
        for i, face in enumerate(shape.Faces):
            faces.append(analyze_face(face, i))
    return faces


def _angle_between_normals(n1, n2):
    """Angle in degrees between two normal vectors."""
    dot = n1[0]*n2[0] + n1[1]*n2[1] + n1[2]*n2[2]
    l1 = math.sqrt(n1[0]**2 + n1[1]**2 + n1[2]**2)
    l2 = math.sqrt(n2[0]**2 + n2[1]**2 + n2[2]**2)
    if l1 < 1e-10 or l2 < 1e-10:
        return 180.0
    cos_a = max(-1.0, min(1.0, dot / (l1 * l2)))
    return math.degrees(math.acos(cos_a))


def group_by_normal(faces, angle_tol=5.0):
    """Group planar faces by normal direction.

    Args:
        faces: List of FaceInfo.
        angle_tol: Tolerance in degrees for grouping normals.

    Returns:
        Dict mapping group name to list of face indices.
    """
    _axis_names = {
        (0, 0, 1): "Top (Z+)", (0, 0, -1): "Bottom (Z-)",
        (0, 1, 0): "Back (Y+)", (0, -1, 0): "Front (Y-)",
        (1, 0, 0): "Right (X+)", (-1, 0, 0): "Left (X-)",
    }
    groups = {}
    for fi in faces:
        if not fi.is_planar:
            continue
        placed = False
        for axis, name in _axis_names.items():
            if _angle_between_normals(fi.normal, axis) < angle_tol:
                groups.setdefault(name, []).append(fi.index)
                placed = True
                break
        if not placed:
            groups.setdefault("Other planar", []).append(fi.index)
    return groups


def detect_duplicates(faces, tol=1e-3):
    """Find faces with identical area + edge count + surface type.

    Returns a list of sets, each containing indices of duplicate faces.
    """
    buckets = {}
    for fi in faces:
        key = (fi.surface_type, fi.edge_count)
        buckets.setdefault(key, []).append(fi)

    dup_groups = []
    for key, group in buckets.items():
        if len(group) < 2:
            continue
        # Within this bucket, cluster by area within tolerance
        used = set()
        for i, a in enumerate(group):
            if i in used:
                continue
            cluster = {a.index}
            for j in range(i + 1, len(group)):
                if j in used:
                    continue
                if abs(a.area - group[j].area) / max(a.area, 1e-10) < tol:
                    cluster.add(group[j].index)
                    used.add(j)
            if len(cluster) > 1:
                dup_groups.append(cluster)
                used.add(i)
    return dup_groups


def detect_profile_faces(faces):
    """Identify faces likely to be cross-section profiles.

    Criteria:
    - Planar face
    - Perpendicular to a principal axis (within 5 degrees)
    - Has many edges (>= 6, indicating complex profile)
    - Area in mid-range

    Returns list of face indices.
    """
    if not faces:
        return []

    areas = [fi.area for fi in faces if fi.area > 0]
    if not areas:
        return []
    median_area = sorted(areas)[len(areas) // 2]

    profile_indices = []
    for fi in faces:
        if not fi.is_planar:
            continue
        if fi.edge_count < 6:
            continue
        # Check if perpendicular to a principal axis
        is_perpendicular = False
        for axis in _PRINCIPAL_AXES:
            if _angle_between_normals(fi.normal, axis) < 5.0:
                is_perpendicular = True
                break
        if not is_perpendicular:
            continue
        # Prefer mid-range area (not too small, not too large)
        if fi.area > median_area * 0.1:
            profile_indices.append(fi.index)

    return profile_indices


def score_faces(faces):
    """Assign algo_score (0-100) to each face based on weighted criteria.

    Weights:
    - Area (mid-range preferred): 0.30
    - Edge count (complexity): 0.25
    - Surface type: 0.20
    - Profile likelihood: 0.15
    - Uniqueness: 0.10

    Modifies faces in-place and returns the list.
    """
    if not faces:
        return faces

    # Precompute stats
    areas = [fi.area for fi in faces if fi.area > 0]
    if not areas:
        return faces
    median_area = sorted(areas)[len(areas) // 2]
    max_area = max(areas)

    edge_counts = [fi.edge_count for fi in faces]
    max_edges = max(edge_counts) if edge_counts else 1

    profile_set = set(detect_profile_faces(faces))
    dup_groups = detect_duplicates(faces)
    dup_set = set()
    for g in dup_groups:
        dup_set.update(g)

    for fi in faces:
        # Area score: Gaussian-like around median, penalize extremes
        if max_area > 0 and median_area > 0:
            ratio = fi.area / median_area
            # Bell curve: peak at ratio=1, drops off
            area_score = math.exp(-0.5 * ((ratio - 1.0) / 1.5) ** 2)
        else:
            area_score = 0.5

        # Edge count score: more edges = more interesting, diminishing returns
        if max_edges > 0:
            edge_score = min(fi.edge_count / 20.0, 1.0)
        else:
            edge_score = 0.0

        # Surface type score
        type_score = _SURFACE_SCORES.get(fi.surface_type, 0.2)

        # Profile likelihood
        profile_score = 1.0 if fi.index in profile_set else 0.0

        # Uniqueness: penalize duplicates
        unique_score = 0.0 if fi.index in dup_set else 1.0

        raw = (0.30 * area_score +
               0.25 * edge_score +
               0.20 * type_score +
               0.15 * profile_score +
               0.10 * unique_score)

        fi.algo_score = max(0.0, min(100.0, raw * 100.0))

    return faces


def full_analysis(shape):
    """Run complete algorithmic analysis on a shape.

    Returns an AnalysisResult with scored faces and groups.
    """
    faces = analyze_shape(shape)
    faces = score_faces(faces)
    groups = group_by_normal(faces)
    return AnalysisResult(faces=faces, groups=groups)
