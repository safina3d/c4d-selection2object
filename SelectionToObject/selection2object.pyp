# -*- coding: utf-8 -*-

"""
  Author  : Safina3D
  Version : 1.2.0
  Website : https://safina3d.blogspot.com
  Description: Convert polygon selection tags into separate objects.
"""

import os
import c4d
from c4d import gui, utils, bitmaps, BaseContainer


def call_split_command(obj, doc):
    """Splits an object based on the active polygon selection."""
    if obj is None or doc is None:
        return None

    try:
        result = utils.SendModelingCommand(
            command=c4d.MCOMMAND_SPLIT,
            list=[obj.GetClone(flags=c4d.COPYFLAGS_NO_HIERARCHY | c4d.COPYFLAGS_NO_BITS)],
            mode=c4d.MODELINGCOMMANDMODE_POLYGONSELECTION,
            bc=BaseContainer(),
            doc=doc
        )
        return result[0] if result else None

    except Exception as e:
        print(f"Error in split command: {e}")
        return None


def is_button_pressed(button):
    """Checks if a specific button is pressed."""
    try:
        msg = BaseContainer()
        gui.GetInputState(c4d.BFM_INPUT_KEYBOARD, c4d.BFM_INPUT_CHANNEL, msg)
        return msg.GetLong(c4d.BFM_INPUT_QUALIFIER) & button
    except:
        return False


def remove_selection_tags(obj):
    """Removes all polygon selection tags from an object."""
    if obj is None:
        return

    tags = obj.GetTags()
    for tag in tags:
        if c4d.Tpolygonselection == tag.GetType():
            tag.Remove()


def remove_unused_materials(obj, selection_name):
    """Handles unused materials and clears restrictions."""
    if obj is None:
        return

    tags = obj.GetTags()
    for tag in tags:
        if tag.GetType() != c4d.Ttexture:
            continue

        texture_restriction_name = tag[c4d.TEXTURETAG_RESTRICTION]

        if selection_name is None and texture_restriction_name == "":
            continue

        # Has a restriction but we're not targeting any selection
        has_unmatched_restriction = selection_name is None and texture_restriction_name != ""
        # Has a restriction that doesn't match our target selection
        has_mismatching_selection = selection_name and texture_restriction_name != selection_name

        if has_unmatched_restriction or has_mismatching_selection:
            tag.Remove()
        else:
            # The restriction matches the selection
            tag[c4d.TEXTURETAG_RESTRICTION] = ""


class SelectionsToObjects(c4d.plugins.CommandData):

    def GetState(self, doc):
        """Enables the command if the active object is a polygon object."""
        op = doc.GetActiveObject()
        return c4d.CMD_ENABLED if op and op.IsInstanceOf(c4d.Opolygon) else False

    def Execute(self, doc):
        """Converts polygon selection tags into separate objects."""
        if doc is None:
            return False

        original_obj = doc.GetActiveObject()
        if not original_obj or not original_obj.IsInstanceOf(c4d.Opolygon):
            return False

        delete_original_obj = is_button_pressed(c4d.QCTRL)
        make_child_objects = is_button_pressed(c4d.QSHIFT)

        poly_selection = original_obj.GetPolygonS()
        if not poly_selection:
            return False

        count = original_obj.GetPolygonCount()
        if count == 0:
            return False

        tags = list(reversed(original_obj.GetTags()))
        new_obj_count = 0

        doc.StartUndo()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, original_obj)

        try:
            for tag in tags:
                if c4d.Tpolygonselection == tag.GetType():
                    poly_selection.DeselectAll()
                    bs = tag.GetBaseSelect()

                    if bs is None or bs.GetCount() == 0:
                        continue

                    for i in range(count):
                        if bs.IsSelected(i):
                            poly_selection.Select(i)

                    split_obj = call_split_command(original_obj, doc)
                    if split_obj:
                        selection_name = tag.GetName()
                        split_obj.SetName(selection_name)

                        # Delete selected polygons from original
                        utils.SendModelingCommand(
                            command=c4d.MCOMMAND_DELETE,
                            list=[original_obj],
                            mode=c4d.MODELINGCOMMANDMODE_POLYGONSELECTION,
                            doc=doc
                        )

                        remove_selection_tags(split_obj)
                        remove_unused_materials(obj=split_obj, selection_name=selection_name)

                        # Insert new object in hierarchy
                        if make_child_objects and original_obj:
                            doc.InsertObject(split_obj, parent=original_obj)
                        else:
                            doc.InsertObject(split_obj, parent=None, pred=original_obj)

                        doc.AddUndo(c4d.UNDOTYPE_NEW, split_obj)
                        new_obj_count += 1

                    tag.Remove()

            remove_unused_materials(obj=original_obj, selection_name=None)

            if delete_original_obj  and not make_child_objects and new_obj_count > 0 and original_obj:
                original_obj.Remove()

        except Exception as e:
            print(f"Error during execution: {e}")
            doc.DoUndo()
            return False

        finally:
            doc.EndUndo()
            c4d.EventAdd()

        return True

if __name__ == '__main__':
    icon_absolute_path = os.path.join(os.path.dirname(__file__), 'res/icons', 'selection.tif')
    icon = bitmaps.BaseBitmap()
    icon.InitWith(icon_absolute_path)

    c4d.plugins.RegisterCommandPlugin(
        id=1055923,
        str='Selections To Objects 1.2',
        info=0,
        icon=icon,
        help='Convert polygon selection tags to objects. [CTRL] Delete Source. [SHIFT] Insert as Children',
        dat=SelectionsToObjects()
    )
