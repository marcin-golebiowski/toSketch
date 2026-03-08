# SPDX-License-Identifier: GPL-2.0-or-later
"""
Conftest for integration tests — ensures the REAL FreeCAD modules are used,
undoing any mocks that the parent conftest.py may have installed.
"""
import sys


def _restore_real_freecad():
    """Remove mock FreeCAD/Part/Sketcher from sys.modules so the real ones load."""
    for mod_name in ('FreeCAD', 'Part', 'Sketcher'):
        mock = sys.modules.get(mod_name)
        if mock is not None and not hasattr(mock, '__file__'):
            del sys.modules[mod_name]

    # Now import the real modules (will raise ImportError if FreeCAD not available)
    import FreeCAD  # noqa: F401
    import Part     # noqa: F401
    import Sketcher  # noqa: F401


_restore_real_freecad()
