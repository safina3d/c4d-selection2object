# -*- coding: utf-8 -*-

"""
  Author  : Safina3D
  Website : https://safina3d.blogspot.com
  Description: Convert polygon selection tags or materials into separate objects.
"""

import os
import sys
import c4d
from c4d import bitmaps

# Plugins share sys.modules: the package name must stay unique
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PLUGIN_DIR)
try:
    from selections_to_objects import PLUGIN_ID, PLUGIN_VERSION
    from selections_to_objects.command import SelectionsToObjects
finally:
    sys.path.remove(PLUGIN_DIR)


if __name__ == '__main__':
    icon = bitmaps.BaseBitmap()
    icon.InitWith(os.path.join(PLUGIN_DIR, 'res', 'icons', 'selection.png'))

    c4d.plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=f'Selections To Objects {PLUGIN_VERSION}',
        info=c4d.PLUGINFLAG_COMMAND_OPTION_DIALOG,
        icon=icon,
        help='Create one object per polygon selection tag or material tag. '
             'SHIFT: place them inside the source object. CTRL: delete the source object.',
        dat=SelectionsToObjects()
    )
