# Selections To Objects

##### Cinema 4D Python Plugin

![Selections To Object Icon](https://3.bp.blogspot.com/-ldXQ2BSFV8M/Xn4udU72loI/AAAAAAAACe4/5jtp9pKhZXYRGTHJQRNmtAUuuGzsXH7-gCKgBGAsYHg/s1600/selections2objects256.png "Icon")

Convert all polygon selection tags into separate objects

For more informations please visit : <https://safina3d.blogspot.com>

#### Installation

Requires Cinema 4D R23 or newer (Python 3).

Clone the project or download the zip file and extract it into the Cinema 4D plugins directory.

- Windows: `C:\Program Files\Maxon Cinema 4D <version>\plugins\`
- MacOS: `/Applications/Maxon Cinema 4D <version>/plugins/`

You can also add the folder to the plugin paths in `Preferences > Plugins`.

### How to use

- Select your polygon object
- Make sure that your object has at least one **polygon selection tag**
- Click on the "Selections To Objects" icon to run the plugin

### Additional commands

- SHIFT Button: Make the generated objects children of the original object
- CTRL Button: Delete the original object (ignored when SHIFT is pressed)

### Notes

- When a polygon belongs to several selection tags, it goes to the right-most tag in the Object Manager.
- Materials applied to the whole object are kept on every generated object. Materials restricted to a converted selection are moved to the matching object.

### Tests

Tests run inside Cinema 4D with `c4dpy`, located in the Cinema 4D installation directory:

```
<Cinema 4D directory>/c4dpy tests/test_selection2object.py
```

### ChangeLog

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
