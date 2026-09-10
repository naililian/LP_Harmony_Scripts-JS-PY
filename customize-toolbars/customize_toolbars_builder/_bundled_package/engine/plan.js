/**
 * Customize_Toolbars — engine/plan.js
 *
 * PURE transform: one toolbar config object -> a flat "registration plan" that
 * engine/register.js replays against Harmony's ScriptManager API.
 *
 * No Harmony API, no file IO, no `require`. Everything comes in through `config`
 * and `ctx`. This is the only engine module unit-tested offline
 * (harmony/tests/toolbars/); register.js / index.js touch Harmony and are
 * covered by the in-Harmony smoke checklist in docs/toolbars/.
 *
 *   ctx = {
 *     scriptsDir     : "<packageFolder>/scripts",   // builds launch commands
 *     harmonyVersion : 25,                            // optional, informational
 *     hasIcon        : function (name)     { ... },   // optional -> ICON_MISSING warnings
 *     hasScript      : function (basename) { ... }    // optional -> SCRIPT_NOT_BUNDLED warnings
 *   }
 *
 * Buttons / menu items / shortcuts for script items carry the Harmony launch
 * command string directly ("<Func> in <path>.js") — the pattern proven by
 * harmony/packages/LP_Deformer_Tool/configure.js and My_Tools. addAction is also
 * emitted (named entry) but nothing depends on referencing it by id. Only the
 * title button, which has a real onTrigger, is wired by action id.
 *
 * @author Lilian Penzo
 */

(function (root) {
  "use strict";

  var ID_PREFIX = "customize.toolbars"; // matches docs/specs/manifest-schema.json id pattern

  // ---------------------------------------------------------------- helpers ---

  function slug(value) {
    return String(value == null ? "" : value)
      .replace(/[^A-Za-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .toLowerCase();
  }

  function mintId(kind, toolbarSlug, nameSlug) {
    var id = ID_PREFIX + "." + kind + "." + toolbarSlug;
    return nameSlug ? id + "." + nameSlug : id;
  }

  function flag(value, fallback) {
    return value === undefined || value === null ? fallback : !!value;
  }

  // Harmony's ScriptToolbarDef has no addSeparator, so "---" / {type:"separator"}
  // are tolerated for hand-authored configs but produce nothing.
  function isSeparator(item) {
    return item === "---" || (item && item.type === "separator");
  }

  function normalizeItem(item) {
    if (typeof item === "string") {
      return item === "---" ? { type: "separator" } : { type: "script", script: item };
    }
    var copy = {};
    for (var key in item) {
      if (item.hasOwnProperty(key)) {
        copy[key] = item[key];
      }
    }
    if (!copy.type) {
      copy.type = copy.items ? "submenu" : "script";
    }
    return copy;
  }

  function launchCommand(item, scriptsDir) {
    var entry = item.entry || item.script;
    return entry + " in " + scriptsDir + "/" + item.script + ".js";
  }

  /**
   * The house convention: an icon in script-icons/ named after the script (which
   * is also its main function name), e.g. LP_use_drawing_pivot.png. The builder
   * copies these into the package icons/ folder. Returns the filename that
   * exists, or ".png" on faith when ctx can't probe.
   */
  function conventionIcon(basename, ctx) {
    var candidates = [basename + ".png", basename + ".svg"];
    if (!ctx || !ctx.hasIcon) {
      return candidates[0];
    }
    for (var i = 0; i < candidates.length; i += 1) {
      if (ctx.hasIcon(candidates[i])) {
        return candidates[i];
      }
    }
    return null;
  }

  function warnIconMissing(ctx, name, warnings, owner) {
    if (ctx && ctx.hasIcon && name && !ctx.hasIcon(name)) {
      warnings.push("ICON_MISSING: '" + name + "' for " + owner + " (button shows no icon)");
    }
  }

  function warnScriptMissing(ctx, script, warnings) {
    if (ctx && ctx.hasScript && !ctx.hasScript(script)) {
      warnings.push("SCRIPT_NOT_BUNDLED: '" + script + ".js' not found in scripts/");
    }
  }

  function infoBody(title, items) {
    var lines = [];
    var list = items || [];
    for (var i = 0; i < list.length; i += 1) {
      var it = list[i];
      if (isSeparator(it)) {
        continue;
      }
      if (typeof it === "string") {
        lines.push("• " + it);
      } else if (it && it.type === "submenu") {
        lines.push("• " + (it.label || "Submenu") + " …");
      } else if (it && (it.label || it.script)) {
        lines.push("• " + (it.label || it.script));
      }
    }
    return title + "\n\n" + (lines.length ? lines.join("\n") : "(no items)");
  }

  // ------------------------------------------------------------------ build ---

  function build(rawConfig, rawCtx) {
    var config = rawConfig || {};
    var ctx = rawCtx || {};
    var warnings = [];

    var title = config.title || config.id || "Untitled toolbar";
    var tbSlug = slug(config.id || title);
    if (!tbSlug) {
      return { ok: false, warnings: ["EMPTY_ID: config has no usable 'id' or 'title'"] };
    }

    var scriptsDir = ctx.scriptsDir || "scripts";
    var toolbarId = mintId("toolbar", tbSlug);
    var menuId = mintId("menu", tbSlug);
    // Menu group is opt-in: only when `menu` is a non-empty string (e.g. "Windows").
    var menuName = config.menu ? config.menu : null;
    var shortcutCategory = config.shortcutCategory || title;
    var iconFallback = config.iconFallback === "none" ? "none" : "monogram";

    var plan = {
      ok: true,
      title: title,
      toolbarId: toolbarId,
      menuId: menuId,
      warnings: warnings,
      actions: [],
      shortcuts: [],
      toolbar: {
        id: toolbarId,
        text: title,
        customizable: flag(config.customizable, true),
        buttons: []
      },
      menu: menuName ? { targetMenuId: menuName, id: menuId, text: title } : null,
      submenus: [],
      menuItems: [],
      // { name, text, border } — SVG badges engine/index.js renders into icons/
      // when the file is absent (title initials, script monograms).
      generatedIcons: []
    };

    var usedNameSlugs = {};
    function uniqueName(base) {
      var name = base || "item";
      var candidate = name;
      var n = 2;
      while (usedNameSlugs[candidate]) {
        candidate = name + "_" + n;
        n += 1;
      }
      usedNameSlugs[candidate] = true;
      return candidate;
    }

    addTitleButton(plan, config, tbSlug, warnings, ctx, uniqueName);

    var items = config.items || [];
    for (var i = 0; i < items.length; i += 1) {
      var item = normalizeItem(items[i]);

      if (isSeparator(item)) {
        continue; // no toolbar-separator API in Harmony
      } else if (item.type === "submenu") {
        addSubmenu(plan, item, tbSlug, scriptsDir, ctx, warnings, uniqueName);
      } else if (item.type === "script") {
        addScript(plan, item, tbSlug, scriptsDir, shortcutCategory, iconFallback, ctx, warnings, uniqueName);
      } else {
        warnings.push("UNKNOWN_ITEM_TYPE: '" + item.type + "' (index " + i + ") ignored");
      }
    }

    plan.generatedIcons = dedupeByName(plan.generatedIcons);
    return plan;
  }

  function dedupeByName(list) {
    var seen = {};
    var out = [];
    for (var i = 0; i < list.length; i += 1) {
      if (!seen[list[i].name]) {
        seen[list[i].name] = true;
        out.push(list[i]);
      }
    }
    return out;
  }

  function addTitleButton(plan, config, tbSlug, warnings, ctx, uniqueName) {
    var tb = config.titleButton;
    if (tb === undefined) {
      tb = true;
    }
    if (!tb) {
      return;
    }
    var spec = tb === true ? {} : tb;
    uniqueName("title");
    var actionId = mintId("action", tbSlug, "title");
    var text = spec.tooltip || plan.title;
    var onClick = spec.onClick || "info";

    // The leading button shows the toolbar's initials (config.abbr, <=3 chars).
    // An explicit titleButton.icon wins; otherwise a badge SVG is generated.
    var icon;
    if (spec.icon) {
      icon = spec.icon;
      warnIconMissing(ctx, icon, warnings, "titleButton");
    } else {
      icon = "_title-" + tbSlug + ".svg";
      plan.generatedIcons.push({
        name: icon,
        text: config.abbr || tbSlug,
        border: true
      });
    }

    plan.actions.push({
      id: actionId,
      text: text,
      icon: icon,
      longDesc: plan.title,
      kind: onClick === "menu" ? "openMenu" : (onClick === "none" ? "noop" : "info"),
      infoTitle: plan.title,
      infoBody: infoBody(plan.title, config.items),
      openMenuId: plan.menuId
    });
    plan.toolbar.buttons.push({
      text: text,
      icon: icon,
      action: actionId,
      checkable: false,
      isTitle: true
    });
  }

  function addScript(plan, item, tbSlug, scriptsDir, shortcutCategory, iconFallback, ctx, warnings, uniqueName) {
    if (!item.script) {
      warnings.push("SCRIPT_MISSING_NAME: a script item has no 'script' field; ignored");
      return;
    }
    var label = item.label || item.script;
    var name = uniqueName(slug(label));
    var actionId = mintId("action", tbSlug, name);
    var shortcutId = mintId("shortcut", tbSlug, name);
    var launch = launchCommand(item, scriptsDir);
    var suggested = item.shortcut ? " (suggested key: " + item.shortcut + ")" : "";
    var longDesc = "Run: " + item.script + suggested;

    warnScriptMissing(ctx, item.script, warnings);

    var icon;
    if (item.icon) {
      icon = item.icon;
      warnIconMissing(ctx, icon, warnings, item.script);
    } else {
      var found = conventionIcon(item.script, ctx);
      if (found) {
        icon = found;
      } else if (iconFallback === "monogram") {
        icon = "_mono-" + name + ".svg";
        plan.generatedIcons.push({ name: icon, text: label, border: false });
      } else {
        icon = item.script + ".png";
        warnIconMissing(ctx, icon, warnings, item.script);
      }
    }

    plan.actions.push({
      id: actionId,
      text: label,
      icon: icon,
      longDesc: longDesc,
      kind: "launch",
      launch: launch
    });
    plan.shortcuts.push({
      id: shortcutId,
      text: label,
      action: launch,
      longDesc: longDesc,
      categoryId: plan.toolbarId,
      categoryText: shortcutCategory
    });
    if (flag(item.toolbar, true)) {
      plan.toolbar.buttons.push({
        text: label,
        icon: icon,
        action: launch,
        checkable: flag(item.checkable, false),
        shortcut: shortcutId
      });
    }
    if (flag(item.menu, true) && plan.menu) {
      plan.menuItems.push({
        targetMenuId: plan.menuId,
        id: mintId("menuitem", tbSlug, name),
        text: label,
        action: launch,
        shortcut: shortcutId
      });
    }
  }

  function addSubmenu(plan, item, tbSlug, scriptsDir, ctx, warnings, uniqueName) {
    if (!plan.menu) {
      warnings.push("SUBMENU_WITHOUT_MENU: '" + (item.label || "?") + "' skipped (toolbar has menu:null)");
      return;
    }
    var label = item.label || "Submenu";
    var subName = uniqueName(slug(label));
    var subId = mintId("menu", tbSlug, subName);
    plan.submenus.push({ targetMenuId: plan.menuId, id: subId, text: label });

    var children = item.items || [];
    for (var i = 0; i < children.length; i += 1) {
      var child = normalizeItem(children[i]);
      if (child.type !== "script" || !child.script) {
        warnings.push("SUBMENU_ITEM_IGNORED: only script items are supported inside submenus");
        continue;
      }
      var childLabel = child.label || child.script;
      var childName = uniqueName(slug(subName + "_" + childLabel));
      var actionId = mintId("action", tbSlug, childName);
      warnScriptMissing(ctx, child.script, warnings);
      plan.actions.push({
        id: actionId,
        text: childLabel,
        icon: child.icon || conventionIcon(child.script, ctx) || (child.script + ".png"),
        longDesc: "Run: " + child.script,
        kind: "launch",
        launch: launchCommand(child, scriptsDir)
      });
      plan.menuItems.push({
        targetMenuId: subId,
        id: mintId("menuitem", tbSlug, childName),
        text: childLabel,
        action: launchCommand(child, scriptsDir)
      });
    }
  }

  // ----------------------------------------------------------------- export ---

  var api = { build: build, slug: slug, mintId: mintId, infoBody: infoBody };

  if (typeof exports !== "undefined") {
    exports.build = build;
    exports.slug = slug;
    exports.mintId = mintId;
    exports.infoBody = infoBody;
  }
  root.CustomizeToolbarsPlan = api;
})(this);
