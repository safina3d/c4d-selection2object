# -*- coding: utf-8 -*-

"""Plugin options, saved in the Cinema 4D preferences, and their dialog."""

from dataclasses import dataclass

import c4d
from c4d import gui

from . import PLUGIN_ID

SPLIT_BY_SELECTIONS = 0
SPLIT_BY_MATERIALS = 1

# Container and dialog gadget ids
SPLIT_MODE = 1000
AS_CHILDREN = 1001
DELETE_SOURCE = 1002
DELETE_EMPTY_SOURCE = 1003
CENTER_AXIS = 1004
GROUP_UNDER_NULL = 1005

BOOL_OPTIONS = {
    AS_CHILDREN: ('as_children', 'Insert as children [SHIFT]'),
    DELETE_SOURCE: ('delete_source', 'Delete source object [CTRL]'),
    DELETE_EMPTY_SOURCE: ('delete_empty_source', 'Delete source object when empty'),
    CENTER_AXIS: ('center_axis', 'Center axis of generated objects'),
    GROUP_UNDER_NULL: ('group_under_null', 'Group generated objects under a null'),
}


@dataclass
class Options:
    split_mode: int = SPLIT_BY_SELECTIONS
    as_children: bool = False
    delete_source: bool = False
    delete_empty_source: bool = False
    center_axis: bool = False
    group_under_null: bool = False


def load_options():
    """Reads the options from the Cinema 4D preferences."""
    options = Options()
    bc = c4d.plugins.GetWorldPluginData(PLUGIN_ID)
    if bc is None:
        return options

    options.split_mode = bc.GetInt32(SPLIT_MODE, options.split_mode)
    for option_id, (name, _) in BOOL_OPTIONS.items():
        setattr(options, name, bc.GetBool(option_id, getattr(options, name)))
    return options


def save_options(options):
    """Writes the options in the Cinema 4D preferences."""
    bc = c4d.BaseContainer()
    bc.SetInt32(SPLIT_MODE, options.split_mode)
    for option_id, (name, _) in BOOL_OPTIONS.items():
        bc.SetBool(option_id, getattr(options, name))
    c4d.plugins.SetWorldPluginData(PLUGIN_ID, bc, False)


class OptionsDialog(gui.GeDialog):

    def __init__(self, options):
        super().__init__()
        self.options = options
        self.accepted = False

    def CreateLayout(self):
        self.SetTitle('Selections To Objects')

        if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2):
            self.GroupBorderSpace(10, 10, 10, 0)
            self.AddStaticText(0, c4d.BFH_LEFT, name='Split by')
            self.AddComboBox(SPLIT_MODE, c4d.BFH_SCALEFIT)
            self.AddChild(SPLIT_MODE, SPLIT_BY_SELECTIONS, 'Polygon selections')
            self.AddChild(SPLIT_MODE, SPLIT_BY_MATERIALS, 'Materials')
        self.GroupEnd()

        if self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=1):
            self.GroupBorderSpace(10, 5, 10, 5)
            for option_id, (_, label) in BOOL_OPTIONS.items():
                self.AddCheckbox(option_id, c4d.BFH_LEFT, 0, 0, label)
        self.GroupEnd()

        self.AddDlgGroup(c4d.DLG_OK | c4d.DLG_CANCEL)
        return True

    def InitValues(self):
        self.SetInt32(SPLIT_MODE, self.options.split_mode)
        for option_id, (name, _) in BOOL_OPTIONS.items():
            self.SetBool(option_id, getattr(self.options, name))
        return True

    def Command(self, id, msg):
        if id == c4d.DLG_OK:
            self.options.split_mode = self.GetInt32(SPLIT_MODE)
            for option_id, (name, _) in BOOL_OPTIONS.items():
                setattr(self.options, name, self.GetBool(option_id))
            self.accepted = True
            self.Close()
        elif id == c4d.DLG_CANCEL:
            self.Close()
        return True


def edit_options():
    """Opens the options dialog and saves the options if accepted."""
    dialog = OptionsDialog(load_options())
    dialog.Open(c4d.DLG_TYPE_MODAL, defaultw=300)
    if dialog.accepted:
        save_options(dialog.options)
