# Selections To Objects

##### Cinema 4D Python Plugin

![Selections To Objects Icon](SelectionToObject/res/icons/selection.png "Icon")

Convert all polygon selection tags, or all materials, into separate objects

For more informations please visit : <https://safina3d.blogspot.com>

#### Installation

Requires Cinema 4D R23 or newer (Python 3).

Clone the project or download the zip file and extract it into the Cinema 4D plugins directory.

- Windows: `C:\Program Files\Maxon Cinema 4D <version>\plugins\`
- MacOS: `/Applications/Maxon Cinema 4D <version>/plugins/`

You can also add the folder to the plugin paths in `Preferences > Plugins`.

### How to use

- Select one or more polygon objects
- Make sure that your objects have at least one **polygon selection tag** (or one **material** when splitting by materials)
- Click on the "Selections To Objects" icon to run the plugin

All selected objects are converted in a single undo step.

### Options

Click on the gear icon next to the command in the menu to open the options dialog:

- **Split**
  - *Create one object per*: polygon selection tag, or material tag (using the polygons where the material is visible)
- **New objects**
  - *Place them*: next to the source object, or inside it as children
  - *Put them in a Null named after the source object*
  - *Move the axis of each one to the center of its polygons*
- **Source object**
  - *After conversion*: keep it with its remaining polygons, delete it, or delete it only if no polygon is left. Not available when new objects are placed inside it. Its child objects are always kept.

Options are saved in the Cinema 4D preferences.

### Additional commands

- SHIFT Button: Make the generated objects children of the original object
- CTRL Button: Delete the original object (ignored when SHIFT is pressed)

### Notes

- When a polygon belongs to several selection tags, it goes to the right-most tag in the Object Manager.
- Materials applied to the whole object are kept on every generated object. Materials restricted to a converted selection are moved to the matching object.
- When splitting by materials, a polygon goes to the right-most material visible on it. Polygons without material stay on the source object.
- Point, edge and polygon selection tags emptied by the conversion are removed.
- Position, rotation and scale animation of the source object is kept on generated objects inserted next to it, or on the null when grouping. With *Center axis*, generated objects are not animated unless grouped under a null or inserted as children.

### Tests

Tests run inside Cinema 4D with `c4dpy`, located in the Cinema 4D installation directory:

```
<Cinema 4D directory>/c4dpy tests/test_selection2object.py
```

### ChangeLog

- v1.3.0
  - [Feat] Convert several objects at once
  - [Feat] Options dialog (gear icon), saved in the preferences
  - [Feat] Split by materials
  - [Feat] Center axis of generated objects
  - [Feat] Group generated objects under a null
  - [Feat] Delete source object when empty
  - [Feat] New icon and clearer options
  - [Feat] Selection tags emptied by the conversion are removed
  - [Fix] Deleting the source object no longer deletes its children
  - [Fix] Generated children of an animated source object were animated twice
  - [Perf] Faster on large meshes with many selections
- v1.2.1
  - [Fix] Materials applied to the whole object were removed from the generated objects
  - [Fix] Generated children were offset when the original object was transformed
  - [Fix] Undo did not restore the deleted original object
  - [Fix] Undo on error
  - [Fix] Only materials restricted to converted selections are removed from the source object
  - [Perf] The source object is cloned only once
- v1.2.0
  - [Feat] Unused materials removed from split and source objects
- v1.1.0
  - [Fix] Incorrect children hierarchy
  - [Feat] Selection tag removed from source object
