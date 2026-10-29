# Selections To Objects

<img src="SelectionToObject/res/icons/selection.png" alt="Selections To Objects icon" width="96" align="right">

**A Cinema 4D plugin that turns a single mesh into clean, separate objects in one click.**

Imported a model as one big mesh? Spent time building polygon selections or assigning materials? Selections To Objects splits the object along those selections or materials, names each new object after them, keeps the right materials on each piece and leaves your scene tidy. Everything can be undone in a single step.

For more tools and tutorials, visit <https://safina3d.blogspot.com>

## Features

- **One object per polygon selection tag**, named after the tag
- **One object per material**, using the polygons where each material is visible
- **Several objects at once**, with a single undo
- **Materials follow the polygons**: whole-object materials are kept on every piece, restricted materials move to the matching piece
- **Clean result**: no leftover selection tags, no orphan points, the source object's children are never lost
- **Flexible placement**: next to the source, inside it, or grouped under a Null
- **Centered axis** on each new object, if you want it
- **Animation aware**: new objects keep following the animated source object

## Quick start

1. Select one or more polygon objects that have **polygon selection tags** (or **material tags**)
2. Run **Selections To Objects** from the Extensions menu, or from its icon if you added it to a palette
3. Done: one new object per selection, next to the source object

| Shortcut | Effect |
|---|---|
| **SHIFT** + click | Place the new objects inside the source object, as children |
| **CTRL** + click | Delete the source object after conversion |

## Options

Click on the gear icon next to the command in the menu to open the options. They are saved in the Cinema 4D preferences and used every time you run the command.

| Section | Option | Choices |
|---|---|---|
| Split | Create one object per | Polygon selection tag · Material tag |
| New objects | Place them | Next to the source object · Inside the source object, as children |
| | Put them in a Null named after the source object | on / off |
| | Move the axis of each one to the center of its polygons | on / off |
| Source object | After conversion | Keep it, with its remaining polygons · Delete it · Delete it only if no polygon is left |

The source object cannot be deleted when the new objects are placed inside it, so this choice is disabled in that case.

## Good to know

- **Overlapping selections**: a polygon that belongs to several selection tags goes to the right-most tag in the Object Manager.
- **Split by materials**: a polygon goes to the right-most material visible on it, as in the viewport. Polygons without any material stay on the source object.
- **Selection tags**: point, edge and polygon selection tags emptied by the conversion are removed. The others are updated to match the new objects.
- **Animation**: position, rotation and scale animation of the source object is kept on new objects placed next to it, or moved to the Null when grouping. With a centered axis, new objects are not animated unless they are grouped under a Null or placed inside the source object.

## Installation

Requires Cinema 4D R23 or newer. Tested with Cinema 4D 2023.

1. Download the zip file (or clone the project)
2. Copy the `SelectionToObject` folder into the `plugins` folder of your Cinema 4D installation, or add its parent folder in `Preferences > Plugins`
3. Restart Cinema 4D

## Development

The plugin code lives in the `selections_to_objects` package. `selection2object.pyp` only registers the command.

Tests run inside Cinema 4D with `c4dpy`, located in the Cinema 4D installation directory:

```
<Cinema 4D directory>/c4dpy tests/test_selection2object.py
```

## Changelog

- **v1.3.0**
  - [Feat] Convert several objects at once
  - [Feat] Split by materials
  - [Feat] Options dialog (gear icon), saved in the preferences
  - [Feat] Center axis of new objects
  - [Feat] Group new objects under a Null
  - [Feat] Delete source object only when empty
  - [Feat] Selection tags emptied by the conversion are removed
  - [Feat] New icon
  - [Fix] Deleting the source object no longer deletes its children
  - [Fix] Children of an animated source object were animated twice
  - [Perf] Faster on large meshes with many selections
- **v1.2.1**
  - [Fix] Materials applied to the whole object were removed from the new objects
  - [Fix] Children were offset when the source object was transformed
  - [Fix] Undo did not restore the deleted source object
  - [Fix] Undo on error
  - [Fix] Only materials restricted to converted selections are removed from the source object
  - [Perf] The source object is cloned only once
- **v1.2.0**
  - [Feat] Unused materials removed from split and source objects
- **v1.1.0**
  - [Fix] Incorrect children hierarchy
  - [Feat] Selection tag removed from source object
