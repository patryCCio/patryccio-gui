bl_info = {
    "name": "GUI by PatryCCio",
    "blender": (4, 4, 0),  
    "category": "Object",
    "author": "Patryccio",
    "description": "Helper",
    "version": (1, 0, 0),
    "support": "COMMUNITY",
}

import bpy
import importlib
import os
import sys

addon_path = os.path.dirname(__file__)
if addon_path not in sys.path:
    sys.path.append(addon_path)

from . import visible
from . import cameras
from . import bone_edit
from . import bone_edit2
from . import shapekeys
from . import vertex

modules = [
    visible,
    cameras,
    bone_edit,
    bone_edit2,
    shapekeys,
    vertex,
]

def import_modules():
    for module in modules:
        importlib.reload(module)  

def register():
    import_modules()  
    for module in modules:
        if hasattr(module, 'register'):
            module.register()  

def unregister():
    for module in modules:
        if hasattr(module, 'unregister'):
            module.unregister()  

if __name__ == "__main__":
    register()