/**
 * Customize_Toolbars — engine/index.js
 *
 * Bootstrap: scan toolbars/, turn each config into a plan (engine/plan.js), and
 * replay it into Harmony (engine/register.js). One toolbar failing is isolated
 * and logged; the rest still load.
 *
 * @author Lilian Penzo
 */

// Harmony's require() is unreliable with relative paths from a nested module
// (see harmony/packages/UIManagerFramework/bootstrap.js), so engine siblings are
// required by absolute path inside bootstrap() once packageFolder is known.
var fs = null;
var logMod = null;
var planMod = null;
var registerMod = null;
var iconGen = null;

function loadModules(root) {
  fs = require(root + "/engine/fsutil.js");
  logMod = require(root + "/engine/log.js");
  planMod = require(root + "/engine/plan.js");
  registerMod = require(root + "/engine/register.js");
  iconGen = require(root + "/engine/icongen.js");
}

/** Render plan.generatedIcons into icons/ when the file is missing. */
function materializeIcons(plan, iconsDir, log) {
  for (var i = 0; i < plan.generatedIcons.length; i += 1) {
    var g = plan.generatedIcons[i];
    var path = iconsDir + "/" + g.name;
    if (fs.exists(path)) {
      continue;
    }
    var svg = iconGen.badgeSvg(iconGen.abbreviate(g.text, 3), { border: g.border });
    if (!fs.writeText(path, svg)) {
      log.warn("could not write generated icon " + g.name + " (folder read-only?)");
    }
  }
}

function detectHarmonyVersion() {
  try {
    var raw = "";
    if (typeof about !== "undefined" && about.getVersionString) {
      raw = String(about.getVersionString());
    }
    var m = raw.match(/(\d+)/);
    return m ? parseInt(m[1], 10) : 0;
  } catch (e) {
    return 0;
  }
}

/** List toolbars/*.{json,js}, one entry per basename, .js preferred over .json. */
function collectConfigFiles(dir) {
  var names = fs.listFiles(dir, ["*.json", "*.js"]);
  var byId = {};
  for (var i = 0; i < names.length; i += 1) {
    var name = names[i];
    if (name.charAt(0) === "_" || name.charAt(0) === ".") {
      continue;
    }
    var dot = name.lastIndexOf(".");
    var id = name.slice(0, dot);
    var ext = name.slice(dot + 1).toLowerCase();
    if (!byId[id] || ext === "js") {
      byId[id] = { id: id, ext: ext, path: dir + "/" + name };
    }
  }
  var out = [];
  for (var key in byId) {
    if (byId.hasOwnProperty(key)) {
      out.push(byId[key]);
    }
  }
  out.sort(function (a, b) { return a.id < b.id ? -1 : (a.id > b.id ? 1 : 0); });
  return out;
}

function loadConfig(entry, envCtx, log) {
  if (entry.ext === "js") {
    var mod = require(entry.path);
    if (typeof mod.build === "function") {
      return mod.build(envCtx);
    }
    if (mod.toolbar) {
      return mod.toolbar;
    }
    log.error(entry.id + ".js must export `toolbar` (object) or `build` (function)");
    return null;
  }
  var parsed = fs.parseJsonc(fs.readText(entry.path), entry.id + ".json");
  if (!parsed.ok) {
    log.error(parsed.error);
    return null;
  }
  return parsed.value;
}

function bootstrap(packageFolder) {
  var root = String(packageFolder || "").split("\\").join("/").replace(/\/+$/, "");
  loadModules(root);
  var log = logMod.create();
  var toolbarsDir = root + "/toolbars";
  var scriptsDir = root + "/scripts";
  var iconsDir = root + "/icons";

  var configFiles = collectConfigFiles(toolbarsDir);
  if (!configFiles.length) {
    log.warn("no toolbar configs in " + toolbarsDir);
    return { ok: true, toolbars: 0 };
  }

  var envCtx = {
    packageFolder: root,
    harmonyVersion: detectHarmonyVersion(),
    isPaintMode: (typeof about !== "undefined" && about.isPaintMode) ? about.isPaintMode() : false
  };
  var planCtx = {
    scriptsDir: scriptsDir,
    harmonyVersion: envCtx.harmonyVersion,
    hasIcon: function (name) { return !!name && fs.exists(iconsDir + "/" + name); },
    hasScript: function (base) { return !!base && fs.exists(scriptsDir + "/" + base + ".js"); }
  };

  var made = 0;
  for (var i = 0; i < configFiles.length; i += 1) {
    var entry = configFiles[i];
    var sub = log.child(entry.id);
    try {
      var config = loadConfig(entry, envCtx, sub);
      if (!config) {
        continue;
      }
      var plan = planMod.build(config, planCtx);
      for (var w = 0; w < plan.warnings.length; w += 1) {
        sub.warn(plan.warnings[w]);
      }
      if (!plan.ok) {
        sub.error("config produced no plan; skipped");
        continue;
      }
      materializeIcons(plan, iconsDir, sub);
      var tally = registerMod.apply(plan, { log: sub, iconsDir: iconsDir });
      sub.info(
        "loaded '" + plan.title + "' — " + tally.buttons + " buttons, " +
        tally.menuItems + " menu items, " + tally.shortcuts + " shortcuts" +
        (tally.errors ? " (" + tally.errors + " errors)" : "")
      );
      made += 1;
    } catch (err) {
      sub.error("failed to load: " + err);
    }
  }

  log.info("bootstrap complete — " + made + "/" + configFiles.length + " toolbars");
  return { ok: true, toolbars: made };
}

exports.bootstrap = bootstrap;
