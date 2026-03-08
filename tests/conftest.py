# SPDX-License-Identifier: GPL-2.0-or-later
"""
Mock FreeCAD, Sketcher, and Part modules so constraint tests can run
without a FreeCAD installation (pure pytest).
"""
import sys
import math
import types


# ──────────────────────────────────────────────────────────────────
# Vector mock
# ──────────────────────────────────────────────────────────────────
class MockVector:
    """Minimal FreeCAD.Vector replacement for 2D geometry tests."""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    @property
    def Length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def __sub__(self, other):
        return MockVector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, other):
        return MockVector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, scalar):
        return MockVector(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    def normalize(self):
        ln = self.Length
        if ln == 0:
            return MockVector(0, 0, 0)
        return MockVector(self.x / ln, self.y / ln, self.z / ln)

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def distanceToPoint(self, other):
        return (self - other).Length

    def getAngle(self, other):
        d = self.dot(other) / (self.Length * other.Length + 1e-30)
        d = max(-1.0, min(1.0, d))
        return math.acos(d)

    def __repr__(self):
        return f"V({self.x:.4f}, {self.y:.4f}, {self.z:.4f})"


# ──────────────────────────────────────────────────────────────────
# Geometry mocks
# ──────────────────────────────────────────────────────────────────
class MockLineSegment:
    """Part.LineSegment mock."""
    def __init__(self, start, end):
        self.StartPoint = start
        self.EndPoint = end


class MockArcOfCircle:
    """Part.ArcOfCircle mock with start/end points on the arc."""
    def __init__(self, center, radius, start_point, end_point):
        self.Center = center
        self.Radius = radius
        self.StartPoint = start_point
        self.EndPoint = end_point


class MockCircle:
    """Part.Circle mock (full circle, no start/end points)."""
    def __init__(self, center, radius):
        self.Center = center
        self.Radius = radius


# ──────────────────────────────────────────────────────────────────
# Constraint mock
# ──────────────────────────────────────────────────────────────────
class MockConstraint:
    """Records constraint creation args for verification."""
    def __init__(self, ctype, *args):
        self.Type = ctype
        # Positional args vary by constraint type
        if ctype in ('Equal', 'Parallel'):
            # (type, geo1, geo2)
            self.First = args[0] if len(args) > 0 else None
            self.Second = args[1] if len(args) > 1 else None
        elif ctype in ('Horizontal', 'Vertical'):
            self.First = args[0] if len(args) > 0 else None
        elif ctype == 'Coincident':
            self.First = args[0] if len(args) > 0 else None
            self.FirstPos = args[1] if len(args) > 1 else None
            self.Second = args[2] if len(args) > 2 else None
            self.SecondPos = args[3] if len(args) > 3 else None
        elif ctype == 'Tangent':
            self.First = args[0] if len(args) > 0 else None
            if len(args) == 4:
                self.FirstPos = args[1]
                self.Second = args[2]
                self.SecondPos = args[3]
            elif len(args) == 2:
                self.FirstPos = None
                self.Second = args[1]
                self.SecondPos = None
            else:
                self.FirstPos = None
                self.Second = None
                self.SecondPos = None
        elif ctype in ('Distance', 'Radius'):
            self.First = args[0] if len(args) > 0 else None
            self.Value = args[1] if len(args) > 1 else None
        elif ctype == 'Symmetric':
            self.First = args[0] if len(args) > 0 else None
            self.FirstPos = args[1] if len(args) > 1 else None
            self.Second = args[2] if len(args) > 2 else None
            self.SecondPos = args[3] if len(args) > 3 else None

    def __repr__(self):
        attrs = {k: v for k, v in self.__dict__.items() if v is not None}
        return f"Constraint({attrs})"


# ──────────────────────────────────────────────────────────────────
# Sketch mock
# ──────────────────────────────────────────────────────────────────
class MockSketch:
    """Mock Sketcher::SketchObject that records addConstraint calls."""

    TypeId = 'Sketcher::SketchObject'

    def __init__(self, geometry=None, constraints=None):
        self.Geometry = geometry or []
        self.Constraints = constraints or []
        self.added_constraints = []  # track what was added during test

    def addConstraint(self, constraint):
        self.added_constraints.append(constraint)
        self.Constraints.append(constraint)
        return len(self.Constraints) - 1


# ──────────────────────────────────────────────────────────────────
# Install mocks into sys.modules BEFORE any import of constraint code
# ──────────────────────────────────────────────────────────────────
def _install_mocks():
    # FreeCAD module
    freecad = types.ModuleType('FreeCAD')
    freecad.Vector = MockVector
    freecad.ActiveDocument = types.SimpleNamespace(recompute=lambda: None)
    sys.modules['FreeCAD'] = freecad

    # Part module
    part = types.ModuleType('Part')
    part.LineSegment = MockLineSegment
    part.ArcOfCircle = MockArcOfCircle
    part.Circle = MockCircle
    sys.modules['Part'] = part

    # Sketcher module
    sketcher = types.ModuleType('Sketcher')
    sketcher.Constraint = MockConstraint
    sys.modules['Sketcher'] = sketcher


_install_mocks()
