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
        if isinstance(x, MockVector):
            # Copy constructor: FreeCAD.Vector(other_vector)
            self.x = x.x
            self.y = x.y
            self.z = x.z
        else:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    @property
    def Length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def sub(self, other):
        return MockVector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __sub__(self, other):
        return MockVector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, other):
        return MockVector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, other):
        if isinstance(other, MockVector):
            # FreeCAD Vector * Vector = dot product
            return self.x * other.x + self.y * other.y + self.z * other.z
        return MockVector(self.x * other, self.y * other, self.z * other)

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
    def __init__(self, *args):
        if len(args) == 4:
            # (center, radius, start_point, end_point) — test convenience
            self.Center = args[0]
            self.Radius = args[1]
            self.StartPoint = args[2]
            self.EndPoint = args[3]
        elif len(args) == 3:
            # (circle, start_angle, end_angle) — FreeCAD API signature
            circle = args[0]
            start_angle = args[1]
            end_angle = args[2]
            self.Center = circle.Center
            self.Radius = circle.Radius
            self.StartPoint = MockVector(
                circle.Center.x + circle.Radius * math.cos(start_angle),
                circle.Center.y + circle.Radius * math.sin(start_angle))
            self.EndPoint = MockVector(
                circle.Center.x + circle.Radius * math.cos(end_angle),
                circle.Center.y + circle.Radius * math.sin(end_angle))
        else:
            raise TypeError(f"MockArcOfCircle expects 3 or 4 args, got {len(args)}")


class MockCircle:
    """Part.Circle mock (full circle, no start/end points).

    Supports two calling conventions:
    - MockCircle(center, radius) — test convenience
    - MockCircle(center, normal, radius) — FreeCAD API
    - MockCircle() — default
    """
    def __init__(self, *args):
        if len(args) == 0:
            self.Center = MockVector(0, 0, 0)
            self.Radius = 1.0
        elif len(args) == 2:
            self.Center = args[0]
            self.Radius = args[1]
        elif len(args) == 3:
            self.Center = args[0]
            # args[1] is the normal vector — ignored in mock
            self.Radius = args[2]
        else:
            raise TypeError(f"MockCircle expects 0, 2, or 3 args, got {len(args)}")


class MockBSplineCurve:
    """Part.BSplineCurve mock for bspline2arc tests."""
    TypeId = 'Part::GeomBSplineCurve'

    def __init__(self, points, parameter_range=(0.0, 1.0)):
        self._points = points
        self._param_range = parameter_range
        self.StartPoint = points[0]
        self.EndPoint = points[-1]

    @property
    def ParameterRange(self):
        return self._param_range

    def value(self, t):
        """Linear interpolation along stored points."""
        frac = (t - self._param_range[0]) / (self._param_range[1] - self._param_range[0])
        frac = max(0.0, min(1.0, frac))
        idx = frac * (len(self._points) - 1)
        i = int(idx)
        if i >= len(self._points) - 1:
            return self._points[-1]
        f = idx - i
        p1, p2 = self._points[i], self._points[i + 1]
        return MockVector(
            p1.x + f * (p2.x - p1.x),
            p1.y + f * (p2.y - p1.y),
            p1.z + f * (p2.z - p1.z))

    def getPoles(self):
        return list(self._points)

    @property
    def NbPoles(self):
        return len(self._points)


class MockPoint:
    """Part.Point mock."""
    TypeId = 'Part::GeomPoint'

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.XYZ = MockVector(x, y, z)


class MockEllipse:
    """Part.Ellipse mock."""
    TypeId = 'Part::GeomEllipse'

    def __init__(self, center, major_radius, minor_radius):
        self.Center = center
        self.MajorRadius = major_radius
        self.MinorRadius = minor_radius


# ──────────────────────────────────────────────────────────────────
# Face / Shape mocks (for faceAnalysis tests)
# ──────────────────────────────────────────────────────────────────
class MockSurface:
    """Mock for face.Surface — str(face.Surface) returns '<Type object>'."""
    def __init__(self, type_name="Plane"):
        self._type = type_name
    def __str__(self):
        return f"<{self._type} object>"


class MockBoundBox:
    """Mock for face.BoundBox."""
    def __init__(self, xmin=0, ymin=0, zmin=0, xmax=10, ymax=10, zmax=0):
        self.XMin = xmin
        self.YMin = ymin
        self.ZMin = zmin
        self.XMax = xmax
        self.YMax = ymax
        self.ZMax = zmax


class MockEdge:
    """Minimal edge mock."""
    def __init__(self, length=1.0):
        self.Length = length


class MockFace:
    """Mock for a TopoDS_Face."""
    def __init__(self, surface_type="Plane", area=100.0, edge_count=4,
                 normal=(0, 0, 1), center=(0, 0, 0), bbox=None):
        self.Surface = MockSurface(surface_type)
        self.Area = area
        self.Edges = [MockEdge() for _ in range(edge_count)]
        self._normal = normal
        self.CenterOfMass = MockVector(*center)
        self.BoundBox = bbox or MockBoundBox()

    def normalAt(self, u, v):
        return MockVector(*self._normal)

    @property
    def ParameterRange(self):
        return (0.0, 1.0, 0.0, 1.0)


class MockSolid:
    """Mock for a TopoDS_Solid containing faces."""
    def __init__(self, faces=None):
        self.Faces = faces or []
        self.ShapeType = "Solid"


class MockShape:
    """Mock for Part.Shape (Compound/Solid/Shell)."""
    def __init__(self, faces=None, solids=None):
        self.Faces = faces or []
        self.Solids = solids or []
        if solids:
            self.ShapeType = "Compound"
        else:
            self.ShapeType = "Shell"


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
        elif ctype == 'Angle':
            self.First = args[0] if len(args) > 0 else None
            self.Second = args[1] if len(args) > 1 else None
            self.Value = args[2] if len(args) > 2 else None

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

    def addGeometry(self, geo, construction=False):
        self.Geometry.append(geo)
        return len(self.Geometry) - 1

    def delGeometry(self, index):
        del self.Geometry[index]
        # Remove constraints referencing this index and shift higher indices
        new_constraints = []
        for c in self.Constraints:
            first = getattr(c, 'First', None)
            second = getattr(c, 'Second', None)
            if first == index or second == index:
                continue  # remove constraints referencing deleted geometry
            if first is not None and first > index:
                c.First = first - 1
            if second is not None and second > index:
                c.Second = second - 1
            new_constraints.append(c)
        self.Constraints = new_constraints

    @property
    def GeometryCount(self):
        return len(self.Geometry)

    def recompute(self):
        pass


# ──────────────────────────────────────────────────────────────────
# Install mocks into sys.modules BEFORE any import of constraint code
# ──────────────────────────────────────────────────────────────────
def _install_mocks():
    # FreeCAD module
    freecad = types.ModuleType('FreeCAD')
    freecad.Vector = MockVector
    freecad.ActiveDocument = types.SimpleNamespace(recompute=lambda: None)
    freecad.Console = types.SimpleNamespace(
        PrintMessage=lambda msg: None,
        PrintError=lambda msg: None,
    )
    sys.modules['FreeCAD'] = freecad

    # Part module
    part = types.ModuleType('Part')
    part.LineSegment = MockLineSegment
    part.ArcOfCircle = MockArcOfCircle
    part.Circle = MockCircle
    part.BSplineCurve = MockBSplineCurve
    part.Point = MockPoint
    part.Ellipse = MockEllipse
    sys.modules['Part'] = part

    # Sketcher module
    sketcher = types.ModuleType('Sketcher')
    sketcher.Constraint = MockConstraint
    sys.modules['Sketcher'] = sketcher

    # Draft module (used by toSharedFunc)
    draft = types.ModuleType('Draft')
    draft.makeSketch = lambda *a, **kw: None
    sys.modules['Draft'] = draft

    # FreeCADGui module (used by symmetricConstraints preview)
    gui = types.ModuleType('FreeCADGui')
    gui.ActiveDocument = types.SimpleNamespace(ActiveView=None)
    gui.showMainWindow = lambda: None
    sys.modules['FreeCADGui'] = gui


_install_mocks()
