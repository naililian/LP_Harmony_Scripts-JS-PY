/**
 * Customize_Toolbars — package entry point.
 *
 * Declarative Harmony toolbars: drop a file in toolbars/ (JSON or JS) and get a
 * full toolbar + assignable shortcuts + a Windows-menu group, with no
 * boilerplate. Schema: engine/toolbar.schema.json. Docs: docs/toolbars/.
 *
 * Generated and edited by tools/lp_toolbar_builder (PySide6). Safe to hand-edit
 * the toolbars/*.json files; run "Regenerate" in the builder to refresh engine/.
 *
 * @author Lilian Penzo
 */

function configure(packageFolder, packageName) {
  if (about.isPaintMode()) {
    return;
  }
  try {
    var root = String(packageFolder || "").split("\\").join("/").replace(/\/+$/, "");
    require(root + "/engine/index.js").bootstrap(root);
  } catch (err) {
    MessageLog.trace("[Customize_Toolbars] disabled: " + err);
  }
}

function init() {
  // Reserved. Toolbars are built in configure(); nothing to do post-load.
}

exports.configure = configure;
exports.init = init;
