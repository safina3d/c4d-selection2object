# -*- coding: utf-8 -*-

"""Plugin options, saved in the Cinema 4D preferences, and their dialog."""

from dataclasses import dataclass

import c4d
from c4d import gui

from . import PLUGIN_ID

SPLIT_BY_SELECTIONS = 0
SPLIT_BY_MATERIALS = 1

# Container ids
SPLIT_MODE = 1000
AS_CHILDREN = 1001
DELETE_SOURCE = 1002
DELETE_EMPTY_SOURCE = 1003
CENTER_AXIS = 1004
GROUP_UNDER_NULL = 1005

BOOL_OPTIONS = {
    AS_CHILDREN: 'as_children',
    DELETE_SOURCE: 'delete_source',
    DELETE_EMPTY_SOURCE: 'delete_empty_source',
    CENTER_AXIS: 'center_axis',
    GROUP_UNDER_NULL: 'group_under_null',
}

# Dialog only gadgets
PLACEMENT = 2000
SOURCE_ACTION = 2001

PLACE_NEXT_TO = 0
PLACE_INSIDE = 1

KEEP_SOURCE = 0
DELETE_SOURCE_ALWAYS = 1
DELETE_SOURCE_IF_EMPTY = 2


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
    for option_id, name in BOOL_OPTIONS.items():
        setattr(options, name, bc.GetBool(option_id, getattr(options, name)))
    return options


def save_options(options):
    """Writes the options in the Cinema 4D preferences."""
    bc = c4d.BaseContainer()
    bc.SetInt32(SPLIT_MODE, options.split_mode)
    for option_id, name in BOOL_OPTIONS.items():
        bc.SetBool(option_id, getattr(options, name))
    c4d.plugins.SetWorldPluginData(PLUGIN_ID, bc, False)


class OptionsDialog(gui.GeDialog):

    def __init__(self, options):
        super().__init__()
        self.options = options
        self.accepted = False

    def add_combo_box(self, gadget_id, label, items):
        self.AddStaticText(0, c4d.BFH_LEFT, name=label)
        self.AddComboBox(gadget_id, c4d.BFH_SCALEFIT)
        for value, text in items:
            self.AddChild(gadget_id, value, text)

    def begin_section(self, title, cols):
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=cols, title=title)
        self.GroupBorder(c4d.BORDER_GROUP_IN)
        self.GroupBorderSpace(8, 4, 8, 8)
        self.GroupSpace(8, 4)

    def CreateLayout(self):
        self.SetTitle('Selections To Objects - Options')

        self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1)
        self.GroupBorderSpace(10, 10, 10, 0)
        self.GroupSpace(0, 8)

        self.begin_section('Split', 2)
        self.add_combo_box(SPLIT_MODE, 'Create one object per', [
            (SPLIT_BY_SELECTIONS, 'Polygon selection tag'),
            (SPLIT_BY_MATERIALS, 'Material tag'),
        ])
        self.GroupEnd()

        self.begin_section('New objects', 2)
        self.add_combo_box(PLACEMENT, 'Place them', [
            (PLACE_NEXT_TO, 'Next to the source object'),
            (PLACE_INSIDE, 'Inside the source object, as children  [SHIFT]'),
        ])
        self.AddStaticText(0, c4d.BFH_LEFT, name='')
        self.AddCheckbox(GROUP_UNDER_NULL, c4d.BFH_LEFT, 0, 0, 'Put them in a Null named after the source object')
        self.AddStaticText(0, c4d.BFH_LEFT, name='')
        self.AddCheckbox(CENTER_AXIS, c4d.BFH_LEFT, 0, 0, 'Move the axis of each one to the center of its polygons')
        self.GroupEnd()

        self.begin_section('Source object', 2)
        self.add_combo_box(SOURCE_ACTION, 'After conversion', [
            (KEEP_SOURCE, 'Keep it, with its remaining polygons'),
            (DELETE_SOURCE_ALWAYS, 'Delete it  [CTRL]'),
            (DELETE_SOURCE_IF_EMPTY, 'Delete it only if no polygon is left'),
        ])
        self.AddStaticText(0, c4d.BFH_LEFT, name='')
        self.AddStaticText(0, c4d.BFH_LEFT, name='Its child objects are always kept.')
        self.GroupEnd()

        self.GroupEnd()

        self.AddDlgGroup(c4d.DLG_OK | c4d.DLG_CANCEL)
        return True

    def update_enabling(self):
        # New objects placed inside the source object would be deleted with it
        self.Enable(SOURCE_ACTION, self.GetInt32(PLACEMENT) != PLACE_INSIDE)

    def InitValues(self):
        self.SetInt32(SPLIT_MODE, self.options.split_mode)
        self.SetInt32(PLACEMENT, PLACE_INSIDE if self.options.as_children else PLACE_NEXT_TO)
        if self.options.delete_source:
            source_action = DELETE_SOURCE_ALWAYS
        elif self.options.delete_empty_source:
            source_action = DELETE_SOURCE_IF_EMPTY
        else:
            source_action = KEEP_SOURCE
        self.SetInt32(SOURCE_ACTION, source_action)
        self.SetBool(GROUP_UNDER_NULL, self.options.group_under_null)
        self.SetBool(CENTER_AXIS, self.options.center_axis)
        self.update_enabling()
        return True

    def Command(self, id, msg):
        if id == PLACEMENT:
            self.update_enabling()
        elif id == c4d.DLG_OK:
            source_action = self.GetInt32(SOURCE_ACTION)
            self.options.split_mode = self.GetInt32(SPLIT_MODE)
            self.options.as_children = self.GetInt32(PLACEMENT) == PLACE_INSIDE
            self.options.delete_source = source_action == DELETE_SOURCE_ALWAYS
            self.options.delete_empty_source = source_action == DELETE_SOURCE_IF_EMPTY
            self.options.group_under_null = self.GetBool(GROUP_UNDER_NULL)
            self.options.center_axis = self.GetBool(CENTER_AXIS)
            self.accepted = True
            self.Close()
        elif id == c4d.DLG_CANCEL:
            self.Close()
        return True


def edit_options():
    """Opens the options dialog and saves the options if accepted."""
    dialog = OptionsDialog(load_options())
    dialog.Open(c4d.DLG_TYPE_MODAL, defaultw=420)
    if dialog.accepted:
        save_options(dialog.options)
