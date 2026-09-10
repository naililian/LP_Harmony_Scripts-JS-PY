/**
 * Customize_Toolbars — engine/fsutil.js
 *
 * The small amount of filesystem access the engine needs at bootstrap: list the
 * toolbars/ folder, read a config file, probe for an icon/script. Kept in one
 * place so plan.js can stay pure.
 *
 * @author Lilian Penzo
 */

function normalizePath(path) {
  return String(path || "").split("\\").join("/").replace(/\/+$/, "");
}

function join(a, b) {
  return normalizePath(a) + "/" + String(b || "").replace(/^\/+/, "");
}

/** File basenames in `folder` matching any of `filters` (e.g. ["*.json","*.js"]). */
function listFiles(folder, filters) {
  var dir = new QDir(folder);
  if (!dir.exists()) {
    return [];
  }
  if (filters && filters.length) {
    dir.setNameFilters(filters);
  }
  dir.setFilter(QDir.Files);
  return dir.entryList();
}

function exists(path) {
  return new QFileInfo(path).exists();
}

/** Read a UTF-8 text file, "" on any failure. */
function readText(path) {
  try {
    var file = new QFile(path);
    if (!file.exists() || !file.open(QIODevice.ReadOnly)) {
      return "";
    }
    var stream = new QTextStream(file);
    try {
      stream.setCodec("UTF-8");
    } catch (e) {}
    var text = stream.readAll();
    file.close();
    return String(text || "");
  } catch (err) {
    return "";
  }
}

/** Write a UTF-8 text file. Returns false on any failure (e.g. read-only dir). */
function writeText(path, text) {
  try {
    var file = new File(path);
    file.open(FileAccess.WriteOnly);
    file.write(String(text));
    file.close();
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Parse JSON that may carry `//` line comments and block comments (JSON5-lite).
 * Raw JSON.parse is tried first so valid files are never touched.
 */
function parseJsonc(text, sourceLabel) {
  try {
    return { ok: true, value: JSON.parse(text) };
  } catch (first) {}
  var stripped = String(text)
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
  try {
    return { ok: true, value: JSON.parse(stripped) };
  } catch (second) {
    return { ok: false, error: (sourceLabel || "config") + ": " + second };
  }
}

exports.normalizePath = normalizePath;
exports.join = join;
exports.listFiles = listFiles;
exports.exists = exists;
exports.readText = readText;
exports.writeText = writeText;
exports.parseJsonc = parseJsonc;
