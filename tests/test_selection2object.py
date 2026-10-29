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

PLUGIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'SelectionToObject', 'selection2object.pyp')


def load_plugin():
    loader = SourceFileLoader('selection2object', PLUGIN_PATH)
    spec = importlib.util.spec_from_loader('selection2object', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


s2o = load_plugin()


def make_cube(doc):
    """Returns a cube polygon object (6 polygons) inserted in the document."""
    points = [c4d.Vector(x, y, z) for x in (-100, 100) for y in (-100, 100) for z in (-100, 100)]
    polygons = [
        c4d.CPolygon(0, 1, 3, 2),  # -X
        c4d.CPolygon(4, 6, 7, 5),  # +X
        c4d.CPolygon(0, 4, 5, 1),  # -Y
        c4d.CPolygon(2, 3, 7, 6),  # +Y
        c4d.CPolygon(0, 2, 6, 4),  # -Z
        c4d.CPolygon(1, 5, 7, 3),  # +Z
    ]
    obj = c4d.PolygonObject(len(points), len(polygons))
    obj.SetAllPoints(points)
    for i, polygon in enumerate(polygons):
        obj.SetPolygon(i, polygon)
    obj.Message(c4d.MSG_UPDATE)
    obj.SetName('Source')
    doc.InsertObject(obj)
    return obj


def add_selection(obj, name, indices):
    tag = obj.MakeTag(c4d.Tpolygonselection, obj.GetLastTag())
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


def tags_of_type(obj, tag_type):
    return [tag for tag in obj.GetTags() if tag.GetType() == tag_type]


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


class SelectionsToObjectsTest(unittest.TestCase):

    def setUp(self):
        self.doc = c4d.documents.BaseDocument()
        c4d.documents.InsertBaseDocument(self.doc)
        c4d.documents.SetActiveDocument(self.doc)
        self.obj = make_cube(self.doc)
        self.doc.SetActiveObject(self.obj)
        self.set_keys()

    def tearDown(self):
        c4d.documents.KillDocument(self.doc)

    def set_keys(self, ctrl=False, shift=False):
        pressed = {c4d.QCTRL: ctrl, c4d.QSHIFT: shift}
        s2o.is_button_pressed = lambda button: pressed[button]

    def run_command(self):
        return s2o.SelectionsToObjects().Execute(self.doc)

    def test_split_objects(self):
        expected_a = polygon_centers(self.obj, [0, 1])
        expected_b = polygon_centers(self.obj, [2, 3])
        expected_rest = polygon_centers(self.obj, [4, 5])
        add_selection(self.obj, 'A', [0, 1])
        add_selection(self.obj, 'B', [2, 3])

        self.assertTrue(self.run_command())

        objects = root_objects(self.doc)
        self.assertEqual([o.GetName() for o in objects], ['Source', 'A', 'B'])
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

        self.assertTrue(self.run_command())

        source, a, b = root_objects(self.doc)
        self.assertEqual(polygon_centers(a), expected_a)
        self.assertEqual(polygon_centers(b), expected_b)
        self.assertEqual(source.GetPolygonCount(), 3)

    def test_fully_overlapped_selection_creates_no_object(self):
        add_selection(self.obj, 'A', [0])
        add_selection(self.obj, 'B', [0, 1])

        self.assertTrue(self.run_command())

        objects = root_objects(self.doc)
        self.assertEqual([o.GetName() for o in objects], ['Source', 'B'])
        self.assertEqual(tags_of_type(objects[0], c4d.Tpolygonselection), [])

    def test_materials(self):
        add_selection(self.obj, 'A', [0, 1])
        add_selection(self.obj, 'B', [2, 3])
        add_material(self.doc, self.obj, 'Base')
        add_material(self.doc, self.obj, 'MatA', 'A')
        add_material(self.doc, self.obj, 'MatB', 'B')
        add_material(self.doc, self.obj, 'MatOther', 'Other')

        self.assertTrue(self.run_command())

        source, a, b = root_objects(self.doc)
        self.assertEqual(materials_of(a), {'Base': '', 'MatA': ''})
        self.assertEqual(materials_of(b), {'Base': '', 'MatB': ''})
        self.assertEqual(materials_of(source), {'Base': '', 'MatOther': 'Other'})

    def test_children_keep_world_position(self):
        self.obj.SetMg(utils.MatrixMove(c4d.Vector(100, 50, -30)) * utils.HPBToMatrix(c4d.Vector(0.5, 0.3, 0.1)))
        expected_a = polygon_centers(self.obj, [0, 1])
        expected_b = polygon_centers(self.obj, [2, 3])
        add_selection(self.obj, 'A', [0, 1])
        add_selection(self.obj, 'B', [2, 3])
        self.set_keys(shift=True)

        self.assertTrue(self.run_command())

        objects = root_objects(self.doc)
        self.assertEqual(len(objects), 1)
        children = objects[0].GetChildren()
        self.assertEqual([o.GetName() for o in children], ['A', 'B'])
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
        add_selection(self.obj, 'A', [0, 1])

        self.assertTrue(self.run_command())

        self.assertEqual([o.GetName() for o in parent.GetChildren()], ['Source', 'A'])
        self.assertEqual(polygon_centers(parent.GetChildren()[1]), expected_a)

    def test_ctrl_deletes_original_and_undo_restores_it(self):
        add_selection(self.obj, 'A', [0, 1])
        add_selection(self.obj, 'B', [2, 3])
        self.set_keys(ctrl=True)

        self.assertTrue(self.run_command())
        self.assertEqual([o.GetName() for o in root_objects(self.doc)], ['A', 'B'])

        self.doc.DoUndo()

        objects = root_objects(self.doc)
        self.assertEqual([o.GetName() for o in objects], ['Source'])
        self.assertEqual(objects[0].GetPolygonCount(), 6)
        self.assertEqual(len(tags_of_type(objects[0], c4d.Tpolygonselection)), 2)

    def test_ctrl_is_ignored_with_shift(self):
        add_selection(self.obj, 'A', [0, 1])
        self.set_keys(ctrl=True, shift=True)

        self.assertTrue(self.run_command())

        objects = root_objects(self.doc)
        self.assertEqual([o.GetName() for o in objects], ['Source'])
        self.assertEqual([o.GetName() for o in objects[0].GetChildren()], ['A'])

    def test_undo_restores_everything(self):
        add_selection(self.obj, 'A', [0, 1])
        add_material(self.doc, self.obj, 'MatA', 'A')

        self.assertTrue(self.run_command())
        self.doc.DoUndo()

        objects = root_objects(self.doc)
        self.assertEqual([o.GetName() for o in objects], ['Source'])
        self.assertEqual(objects[0].GetPolygonCount(), 6)
        self.assertEqual(len(tags_of_type(objects[0], c4d.Tpolygonselection)), 1)
        self.assertEqual(materials_of(objects[0]), {'MatA': 'A'})

    def test_empty_selection_is_kept(self):
        add_selection(self.obj, 'Empty', [])
        add_selection(self.obj, 'A', [0])

        self.assertTrue(self.run_command())

        source, a = root_objects(self.doc)
        self.assertEqual([t.GetName() for t in tags_of_type(source, c4d.Tpolygonselection)], ['Empty'])

    def test_no_selection_tag(self):
        self.assertFalse(self.run_command())
        self.assertEqual(len(root_objects(self.doc)), 1)

    def test_not_a_polygon_object(self):
        null = c4d.BaseObject(c4d.Onull)
        self.doc.InsertObject(null)
        self.doc.SetActiveObject(null)
        self.assertFalse(self.run_command())


if __name__ == '__main__':
    result = unittest.main(exit=False, verbosity=2).result
    sys.stdout.flush()
    sys.stderr.flush()
    # c4dpy ignores sys.exit() and always returns 1
    os._exit(0 if result.wasSuccessful() else 1)
