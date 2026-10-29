# -*- coding: utf-8 -*-

"""Converts groups of polygons into separate objects."""

import c4d
from c4d import utils

from .groups import build_groups, get_tags
from .options import SPLIT_BY_MATERIALS

SELECTION_TAG_TYPES = (c4d.Tpolygonselection, c4d.Tpointselection, c4d.Tedgeselection)

TRANSFORM_PARAMETERS = (
    c4d.ID_BASEOBJECT_REL_POSITION, c4d.ID_BASEOBJECT_REL_ROTATION, c4d.ID_BASEOBJECT_REL_SCALE,
    c4d.ID_BASEOBJECT_FROZEN_POSITION, c4d.ID_BASEOBJECT_FROZEN_ROTATION, c4d.ID_BASEOBJECT_FROZEN_SCALE,
)


def call_modeling_command(command, obj, doc):
    """Runs a modeling command on the active polygon selection of an object."""
    return utils.SendModelingCommand(
        command=command,
        list=[obj],
        mode=c4d.MODELINGCOMMANDMODE_POLYGONSELECTION,
        bc=c4d.BaseContainer(),
        doc=doc
    )


def set_polygon_selection(obj, selection):
    """Replaces the active polygon selection of an object."""
    poly_selection = obj.GetPolygonS()
    poly_selection.DeselectAll()
    selection.CopyTo(poly_selection)


def get_polygon_objects(doc):
    """Returns the selected polygon objects."""
    objects = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_NONE)
    return [obj for obj in objects if obj.IsInstanceOf(c4d.Opolygon) and obj.GetPolygonCount() > 0]


def remove_empty_selection_tags(obj, tags=None):
    """Removes selection tags without any selected element."""
    tags = obj.GetTags() if tags is None else tags
    for tag in tags:
        if tag.GetType() in SELECTION_TAG_TYPES and tag.GetBaseSelect().GetCount() == 0:
            tag.Remove()


def clean_selection_piece(piece, selection_name):
    """Keeps materials applied to the whole object and those restricted to the given selection."""
    for tag in get_tags(piece, c4d.Tpolygonselection):
        tag.Remove()

    for tag in get_tags(piece, c4d.Ttexture):
        restriction = tag[c4d.TEXTURETAG_RESTRICTION]
        if not restriction:
            # Applies to the whole object
            continue

        if restriction == selection_name:
            tag[c4d.TEXTURETAG_RESTRICTION] = ""
        else:
            tag.Remove()


def clean_material_piece(piece, texture_index):
    """Keeps only the material the piece was made from."""
    for index, tag in enumerate(get_tags(piece, c4d.Ttexture)):
        if index == texture_index:
            tag[c4d.TEXTURETAG_RESTRICTION] = ""
        else:
            tag.Remove()


def clean_source(obj, groups, split_mode):
    """Removes the converted tags and the materials restricted to converted selections."""
    for group in groups:
        group.tag.Remove()

    if split_mode != SPLIT_BY_MATERIALS:
        converted_names = [group.name for group in groups]
        for tag in get_tags(obj, c4d.Ttexture):
            if tag[c4d.TEXTURETAG_RESTRICTION] in converted_names:
                tag.Remove()


def center_axis(obj):
    """Moves the axis of an object to the center of its bounding box."""
    obj.Message(c4d.MSG_UPDATE)
    center = obj.GetMp()
    obj.SetAllPoints([p - center for p in obj.GetAllPoints()])
    obj.Message(c4d.MSG_UPDATE)
    obj.SetMl(obj.GetMl() * utils.MatrixMove(center))


def get_transform_tracks(obj):
    """Returns the position, rotation and scale animation tracks."""
    return [track for track in obj.GetCTracks() if track.GetDescriptionID()[0].id in TRANSFORM_PARAMETERS]


def insert_pieces(doc, obj, pieces, options):
    """Inserts the generated objects next to or under the source object."""
    # Points of the pieces are in the source object space
    if options.as_children:
        parent, pred, matrix = obj, None, c4d.Matrix()
    else:
        parent, pred, matrix = obj.GetUp(), obj, obj.GetMl()

    if options.group_under_null:
        null = c4d.BaseObject(c4d.Onull)
        null.SetName(obj.GetName())
        null.SetMl(matrix)
        if not options.as_children:
            # The null replaces the source object transformation
            for track in get_transform_tracks(obj):
                null.InsertTrackSorted(track.GetClone())
        doc.InsertObject(null, parent=parent, pred=pred)
        doc.AddUndo(c4d.UNDOTYPE_NEW, null)
        parent, pred, matrix = null, None, c4d.Matrix()

    # Pieces keep the source object animation only when they keep its transformation
    keep_animation = not (options.as_children or options.group_under_null or options.center_axis)

    for piece in pieces:
        if not keep_animation:
            for track in get_transform_tracks(piece):
                track.Remove()
        piece.SetMl(matrix)
        if options.center_axis:
            center_axis(piece)
        doc.InsertObject(piece, parent=parent, pred=pred)
        doc.AddUndo(c4d.UNDOTYPE_NEW, piece)
        pred = piece


def remove_keeping_children(doc, obj):
    """Removes an object, its children taking its place in the hierarchy."""
    pred = obj
    for child in obj.GetChildren():
        mg = child.GetMg()
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, child)
        child.Remove()
        doc.InsertObject(child, parent=obj.GetUp(), pred=pred)
        child.SetMg(mg)
        pred = child

    doc.AddUndo(c4d.UNDOTYPE_DELETEOBJ, obj)
    obj.Remove()


def convert_object(doc, obj, groups, options):
    """Converts the groups of an object into separate objects. Returns the generated objects."""
    # All splits are done on a single clone without children
    work_obj = obj.GetClone(flags=c4d.COPYFLAGS_NO_HIERARCHY | c4d.COPYFLAGS_NO_BITS)
    if options.split_mode != SPLIT_BY_MATERIALS:
        # Removed from the pieces anyway, avoids remapping them on each split
        for tag in get_tags(work_obj, c4d.Tpolygonselection):
            tag.Remove()

    selection_tags = [tag for tag in obj.GetTags() if tag.GetType() in SELECTION_TAG_TYPES
                      and tag.GetBaseSelect().GetCount() > 0]

    converted_polygons = c4d.BaseSelect()
    pieces = []
    for group in groups:
        if group.polygons.GetCount() == 0:
            # Every polygon was taken by another group
            continue

        set_polygon_selection(work_obj, group.polygons)
        result = call_modeling_command(c4d.MCOMMAND_SPLIT, work_obj, doc)
        if not result:
            raise RuntimeError(f"Unable to split '{group.name}'")

        piece = result[0]
        piece.SetName(group.name)
        if options.split_mode == SPLIT_BY_MATERIALS:
            clean_material_piece(piece, group.tag_index)
        else:
            clean_selection_piece(piece, group.name)
        remove_empty_selection_tags(piece)

        converted_polygons.Merge(group.polygons)
        pieces.append(piece)

    if pieces:
        # Delete all converted polygons from the source object at once
        set_polygon_selection(obj, converted_polygons)
        if not call_modeling_command(c4d.MCOMMAND_DELETE, obj, doc):
            raise RuntimeError(f"Unable to delete polygons from '{obj.GetName()}'")
        obj.GetPolygonS().DeselectAll()

    clean_source(obj, groups, options.split_mode)
    # Only the tags emptied by the conversion
    remove_empty_selection_tags(obj, [tag for tag in selection_tags if tag.IsAlive() and tag.GetObject()])

    insert_pieces(doc, obj, pieces, options)

    # Children would be removed with their parent
    if pieces and not options.as_children:
        if options.delete_source or (options.delete_empty_source and obj.GetPolygonCount() == 0):
            remove_keeping_children(doc, obj)

    return pieces


def convert_objects(doc, objects, options):
    """Converts several objects in a single undo step. Returns True if any object was converted."""
    try:
        jobs = [(obj, build_groups(obj, options.split_mode)) for obj in objects]
    except Exception as e:
        print(f"Selections To Objects - error while reading the selections: {e}")
        return False

    jobs = [(obj, groups) for obj, groups in jobs if groups]
    if not jobs:
        return False

    doc.StartUndo()
    try:
        for obj, _ in jobs:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)

        for obj, groups in jobs:
            convert_object(doc, obj, groups, options)

    except Exception as e:
        print(f"Selections To Objects - error during execution: {e}")
        doc.EndUndo()
        doc.DoUndo()
        c4d.EventAdd()
        return False

    doc.EndUndo()
    c4d.EventAdd()
    return True
