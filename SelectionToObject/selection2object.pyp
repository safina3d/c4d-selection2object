# -*- coding: utf-8 -*-

"""
  Author  : Safina3D
  Version : 1.0.0
  Website : https://safina3d.blogspot.com
"""

import os
import c4d
from c4d import gui, utils, bitmaps, BaseContainer


def call_split_command(op, doc):
    res = utils.SendModelingCommand(command=c4d.MCOMMAND_SPLIT,
                                    list=[op],
                                    mode=c4d.MODELINGCOMMANDMODE_POLYGONSELECTION,
                                    bc=BaseContainer(),
                                    doc=doc)
    return res[0] if res else None


def check_button(button):
    msg = BaseContainer()
    gui.GetInputState(c4d.BFM_INPUT_KEYBOARD, c4d.BFM_INPUT_CHANNEL, msg)
    return msg.GetLong(c4d.BFM_INPUT_QUALIFIER) & button


def remove_selection_tags(obj):
    tags = obj.GetTags()
    for tag in tags:
        if c4d.Tpolygonselection == tag.GetType():
            tag.Remove()


class SelectionsToObjects(c4d.plugins.CommandData):

    def GetState(self, doc):
        op = doc.GetActiveObject()
        return c4d.CMD_ENABLED if op and op.IsInstanceOf(c4d.Opolygon) else False

    def Execute(self, doc):

        op = doc.GetActiveObject()

        delete_obj = check_button(c4d.QCTRL)
        make_child = check_button(c4d.QSHIFT)

        poly_selection = op.GetPolygonS()
        count = op.GetPolygonCount()
        tags = reversed(op.GetTags())
        new_obj_count = 0
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, op)
        for tag in tags:
            if c4d.Tpolygonselection == tag.GetType():
                poly_selection.DeselectAll()
                bs = tag.GetBaseSelect()

                # Empty selection case
                if bs.GetCount() == 0:
                    continue

                for i in xrange(count):
                    if bs.IsSelected(i):
                        poly_selection.Select(i)

                result = call_split_command(op, doc)
                if result:
                    result.SetName(tag[c4d.ID_BASELIST_NAME])
                    utils.SendModelingCommand(command=c4d.MCOMMAND_DELETE,
                                              list=[op],
                                              mode=c4d.MODELINGCOMMANDMODE_POLYGONSELECTION,
                                              doc=doc)
                    if make_child:
                        doc.InsertObject(result, op)
                    else:
                        doc.InsertObject(result, None, op)
                    doc.AddUndo(c4d.UNDOTYPE_NEW, result)
                    remove_selection_tags(result)
                    new_obj_count += 1

        if delete_obj and not make_child and new_obj_count > 0:
            op.Remove()

        doc.EndUndo()
        c4d.EventAdd()
        return True


if __name__ == '__main__':
    icon_absolute_path = os.path.join(os.path.dirname(__file__), 'res/icons', 'selection.tif')
    icon = bitmaps.BaseBitmap()
    icon.InitWith(icon_absolute_path)

    c4d.plugins.RegisterCommandPlugin(
        id=1039790,
        str='Selections To Objects',
        info=0,
        icon=icon,
        help='Convert polygon selection tags to objects',
        dat=SelectionsToObjects()
    )
