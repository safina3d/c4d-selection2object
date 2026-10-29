# -*- coding: utf-8 -*-

"""
  Tests for Selections To Objects. Must be run with c4dpy:
  <Cinema 4D directory>/c4dpy tests/test_selection2object.py
"""

import os
import sys
import unittest
import importlib.util
from importlib.machinery import SourceFileLoader

import c4d
from c4d import utils

PLUGIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'SelectionToObject')
sys.path.insert(0, PLUGIN_DIR)

from selections_to_objects import PLUGIN_ID, split, command  # noqa: E402
from selections_to_objects.options import Options, SPLIT_BY_MATERIALS, load_options, save_options  # noqa: E402


def load_plugin():
    path = os.path.join(PLUGIN_DIR, 'selection2object.pyp')
    loader = SourceFileLoader('selection2object', path)
    spec = importlib.util.spec_from_loader('selection2object', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


CUBE_POINTS = [c4d.Vector(x, y, z) for x in (-100, 100) for y in (-100, 100) for z in (-100, 100)]
CUBE_POLYGONS = [
    c4d.CPolygon(0, 1, 3, 2),  # -X
    c4d.CPolygon(4, 6, 7, 5),  # +X
    c4d.CPolygon(0, 4, 5, 1),  # -Y
    c4d.CPolygon(2, 3, 7, 6),  # +Y
    c4d.CPolygon(0, 2, 6, 4),  # -Z
    c4d.CPolygon(1, 5, 7, 3),  # +Z
]
# Quad not connected to the cube
ISLAND_POINTS = [c4d.Vector(500, 0, 0), c4d.Vector(600, 0, 0), c4d.Vector(600, 100, 0), c4d.Vector(500, 100, 0)]
ISLAND_POLYGON = c4d.CPolygon(8, 9, 10, 11)


def make_object(doc, name='Source', island=False):
    """Returns a cube polygon object (6 polygons, + 1 island polygon) inserted in the document."""
    points = CUBE_POINTS + (ISLAND_POINTS if island else [])
    polygons = CUBE_POLYGONS + ([ISLAND_POLYGON] if island else [])
    obj = c4d.PolygonObject(len(points), len(polygons))
    obj.SetAllPoints(points)
    for i, polygon in enumerate(polygons):
        obj.SetPolygon(i, polygon)
    obj.Message(c4d.MSG_UPDATE)
    obj.SetName(name)
    doc.InsertObject(obj)
    return obj


def add_selection(obj, name, indices, tag_type=c4d.Tpolygonselection):
    tag = obj.MakeTag(tag_type, obj.GetLastTag())
    tag.SetName(name)
    bs = tag.GetBaseSelect()
    for i in indices:
        bs.Select(i)
    return tag


def add_material(doc, obj, name, restriction=''):
    mat = c4d.BaseMaterial(c4d.Mmaterial)
    mat.SetName(name)
    doc.InsertMaterial(mat)
    tag = obj.MakeTag(c4d.Ttexture, obj.GetLastTag())
    tag[c4d.TEXTURETAG_MATERIAL] = mat
    tag[c4d.TEXTURETAG_RESTRICTION] = restriction
    return tag


def polygon_centers(obj, indices=None):
    """World space polygon centers, rounded, as a set."""
    mg = obj.GetMg()
    points = obj.GetAllPoints()
    polygons = obj.GetAllPolygons()
    indices = range(len(polygons)) if indices is None else indices
    centers = set()
    for i in indices:
        p = polygons[i]
        ids = [p.a, p.b, p.c] if p.IsTriangle() else [p.a, p.b, p.c, p.d]
        c = sum((points[k] for k in ids), c4d.Vector()) / len(ids)
        w = mg * c
        centers.add((round(w.x, 3), round(w.y, 3), round(w.z, 3)))
    return centers


def unused_points(obj):
    used = set()
    for p in obj.GetAllPolygons():
        used.update([p.a, p.b, p.c, p.d])
    return set(range(obj.GetPointCount())) - used


def tags_of_type(obj, tag_type):
    return [tag for tag in obj.GetTags() if tag.GetType() == tag_type]


def tag_names(obj, tag_type):
    return [tag.GetName() for tag in tags_of_type(obj, tag_type)]


def materials_of(obj):
    """{material name: restriction} of the texture tags of an object."""
    return {tag[c4d.TEXTURETAG_MATERIAL].GetName(): tag[c4d.TEXTURETAG_RESTRICTION]
            for tag in tags_of_type(obj, c4d.Ttexture)}


def root_objects(doc):
    objects = []
    obj = doc.GetFirstObject()
    while obj:
        objects.append(obj)
        obj = obj.GetNext()
    return objects


def names(objects):
    return [o.GetName() for o in objects]


class BaseTest(unittest.TestCase):

    def setUp(self):
        self.doc = c4d.documents.BaseDocument()
        c4d.documents.InsertBaseDocument(self.doc)
        c4d.documents.SetActiveDocument(self.doc)
        self.obj = make_object(self.doc)
        self.doc.SetActiveObject(self.obj)

    def tearDown(self):
        c4d.documents.KillDocument(self.doc)

    def convert(self, objects=None, **options):
        objects = [self.obj] if objects is None else objects
        return split.convert_objects(self.doc, objects, Options(**options))


class SplitBySelectionsTest(BaseTest):

    def test_split_objects(self):
        expected_a = polygon_centers(self.obj, [0, 1])
        expected_b = polygon_centers(self.obj, [2, 3])
        expected_rest = polygon_centers(self.obj, [4, 5])
        add_selection(self.obj, 'A', [0, 1])
        add_selection(self.obj, 'B', [2, 3])

        self.assertTrue(self.convert())

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Source', 'A', 'B'])
        source, a, b = objects
        self.assertEqual(polygon_centers(a), expected_a)
        self.assertEqual(polygon_centers(b), expected_b)
        self.assertEqual(polygon_centers(source), expected_rest)
        for obj in objects:
            self.assertEqual(tags_of_type(obj, c4d.Tpolygonselection), [])

    def test_overlapping_selections_go_to_right_most_tag(self):
        expected_a = polygon_centers(self.obj, [0])
        expected_b = polygon_centers(self.obj, [1, 2])
        add_selection(self.obj, 'A', [0, 1])
        add_selection(self.obj, 'B', [1, 2])

        self.assertTrue(self.convert())

        source, a, b = root_objects(self.doc)
        self.assertEqual(polygon_centers(a), expected_a)
        self.assertEqual(polygon_centers(b), expected_b)
        self.assertEqual(source.GetPolygonCount(), 3)

    def test_fully_overlapped_selection_creates_no_object(self):
        add_selection(self.obj, 'A', [0])
        add_selection(self.obj, 'B', [0, 1])

        self.assertTrue(self.convert())

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Source', 'B'])
        self.assertEqual(tags_of_type(objects[0], c4d.Tpolygonselection), [])

    def test_materials(self):
        add_selection(self.obj, 'A', [0, 1])
        add_selection(self.obj, 'B', [2, 3])
        add_material(self.doc, self.obj, 'Base')
        add_material(self.doc, self.obj, 'MatA', 'A')
        add_material(self.doc, self.obj, 'MatB', 'B')
        add_material(self.doc, self.obj, 'MatOther', 'Other')

        self.assertTrue(self.convert())

        source, a, b = root_objects(self.doc)
        self.assertEqual(materials_of(a), {'Base': '', 'MatA': ''})
        self.assertEqual(materials_of(b), {'Base': '', 'MatB': ''})
        self.assertEqual(materials_of(source), {'Base': '', 'MatOther': 'Other'})

    def test_empty_selection_is_kept(self):
        add_selection(self.obj, 'Empty', [])
        add_selection(self.obj, 'A', [0])

        self.assertTrue(self.convert())

        source, a = root_objects(self.doc)
        self.assertEqual(tag_names(source, c4d.Tpolygonselection), ['Empty'])

    def test_no_selection_tag(self):
        self.assertFalse(self.convert())
        self.assertEqual(len(root_objects(self.doc)), 1)


class SplitByMaterialsTest(BaseTest):

    def test_split_by_materials(self):
        expected_base = polygon_centers(self.obj, [4, 5])
        expected_a = polygon_centers(self.obj, [0, 1])
        expected_b = polygon_centers(self.obj, [2, 3])
        add_selection(self.obj, 'A', [0, 1])
        add_selection(self.obj, 'B', [2, 3])
        add_material(self.doc, self.obj, 'Base')
        add_material(self.doc, self.obj, 'MatA', 'A')
        add_material(self.doc, self.obj, 'MatB', 'B')

        self.assertTrue(self.convert(split_mode=SPLIT_BY_MATERIALS))

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Source', 'Base', 'MatA', 'MatB'])
        source, base, a, b = objects
        self.assertEqual(polygon_centers(base), expected_base)
        self.assertEqual(polygon_centers(a), expected_a)
        self.assertEqual(polygon_centers(b), expected_b)
        self.assertEqual(materials_of(base), {'Base': ''})
        self.assertEqual(materials_of(a), {'MatA': ''})
        self.assertEqual(materials_of(b), {'MatB': ''})
        self.assertEqual(source.GetPolygonCount(), 0)
        self.assertEqual(source.GetTags() and materials_of(source), {})
        self.assertEqual(tags_of_type(source, c4d.Tpolygonselection), [])

    def test_polygons_without_material_stay_on_source(self):
        expected_rest = polygon_centers(self.obj, [2, 3, 4, 5])
        add_selection(self.obj, 'A', [0, 1])
        add_selection(self.obj, 'Other', [4])
        add_material(self.doc, self.obj, 'MatA', 'A')
        add_material(self.doc, self.obj, 'MatMissing', 'Missing')

        self.assertTrue(self.convert(split_mode=SPLIT_BY_MATERIALS))

        source, a = root_objects(self.doc)
        self.assertEqual(polygon_centers(source), expected_rest)
        self.assertEqual(materials_of(source), {'MatMissing': 'Missing'})
        self.assertEqual(tag_names(source, c4d.Tpolygonselection), ['Other'])

    def test_last_material_wins(self):
        add_selection(self.obj, 'A', [0, 1])
        add_material(self.doc, self.obj, 'MatA', 'A')
        add_material(self.doc, self.obj, 'Base')

        self.assertTrue(self.convert(split_mode=SPLIT_BY_MATERIALS))

        self.assertEqual(names(root_objects(self.doc)), ['Source', 'Base'])

    def test_no_material(self):
        add_selection(self.obj, 'A', [0, 1])
        self.assertFalse(self.convert(split_mode=SPLIT_BY_MATERIALS))


class OptionsTest(BaseTest):

    def setUp(self):
        super().setUp()
        add_selection(self.obj, 'A', [0, 1])
        add_selection(self.obj, 'B', [2, 3])

    def transform_source(self):
        self.obj.SetMg(utils.MatrixMove(c4d.Vector(100, 50, -30)) * utils.HPBToMatrix(c4d.Vector(0.5, 0.3, 0.1)))
        return polygon_centers(self.obj, [0, 1]), polygon_centers(self.obj, [2, 3])

    def test_children_keep_world_position(self):
        expected_a, expected_b = self.transform_source()

        self.assertTrue(self.convert(as_children=True))

        objects = root_objects(self.doc)
        self.assertEqual(len(objects), 1)
        children = objects[0].GetChildren()
        self.assertEqual(names(children), ['A', 'B'])
        self.assertEqual(polygon_centers(children[0]), expected_a)
        self.assertEqual(polygon_centers(children[1]), expected_b)

    def test_siblings_keep_world_position(self):
        parent = c4d.BaseObject(c4d.Onull)
        parent.SetMg(utils.MatrixMove(c4d.Vector(-20, 10, 5)))
        self.doc.InsertObject(parent)
        self.obj.Remove()
        self.obj.InsertUnder(parent)
        self.obj.SetMl(utils.MatrixMove(c4d.Vector(7, 0, 3)) * utils.HPBToMatrix(c4d.Vector(1, 0, 0)))
        expected_a = polygon_centers(self.obj, [0, 1])

        self.assertTrue(self.convert())

        self.assertEqual(names(parent.GetChildren()), ['Source', 'A', 'B'])
        self.assertEqual(polygon_centers(parent.GetChildren()[1]), expected_a)

    def test_center_axis(self):
        add_selection(self.obj, 'C', [4])
        expected_a, expected_b = self.transform_source()
        expected_c = polygon_centers(self.obj, [4])
        # Center of the -Z face in the source object space
        expected_c_axis = self.obj.GetMg() * c4d.Vector(0, 0, -100)

        self.assertTrue(self.convert(center_axis=True))

        source, a, b, c = root_objects(self.doc)
        for piece, expected in ((a, expected_a), (b, expected_b), (c, expected_c)):
            self.assertEqual(polygon_centers(piece), expected)
            points = piece.GetAllPoints()
            center = (c4d.Vector(min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)) +
                      c4d.Vector(max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))) * 0.5
            self.assertAlmostEqual(center.GetLength(), 0, places=3)
        self.assertAlmostEqual((c.GetMg().off - expected_c_axis).GetLength(), 0, places=3)

    def test_group_under_null(self):
        expected_a, expected_b = self.transform_source()

        self.assertTrue(self.convert(group_under_null=True))

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Source', 'Source'])
        null = objects[1]
        self.assertEqual(null.GetType(), c4d.Onull)
        self.assertEqual(names(null.GetChildren()), ['A', 'B'])
        self.assertEqual(polygon_centers(null.GetChildren()[0]), expected_a)
        self.assertEqual(polygon_centers(null.GetChildren()[1]), expected_b)

    def test_group_under_null_as_children(self):
        expected_a, _ = self.transform_source()

        self.assertTrue(self.convert(group_under_null=True, as_children=True))

        null = self.obj.GetDown()
        self.assertEqual(null.GetType(), c4d.Onull)
        self.assertEqual(names(null.GetChildren()), ['A', 'B'])
        self.assertEqual(polygon_centers(null.GetChildren()[0]), expected_a)

    def test_delete_source_and_undo(self):
        self.assertTrue(self.convert(delete_source=True))
        self.assertEqual(names(root_objects(self.doc)), ['A', 'B'])

        self.doc.DoUndo()

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Source'])
        self.assertEqual(objects[0].GetPolygonCount(), 6)
        self.assertEqual(len(tags_of_type(objects[0], c4d.Tpolygonselection)), 2)

    def test_delete_source_keeps_its_children(self):
        self.obj.SetMg(utils.MatrixMove(c4d.Vector(100, 0, 0)))
        child = c4d.BaseObject(c4d.Onull)
        child.SetName('Child')
        child.InsertUnder(self.obj)
        child.SetMl(utils.MatrixMove(c4d.Vector(0, 50, 0)))
        expected_mg = child.GetMg()

        self.assertTrue(self.convert(delete_source=True))

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Child', 'A', 'B'])
        self.assertEqual(objects[0].GetMg(), expected_mg)

        self.doc.DoUndo()

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Source'])
        self.assertEqual(names(objects[0].GetChildren()), ['Child'])

    def test_delete_source_is_ignored_with_children(self):
        self.assertTrue(self.convert(delete_source=True, as_children=True))

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Source'])
        self.assertEqual(names(objects[0].GetChildren()), ['A', 'B'])

    def test_delete_empty_source(self):
        add_selection(self.obj, 'C', [4, 5])

        self.assertTrue(self.convert(delete_empty_source=True))

        self.assertEqual(names(root_objects(self.doc)), ['A', 'B', 'C'])

    def test_delete_empty_source_keeps_non_empty_source(self):
        self.assertTrue(self.convert(delete_empty_source=True))

        self.assertEqual(names(root_objects(self.doc)), ['Source', 'A', 'B'])

    def test_undo_restores_everything(self):
        add_material(self.doc, self.obj, 'MatA', 'A')

        self.assertTrue(self.convert(center_axis=True, group_under_null=True))
        self.doc.DoUndo()

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Source'])
        self.assertEqual(objects[0].GetPolygonCount(), 6)
        self.assertEqual(tag_names(objects[0], c4d.Tpolygonselection), ['A', 'B'])
        self.assertEqual(materials_of(objects[0]), {'MatA': 'A'})


class SavedOptionsTest(unittest.TestCase):

    def setUp(self):
        self.saved = c4d.plugins.GetWorldPluginData(PLUGIN_ID)

    def tearDown(self):
        c4d.plugins.SetWorldPluginData(PLUGIN_ID, self.saved if self.saved is not None else c4d.BaseContainer(), False)

    def test_options_are_saved(self):
        expected = Options(split_mode=SPLIT_BY_MATERIALS, as_children=True, center_axis=True, group_under_null=True)
        save_options(expected)
        self.assertEqual(load_options(), expected)

        expected = Options()
        save_options(expected)
        self.assertEqual(load_options(), expected)


class MultipleObjectsTest(BaseTest):

    def test_convert_several_objects_in_one_undo(self):
        other = make_object(self.doc, 'Other')
        add_selection(self.obj, 'A', [0])
        add_selection(other, 'B', [1])
        self.doc.SetActiveObject(other, c4d.SELECTION_ADD)

        objects = split.get_polygon_objects(self.doc)
        self.assertEqual(len(objects), 2)
        self.assertTrue(self.convert(objects))
        self.assertEqual(names(root_objects(self.doc)), ['Other', 'B', 'Source', 'A'])

        self.doc.DoUndo()

        self.assertEqual(names(root_objects(self.doc)), ['Other', 'Source'])
        self.assertEqual([o.GetPolygonCount() for o in root_objects(self.doc)], [6, 6])

    def test_selected_parent_and_child_with_delete_source(self):
        child = make_object(self.doc, 'Child')
        child.Remove()
        child.InsertUnder(self.obj)
        add_selection(self.obj, 'A', [0])
        add_selection(child, 'B', [1])

        self.assertTrue(self.convert([self.obj, child], delete_source=True))

        self.assertEqual(names(root_objects(self.doc)), ['B', 'A'])

    def test_objects_without_tags_are_ignored(self):
        other = make_object(self.doc, 'Other')
        add_selection(self.obj, 'A', [0])

        self.assertTrue(self.convert([self.obj, other]))

        self.assertEqual(names(root_objects(self.doc)), ['Other', 'Source', 'A'])


class TagsTest(BaseTest):

    def test_no_unused_points(self):
        c4d.documents.KillDocument(self.doc)
        self.setUp_island()
        add_selection(self.obj, 'Island', [6])
        add_selection(self.obj, 'A', [0])

        self.assertTrue(self.convert())

        source, island, a = root_objects(self.doc)
        self.assertEqual(source.GetPointCount(), 8)
        self.assertEqual(island.GetPointCount(), 4)
        self.assertEqual(a.GetPointCount(), 4)
        for obj in (source, island, a):
            self.assertEqual(unused_points(obj), set())

    def setUp_island(self):
        self.doc = c4d.documents.BaseDocument()
        c4d.documents.InsertBaseDocument(self.doc)
        self.obj = make_object(self.doc, island=True)

    def test_other_selection_tags(self):
        c4d.documents.KillDocument(self.doc)
        self.setUp_island()
        add_selection(self.obj, 'Island', [6])
        add_selection(self.obj, 'IslandPoints', [8, 9], c4d.Tpointselection)
        add_selection(self.obj, 'CubePoints', [0, 1], c4d.Tpointselection)
        add_selection(self.obj, 'EmptyPoints', [], c4d.Tpointselection)

        self.assertTrue(self.convert())

        source, island = root_objects(self.doc)
        self.assertEqual(tag_names(island, c4d.Tpointselection), ['IslandPoints'])
        self.assertEqual(tags_of_type(island, c4d.Tpointselection)[0].GetBaseSelect().GetCount(), 2)
        # Emptied by the conversion: removed. Empty before: kept.
        self.assertEqual(tag_names(source, c4d.Tpointselection), ['CubePoints', 'EmptyPoints'])

    def test_uvw_follow_polygons(self):
        uvw = c4d.UVWTag(self.obj.GetPolygonCount())
        self.obj.InsertTag(uvw)
        add_selection(self.obj, 'A', [0, 1])

        self.assertTrue(self.convert())

        source, a = root_objects(self.doc)
        self.assertEqual(tags_of_type(a, c4d.Tuvw)[0].GetDataCount(), 2)
        self.assertEqual(tags_of_type(source, c4d.Tuvw)[0].GetDataCount(), 4)


def animate_position_x(doc, obj, values):
    """Adds a position X track with a key per (frame, value)."""
    desc_id = c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION, c4d.DTYPE_VECTOR, 0),
                         c4d.DescLevel(c4d.VECTOR_X, c4d.DTYPE_REAL, 0))
    track = c4d.CTrack(obj, desc_id)
    obj.InsertTrackSorted(track)
    curve = track.GetCurve()
    for frame, value in values:
        key = curve.AddKey(c4d.BaseTime(frame, doc.GetFps()))['key']
        key.SetValue(curve, value)


class AnimationTest(BaseTest):

    def setUp(self):
        super().setUp()
        add_selection(self.obj, 'A', [0])
        animate_position_x(self.doc, self.obj, [(0, 0.0), (10, 500.0)])

    def world_x_at_frame_10(self, obj):
        self.doc.SetTime(c4d.BaseTime(10, self.doc.GetFps()))
        self.doc.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
        return round(obj.GetMg().off.x, 3)

    def test_siblings_keep_animation(self):
        self.assertTrue(self.convert())

        source, a = root_objects(self.doc)
        self.assertEqual(self.world_x_at_frame_10(a), 500)

    def test_children_follow_animated_parent(self):
        self.assertTrue(self.convert(as_children=True))

        self.assertEqual(self.world_x_at_frame_10(self.obj.GetDown()), 500)

    def test_null_carries_animation(self):
        self.assertTrue(self.convert(group_under_null=True, delete_source=True))

        null, = root_objects(self.doc)
        self.assertEqual(self.world_x_at_frame_10(null.GetDown()), 500)


class EdgeCasesTest(BaseTest):

    def test_error_restores_document(self):
        add_selection(self.obj, 'A', [0])
        add_selection(self.obj, 'B', [1])
        self.doc.InsertObject(c4d.BaseObject(c4d.Onull))
        original_command = split.call_modeling_command
        calls = []

        def failing_command(command, obj, doc):
            calls.append(command)
            if len(calls) == 2:
                return False
            return original_command(command, obj, doc)

        split.call_modeling_command = failing_command
        try:
            self.assertFalse(self.convert(delete_source=True))
        finally:
            split.call_modeling_command = original_command

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Null', 'Source'])
        self.assertEqual(objects[1].GetPolygonCount(), 6)
        self.assertEqual(tag_names(objects[1], c4d.Tpolygonselection), ['A', 'B'])

    def test_selection_out_of_range_is_ignored(self):
        add_selection(self.obj, 'A', [0, 1, 50])

        self.assertTrue(self.convert())

        source, a = root_objects(self.doc)
        self.assertEqual(a.GetPolygonCount(), 2)
        self.assertEqual(source.GetPolygonCount(), 4)

    def test_ngons(self):
        plane = c4d.BaseObject(c4d.Oplane)
        plane[c4d.PRIM_PLANE_SUBW] = 4
        plane[c4d.PRIM_PLANE_SUBH] = 4
        obj = utils.SendModelingCommand(c4d.MCOMMAND_CURRENTSTATETOOBJECT, [plane], doc=self.doc)[0]
        self.doc.InsertObject(obj)
        polygon_selection = obj.GetPolygonS()
        for i in (0, 1, 4, 5):
            polygon_selection.Select(i)
        utils.SendModelingCommand(c4d.MCOMMAND_MELT, [obj], c4d.MODELINGCOMMANDMODE_POLYGONSELECTION,
                                  c4d.BaseContainer(), self.doc)
        self.assertEqual(obj.GetNgonCount(), 1)
        # Polygons making the ngon
        ngon_selection = c4d.BaseSelect()
        _, polygon_to_ngon = obj.GetPolygonTranslationMap()
        for i, ngon in enumerate(polygon_to_ngon):
            if ngon == 0:
                ngon_selection.Select(i)
        tag = obj.MakeTag(c4d.Tpolygonselection)
        tag.SetName('Ngon')
        ngon_selection.CopyTo(tag.GetBaseSelect())
        expected = polygon_centers(obj, [i for i in range(obj.GetPolygonCount()) if ngon_selection.IsSelected(i)])

        self.assertTrue(split.convert_objects(self.doc, [obj], Options()))

        piece = obj.GetNext()
        self.assertEqual(piece.GetName(), 'Ngon')
        self.assertEqual(piece.GetNgonCount(), 1)
        self.assertEqual(polygon_centers(piece), expected)
        self.assertEqual(obj.GetNgonCount(), 0)

    def test_children_with_center_axis(self):
        add_selection(self.obj, 'C', [4])
        self.obj.SetMg(utils.MatrixMove(c4d.Vector(100, 50, -30)) * utils.HPBToMatrix(c4d.Vector(0.5, 0.3, 0.1)))
        expected = polygon_centers(self.obj, [4])

        self.assertTrue(self.convert(as_children=True, center_axis=True))

        piece = self.obj.GetDown()
        self.assertEqual(polygon_centers(piece), expected)
        self.assertAlmostEqual((piece.GetMl().off - c4d.Vector(0, 0, -100)).GetLength(), 0, places=3)

    def test_undo_split_by_materials(self):
        add_selection(self.obj, 'A', [0, 1])
        add_material(self.doc, self.obj, 'Base')
        add_material(self.doc, self.obj, 'MatA', 'A')

        self.assertTrue(self.convert(split_mode=SPLIT_BY_MATERIALS, delete_empty_source=True))
        self.assertEqual(names(root_objects(self.doc)), ['Base', 'MatA'])

        self.doc.DoUndo()

        objects = root_objects(self.doc)
        self.assertEqual(names(objects), ['Source'])
        self.assertEqual(objects[0].GetPolygonCount(), 6)
        self.assertEqual(materials_of(objects[0]), {'Base': '', 'MatA': 'A'})
        self.assertEqual(tag_names(objects[0], c4d.Tpolygonselection), ['A'])


class CommandTest(BaseTest):

    def setUp(self):
        super().setUp()
        self.plugin = load_plugin()
        self.pressed = {c4d.QCTRL: False, c4d.QSHIFT: False}
        self.original_is_button_pressed = command.is_button_pressed
        command.is_button_pressed = lambda button: self.pressed[button]

    def tearDown(self):
        command.is_button_pressed = self.original_is_button_pressed
        super().tearDown()

    def test_state(self):
        cmd = self.plugin.SelectionsToObjects()
        self.assertEqual(cmd.GetState(self.doc), c4d.CMD_ENABLED)
        null = c4d.BaseObject(c4d.Onull)
        self.doc.InsertObject(null)
        self.doc.SetActiveObject(null)
        self.assertEqual(cmd.GetState(self.doc), 0)
        self.assertFalse(cmd.Execute(self.doc))

    def test_shift_inserts_as_children(self):
        add_selection(self.obj, 'A', [0])
        self.pressed[c4d.QSHIFT] = True

        self.assertTrue(self.plugin.SelectionsToObjects().Execute(self.doc))

        self.assertEqual(names(self.obj.GetChildren()), ['A'])

    def test_ctrl_deletes_source(self):
        add_selection(self.obj, 'A', [0])
        self.pressed[c4d.QCTRL] = True

        self.assertTrue(self.plugin.SelectionsToObjects().Execute(self.doc))

        self.assertEqual(names(root_objects(self.doc)), ['A'])


if __name__ == '__main__':
    result = unittest.main(exit=False, verbosity=2).result
    sys.stdout.flush()
    sys.stderr.flush()
    # c4dpy ignores sys.exit() and always returns 1
    os._exit(0 if result.wasSuccessful() else 1)
