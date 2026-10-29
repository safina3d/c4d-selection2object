# -*- coding: utf-8 -*-

"""Computes which polygons go to which generated object."""

from dataclasses import dataclass

import c4d

from .options import SPLIT_BY_MATERIALS


@dataclass
class Group:
    name: str
    polygons: c4d.BaseSelect
    # Converted tag: polygon selection tag or texture tag
    tag: c4d.BaseTag
    # Index of the tag among the tags of the same type
    tag_index: int


def get_tags(obj, tag_type):
    return [tag for tag in obj.GetTags() if tag.GetType() == tag_type]


def resolve_regions(regions, count):
    """Returns one selection per region, a polygon belonging to the last region containing it.
    A region set to None contains every polygon."""
    all_polygons = c4d.BaseSelect()
    if count > 0:
        all_polygons.SelectAll(count - 1)

    taken = c4d.BaseSelect()
    selections = []
    for region in reversed(regions):
        selection = all_polygons.GetClone()
        if region is not None:
            # Also drops indices out of range
            selection.Cross(region)
        selection.DeselectFrom(taken)
        taken.Merge(selection)
        selections.append(selection)

    selections.reverse()
    return selections


def groups_by_selections(obj):
    """One group per non empty polygon selection tag."""
    tags = [tag for tag in get_tags(obj, c4d.Tpolygonselection) if tag.GetBaseSelect().GetCount() > 0]
    selections = resolve_regions([tag.GetBaseSelect() for tag in tags], obj.GetPolygonCount())
    return [Group(tag.GetName(), selection, tag, index)
            for index, (tag, selection) in enumerate(zip(tags, selections))]


def groups_by_materials(obj):
    """One group per texture tag, using the polygons the material is visible on."""
    selections = {}
    for tag in get_tags(obj, c4d.Tpolygonselection):
        selections.setdefault(tag.GetName(), tag.GetBaseSelect())

    tags, indices, regions = [], [], []
    for index, tag in enumerate(get_tags(obj, c4d.Ttexture)):
        restriction = tag[c4d.TEXTURETAG_RESTRICTION]
        if restriction and restriction not in selections:
            # Restricted to a selection that does not exist: applied nowhere
            continue
        tags.append(tag)
        indices.append(index)
        regions.append(selections[restriction] if restriction else None)

    polygons = resolve_regions(regions, obj.GetPolygonCount())
    groups = []
    for tag, index, selection in zip(tags, indices, polygons):
        material = tag[c4d.TEXTURETAG_MATERIAL]
        name = material.GetName() if material else tag.GetName()
        groups.append(Group(name, selection, tag, index))
    return groups


def build_groups(obj, split_mode):
    if split_mode == SPLIT_BY_MATERIALS:
        return groups_by_materials(obj)
    return groups_by_selections(obj)
