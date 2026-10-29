# -*- coding: utf-8 -*-

"""Cinema 4D command."""

import c4d
from c4d import gui

from .options import load_options, edit_options
from .split import convert_objects, get_polygon_objects


def is_button_pressed(button):
    """Checks if a specific qualifier key is pressed."""
    msg = c4d.BaseContainer()
    if not gui.GetInputState(c4d.BFM_INPUT_KEYBOARD, c4d.BFM_INPUT_CHANNEL, msg):
        return False
    return bool(msg.GetInt32(c4d.BFM_INPUT_QUALIFIER) & button)


class SelectionsToObjects(c4d.plugins.CommandData):

    def GetState(self, doc):
        """Enables the command if a polygon object is selected."""
        return c4d.CMD_ENABLED if get_polygon_objects(doc) else 0

    def Execute(self, doc):
        """Converts the selected polygon objects."""
        if doc is None:
            return False

        options = load_options()
        if is_button_pressed(c4d.QCTRL):
            options.delete_source = True
        if is_button_pressed(c4d.QSHIFT):
            options.as_children = True

        return convert_objects(doc, get_polygon_objects(doc), options)

    def ExecuteOptionID(self, doc, plugid, subid):
        """Opens the options dialog (gear icon)."""
        edit_options()
        return True
