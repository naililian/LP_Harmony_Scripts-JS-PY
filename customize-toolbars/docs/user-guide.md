# Customize Toolbars — user guide

A desktop tool that turns your Harmony scripts into toolbars (buttons + shortcuts
+ an optional menu) without hand-writing a `configure.js`. You arrange the
toolbar visually and it generates a **package** you drop into Harmony's
`packages/` folder.

---

## 1. Install (once)

Double-click **`run.bat`** — the first run creates a local `.venv` and installs
the three dependencies. Or manually:

```
py -3.9 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Needs **dukpy** + **jsonschema** (the builder runs the real engine for the live
preview) and **PySide6** (the window). Python 3.9 = the one Harmony ships.

---

## 2. Launch

```
run.bat
```

- Double-click, or run with no arguments → **opens the window**.
- A console stays open behind it — that's where errors/tracebacks show. Close it
  by closing the window.
- `run.bat gui my_project.lptb.json` → open with a project already loaded.

---

## 3. The window, panel by panel

```
┌─ Scripts ────────┬─ Toolbars ───────────────┬─ Item / Registers ────────┐
│ source folders   │ [toolbar combo] New Del  │ Label   [__________]      │
│ [Add] [Remove]   │ Title  [___________]     │ Icon    [__________]      │
│ [filter……]       │ Abbr   [RIG]             │ Shortcut[Alt+D]          │
│ ☑ hide non-      │ Menu   [__________]      │ ☑ show on toolbar        │
│   launchers      │ Shortcut cat. [_______]  │ ☑ show in menu           │
│ ┌──────────────┐ │ ┌──────────────────────┐ │ Companions               │
│ │ my_a  icon   │ │ │ Use Drawing Pivot    │ │ [my_tool_*.py        ]   │
│ │ my_b  env-o  │ │ │ Set Pivot by Drawing │ │                          │
│ │ …            │ │ │ Clone Drawing        │ │ ── Registers in Harmony ─│
│ └──────────────┘ │ └──────────────────────┘ │ toolbar 'Rig' — 4        │
│ [Add to toolbar▶]│ [▲][▼][Remove][+Submenu] │ buttons, 3 shortcuts…    │
└──────────────────┴──────────────────────────┴──────────────────────────┘
                                              [ ● editing… ]  [ Build ▾ ]
```

### 3.1 Scripts (left)

- **Source folders** — where your launcher `.js` files live. `Add folder…` to add
  another (e.g. scripts from another production).
- **filter** — type to narrow the list.
- **hide non-launchers** — hides `.js` files that are *helpers* (no top-level
  function to launch), e.g. `my_tool_helpers.js`.
- Each script shows its real icon (if one exists in a `script-icons/` folder next
  to it) plus tags: `no-icon`, `env-only` (see §7).
- Select one or more (Ctrl/Shift) → **Add to toolbar ▶** (or double-click). They
  go into the currently selected toolbar.

### 3.2 Toolbars (centre)

- **Combo + New / Delete** — several toolbars per package.
- **Title** — the toolbar's visible name (also the menu-group name and the header
  of the title button's message box).
- **Abbr** — 1–3 letters for the **badge** (the leading button that identifies
  the toolbar). Blank = first 3 characters of `id`.
- **Menu** — **blank = toolbar only** (the default). Type `Windows` (or another
  Harmony menu) to also create a menu group with the same items.
- **Shortcut cat.** — category in *Preferences ▸ Keyboard Shortcuts*. Defaults to
  Title.
- **Items list** — each row shows the icon it will get in Harmony (the real
  `script-icons` file, or a letter badge if there's none). `▲ ▼` reorder,
  **Remove**, **+ Submenu** adds a nested submenu (menu only, see §7).

### 3.3 Item / Registers (right)

With a script item selected:

| Field | What it does |
|---|---|
| **Label** | Button / menu text. Default = script name. |
| **Icon** | File in `icons/`. **Blank = automatic**: uses `<script>.png` from a `script-icons/` folder, and if none exists, generates a letter monogram. |
| **Shortcut** | *Suggested* key (e.g. `Alt+D`). Harmony does **not** let a script set the key — it shows in the shortcut's description and you assign it in Preferences. |
| **show on toolbar** | Put the button on the bar (default on). |
| **show in menu** | Put the entry in the menu (default on; only applies if the toolbar has a `Menu`). |
| **Companions** | Glob patterns for extra files to bundle next to the script, one per line. Needed for scripts with many modules, e.g. a tool split across `my_tool_*.py`, `my_tool_config.json`. |

**Registers in Harmony** — a live preview of what will be registered (buttons,
shortcuts, menu items) and **warnings** (missing script, `env-only`, unresolved
companion). It runs the real engine, so it's accurate.

### 3.4 The File menu

| Item | What it does |
|---|---|
| **New project** | Empty project. |
| **Open project… (.lptb.json)** | Reopen a saved project. |
| **Edit an installed toolbar package…** | Scans every Harmony version and lists the ones that already have your package. Pick one → it loads back into the editor (all toolbars, all items) and the window enters **editing mode**. |
| **Open a package folder…** | Browse to any folder containing `configure.js` and load it. |
| **Save project / Save project as…** | Writes a `.lptb.json` (package metadata + source folders + every toolbar). Handy to keep alongside the source scripts. |

**Editing mode** — when you open an installed package, the footer shows
*● editing installed package* and the bottom-right button becomes
**Save changes to Harmony**: it rebuilds and reinstalls straight over the package
you opened. (The ▾ still has *Build to folder*, *Build & install elsewhere*,
*Export .zip*, *Uninstall*.) To **remove** a toolbar, delete it in the centre
panel and Save. To remove **everything**, use Uninstall (see below).

---

## 4. Generate, install, uninstall — the bottom-right button

The button click does the most likely thing; the **▾** has the rest.

- **New / edited-from-a-project** → the button is **Build & install…**
- **Opened from an installed package** → the button is **Save changes to Harmony**
  (rebuilds and reinstalls over that package)

| ▾ option | What it does |
|---|---|
| **Build to folder…** | Writes the package to a folder you choose. |
| **Build && install…** | Shows **checkboxes** for every Toon Boom version detected, plus `Add folder…`. Tick **all the versions** you want (e.g. Harmony 24 and 25) and it copies the package into each. |
| **Export .zip…** | Makes a `.zip` of the package to hand to another machine. |
| **Uninstall from Harmony…** | Lists the versions that have your package; tick some, confirm → deletes the package folder from each. Removes all its toolbars. |

When it finishes you get a **"Done"** dialog with a summary. **Restart Harmony**
for changes to take effect (toolbars are built only at startup).

After installing, in Harmony: right-click a toolbar area → tick your toolbar; or
*Windows ▸ toolbars*.

---

## 5. Full config reference (`toolbars/<id>.json`)

You can hand-edit these files; the builder reads and rewrites them.

### Toolbar level

| Key | Type | Default | Description |
|---|---|---|---|
| `id` | string | — | Stable slug. Internal ids are derived from it. **Required.** |
| `title` | string | — | Visible name. **Required.** |
| `abbr` | string (1–3) | `id[:3]` | Text of the leading badge. |
| `menu` | string \| null | `null` | **Opt-in.** `"Windows"` (or another menu) to add a menu group. Omit = toolbar only. |
| `shortcutCategory` | string | `title` | Category in Preferences ▸ Keyboard Shortcuts. |
| `customizable` | bool | `true` | Harmony's "customizable" toolbar flag. |
| `iconFallback` | `"monogram"` \| `"none"` | `"monogram"` | `monogram` = generate a letter badge for icon-less buttons; `none` = leave Harmony's placeholder. |
| `titleButton` | bool \| object | `true` | `false` removes it. Object: `{ "icon": "x.svg", "tooltip": "…", "onClick": "info" }`. `onClick`: `info` (message box with the item list) / `menu` (same as info) / `none` (inert). |
| `items` | array | `[]` | See below. |

### Items

An item is **a string** (script name, everything default) or **an object**:

| Key | Type | Default | Description |
|---|---|---|---|
| `type` | `"script"` \| `"submenu"` | `script` | |
| `script` | string | — | Basename of the `.js`. **Required** for `script`. |
| `entry` | string | = `script` | Function inside the `.js` to launch. |
| `label` | string | = `script` | Button / menu text. |
| `icon` | string | auto | File in `icons/`. Auto = `<script>.png` → monogram. |
| `shortcut` | string | — | Suggested key (informational only, see §7). |
| `toolbar` | bool | `true` | Include as a button. |
| `menu` | bool | `true` | Include as a menu item (only if the toolbar has `menu`). |
| `checkable` | bool | `false` | Toggle-style button. |
| `companions` | string[] | — | Glob patterns for extra files to bundle. Read by the builder only. |

**Submenu**: `{ "type": "submenu", "label": "Pivots", "items": ["my_a", "my_b"] }`
— adds nested menu entries only, no toolbar buttons.

### `.js` instead of `.json` (advanced)

For comments or conditional logic, `toolbars/<id>.js`:

```js
exports.toolbar = { id: "rig", title: "Rig", items: [ /* … */ ] };
// or, conditional:
exports.build = function (ctx) {           // ctx = { packageFolder, harmonyVersion, isPaintMode }
  var items = ["my_a"];
  if (ctx.harmonyVersion >= 25) items.push("my_h25_only");
  return { id: "rig", title: "Rig", items: items };
};
```

The engine prefers the `.js` if both exist.

---

## 6. The generated package

```
Customize_Toolbars/
  configure.js          # what Harmony runs
  tbpackage.json        # metadata
  engine/               # the engine — don't edit
  toolbars/<id>.json    # one per toolbar
  scripts/              # copies of the .js + companions (self-contained)
  icons/                # script icons + generated badges (_title-*, _mono-*)
```

Installs into:
- `%APPDATA%\Toon Boom Animation\<edition>\<NNNN>-scripts\packages\`
  (one per version: `2400` = Harmony 24, `2500` = Harmony 25, …)
- or the folder named by `TB_EXTERNAL_SCRIPT_PACKAGES_FOLDER`.

`run.bat locations` lists the ones it detects.

---

## 7. Limits & things to know

- **No default keystrokes.** Harmony doesn't let a script set the key combo. It
  registers an assignable entry and you set the key in *Preferences ▸ Keyboard
  Shortcuts*. `shortcut` in the config is just a note.
- **Built at startup.** Edit a toolbar → reinstall → restart Harmony.
- **No toolbar separators.** Harmony's `ScriptToolbarDef` has no API for it.
  `"---"` in a config is ignored.
- **Submenus are menu-only** (no toolbar buttons).
- **`env-only` scripts.** Some launchers locate their `.py` (or helpers) via the
  `TOONBOOM_GLOBAL_SCRIPT_LOCATION` environment variable rather than their own
  file path. They work as long as that variable is set on the target machine.
  The preview and the build report flag them.
- **One package.** All your toolbars live in `Customize_Toolbars`. To drop one
  toolbar, delete it in the builder and reinstall; to drop everything, use
  **Uninstall from Harmony…**.

---

## 8. CLI (no window)

```
run.bat build <project.lptb.json> [options]
run.bat scan <folder> [--recursive]
run.bat locations
```

**`build`**

| Flag | Description |
|---|---|
| `--out DIR` | Where to write the package (default `dist`). |
| `--install DIR` | Copy into that `packages/` folder. **Repeatable** (`--install A --install B`) for several versions. |
| `--zip FILE` | Also produce a `.zip`. |
| `--harmony N` | Target Harmony major version (only affects `.js` configs using `build(ctx)`). |
| `--force` | Build even with config errors. |

**`scan`** — lists the launcher scripts in a folder with their kind
(`file_fallback` / `env_only` / `plain`), whether they have a `.py` / `.ui` /
icon, and the files they reference.

**`locations`** — the `packages/` folders it detects, with `[ok]` / `[missing]` /
`read-only`.

---

## 9. Typical workflow

1. `run.bat`
2. Left panel: choose your scripts folder.
3. Centre panel: **New** → Title `Rig`, Abbr `RIG`.
4. Left: select scripts → **Add to toolbar ▶**. Reorder with ▲▼.
5. Right: per script set Label / icon / suggested shortcut. For a multi-module
   tool, set Companions like `my_tool_*.py`.
6. Repeat 3–5 for more toolbars.
7. **File ▸ Save project** (so you can edit it again later).
8. **Build & install…** → tick every Harmony version → install.
9. Restart Harmony. Right-click the toolbar area → enable your toolbars.
