# -*- coding: utf-8 -*-

"""
  Author  : Safina3D
  Version : 1.2.0
  Website : https://safina3d.blogspot.com
"""

import os
import c4d
from c4d import gui, utils, bitmaps, BaseContainer


def call_split_command(obj, doc):
    result = utils.SendModelingCommand(command=c4d.MCOMMAND_SPLIT,
                                    list=[obj.GetClone(flags=c4d.COPYFLAGS_NO_HIERARCHY|c4d.COPYFLAGS_NO_BITS)],
                                    mode=c4d.MODELINGCOMMANDMODE_POLYGONSELECTION,
                                    bc=BaseContainer(),
                                    doc=doc)
    return result[0] if result else None


def check_button(button):
    msg = BaseContainer()
    gui.GetInputState(c4d.BFM_INPUT_KEYBOARD, c4d.BFM_INPUT_CHANNEL, msg)
    return msg.GetLong(c4d.BFM_INPUT_QUALIFIER) & button


def remove_selection_tags(obj):
    tags = obj.GetTags()
    for tag in tags:
        if c4d.Tpolygonselection == tag.GetType():
            tag.Remove()

def remove_unused_materials_from_split_obj(obj, selection_name):
    if obj is None:
        return

    tags = obj.GetTags()
    for tag in tags:
        if tag.GetType() != c4d.Ttexture:
            continue
        
        restriction_name = tag[c4d.TEXTURETAG_RESTRICTION]

        if restriction_name == selection_name:
            # Erase restriction as we've already split the object
            tag[c4d.TEXTURETAG_RESTRICTION] = ""
        elif restriction_name != "":
            tag.Remove()

class SelectionsToObjects(c4d.plugins.CommandData):

    def GetState(self, doc):
        op = doc.GetActiveObject()
        return c4d.CMD_ENABLED if op and op.IsInstanceOf(c4d.Opolygon) else False

    def Execute(self, doc):

        original_obj = doc.GetActiveObject()

        delete_obj = check_button(c4d.QCTRL)
        make_child = check_button(c4d.QSHIFT)

        poly_selection = original_obj.GetPolygonS()
        count = original_obj.GetPolygonCount()
        tags = reversed(original_obj.GetTags())
        new_obj_count = 0
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, original_obj)

        for tag in tags:
            if c4d.Tpolygonselection == tag.GetType():
                poly_selection.DeselectAll()
                bs = tag.GetBaseSelect()

                # Empty selection case
                if bs.GetCount() == 0:
                    continue

                for i in range(count):
                    if bs.IsSelected(i):
                        poly_selection.Select(i)

                split_obj = call_split_command(original_obj, doc)
                if split_obj:
                    selection_name = tag.GetName()
                    split_obj.SetName(selection_name)
                    utils.SendModelingCommand(command=c4d.MCOMMAND_DELETE,
                                              list=[original_obj],
                                              mode=c4d.MODELINGCOMMANDMODE_POLYGONSELECTION,
                                              doc=doc)
                    
                    remove_selection_tags(split_obj)
                    remove_unused_materials(obj=split_obj, selection_name=selection_name)
                    
                    if make_child:_from_split_obj
                        doc.InsertObject(split_obj, parent=original_obj)
                    else:
                        doc.InsertObject(split_obj, parent=None, pred=original_obj)

                    doc.AddUndo(c4d.UNDOTYPE_NEW, split_obj)
                    new_obj_count += 1

                tag.Remove()

        # Original object is typically covered with redundant materials
        remove_unused_materials(obj=original_obj, selection_name=None)

        if delete_obj and not make_child and new_obj_count > 0:
            original_obj.Remove()

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
