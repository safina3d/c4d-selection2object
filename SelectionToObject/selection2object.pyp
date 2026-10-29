# -*- coding: utf-8 -*-

"""
  Author  : Safina3D
  Website : https://safina3d.blogspot.com
  Description: Convert polygon selection tags into separate objects.
"""

import os
import c4d
from c4d import gui, utils, bitmaps, BaseContainer

PLUGIN_ID = 1055923
PLUGIN_VERSION = "1.2.1"


def call_modeling_command(command, obj, doc):
    """Runs a modeling command on the active polygon selection of an object."""
    result = utils.SendModelingCommand(
        command=command,
        list=[obj],
        mode=c4d.MODELINGCOMMANDMODE_POLYGONSELECTION,
        bc=BaseContainer(),
        doc=doc
    )
    return result


def set_polygon_selection(obj, selection):
    """Replaces the active polygon selection of an object."""
    poly_selection = obj.GetPolygonS()
    poly_selection.DeselectAll()
    selection.CopyTo(poly_selection)


def is_button_pressed(button):
    """Checks if a specific qualifier key is pressed."""
    msg = BaseContainer()
    if not gui.GetInputState(c4d.BFM_INPUT_KEYBOARD, c4d.BFM_INPUT_CHANNEL, msg):
        return False
    return bool(msg.GetInt32(c4d.BFM_INPUT_QUALIFIER) & button)


def get_selection_tags(obj):
    """Returns polygon selection tags, last tag first."""
    return [tag for tag in reversed(obj.GetTags()) if tag.GetType() == c4d.Tpolygonselection]


def remove_selection_tags(obj):
    """Removes all polygon selection tags from an object."""
    for tag in obj.GetTags():
        if tag.GetType() == c4d.Tpolygonselection:
            tag.Remove()


def clean_split_materials(obj, selection_name):
    """Keeps materials applied to the whole object and those restricted to the given selection."""
    for tag in obj.GetTags():
        if tag.GetType() != c4d.Ttexture:
            continue

        restriction = tag[c4d.TEXTURETAG_RESTRICTION]
        if not restriction:
            # Applies to the whole object
            continue

        if restriction == selection_name:
            tag[c4d.TEXTURETAG_RESTRICTION] = ""
        else:
            tag.Remove()


def remove_converted_materials(obj, converted_names):
    """Removes materials restricted to selections that were converted into objects."""
    for tag in obj.GetTags():
        if tag.GetType() == c4d.Ttexture and tag[c4d.TEXTURETAG_RESTRICTION] in converted_names:
            tag.Remove()


class SelectionsToObjects(c4d.plugins.CommandData):

    def GetState(self, doc):
        """Enables the command if the active object is a polygon object."""
        op = doc.GetActiveObject()
        return c4d.CMD_ENABLED if op and op.IsInstanceOf(c4d.Opolygon) else 0

    def Execute(self, doc):
        """Converts polygon selection tags into separate objects."""
        if doc is None:
            return False

        original_obj = doc.GetActiveObject()
        if not original_obj or not original_obj.IsInstanceOf(c4d.Opolygon):
            return False

        if original_obj.GetPolygonCount() == 0:
            return False

        selection_tags = get_selection_tags(original_obj)
        if not selection_tags:
            return False

        delete_original_obj = is_button_pressed(c4d.QCTRL)
        make_child_objects = is_button_pressed(c4d.QSHIFT)

        # All splits are done on a single clone without children. Its selection tags are
        # updated by C4D each time polygons are deleted, so a polygon shared by several
        # selections goes only to the first processed one.
        work_obj = original_obj.GetClone(flags=c4d.COPYFLAGS_NO_HIERARCHY | c4d.COPYFLAGS_NO_BITS)
        work_tags = get_selection_tags(work_obj)

        converted_polygons = c4d.BaseSelect()
        converted_tags = []
        split_objects = []

        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, original_obj)

        try:
            for tag, work_tag in zip(selection_tags, work_tags):
                bs = tag.GetBaseSelect()
                if bs is None or bs.GetCount() == 0:
                    continue

                work_bs = work_tag.GetBaseSelect()
                if work_bs is None or work_bs.GetCount() == 0:
                    # Every polygon was already taken by another selection
                    converted_tags.append(tag)
                    continue

                set_polygon_selection(work_obj, work_bs)
                result = call_modeling_command(c4d.MCOMMAND_SPLIT, work_obj, doc)
                if not result:
                    continue

                split_obj = result[0]
                selection_name = tag.GetName()
                split_obj.SetName(selection_name)
                remove_selection_tags(split_obj)
                clean_split_materials(split_obj, selection_name)

                if not call_modeling_command(c4d.MCOMMAND_DELETE, work_obj, doc):
                    raise RuntimeError(f"Unable to delete polygons of selection '{selection_name}'")

                converted_polygons.Merge(bs)
                converted_tags.append(tag)
                split_objects.append(split_obj)

            if split_objects:
                # Delete all converted polygons from the original object at once
                set_polygon_selection(original_obj, converted_polygons)
                if not call_modeling_command(c4d.MCOMMAND_DELETE, original_obj, doc):
                    raise RuntimeError("Unable to delete polygons from the original object")
                original_obj.GetPolygonS().DeselectAll()

            converted_names = [tag.GetName() for tag in converted_tags]
            for tag in converted_tags:
                tag.Remove()
            remove_converted_materials(original_obj, converted_names)

            # Inserted in reverse order to keep the tags order in the object manager
            for split_obj in split_objects:
                if make_child_objects:
                    # Points are already in the original object space
                    split_obj.SetMl(c4d.Matrix())
                    doc.InsertObject(split_obj, parent=original_obj)
                else:
                    doc.InsertObject(split_obj, parent=None, pred=original_obj)
                doc.AddUndo(c4d.UNDOTYPE_NEW, split_obj)

            if delete_original_obj and not make_child_objects and split_objects:
                doc.AddUndo(c4d.UNDOTYPE_DELETEOBJ, original_obj)
                original_obj.Remove()

        except Exception as e:
            print(f"Selections To Objects - error during execution: {e}")
            doc.EndUndo()
            doc.DoUndo()
            c4d.EventAdd()
            return False

        doc.EndUndo()
        c4d.EventAdd()
        return True


if __name__ == '__main__':
    icon_absolute_path = os.path.join(os.path.dirname(__file__), 'res', 'icons', 'selection.tif')
    icon = bitmaps.BaseBitmap()
    icon.InitWith(icon_absolute_path)

    c4d.plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=f'Selections To Objects {PLUGIN_VERSION}',
        info=0,
        icon=icon,
        help='Convert polygon selection tags to objects. [CTRL] Delete Source. [SHIFT] Insert as Children',
        dat=SelectionsToObjects()
    )
