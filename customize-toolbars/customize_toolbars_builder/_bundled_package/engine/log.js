/**
 * Customize_Toolbars — engine/log.js
 *
 * Thin structured logger. Every line is prefixed "[Customize_Toolbars]" and mirrored to
 * MessageLog + the process stdout, matching the house style used across the
 * other packages (see harmony/packages/My_Tools/configure.js `log`).
 *
 * @author Lilian Penzo
 */

function create(options) {
  var opts = options || {};
  var scope = opts.scope ? " " + opts.scope : "";
  var counts = { info: 0, warn: 0, error: 0 };

  function emit(level, message) {
    counts[level] = (counts[level] || 0) + 1;
    var line = "[Customize_Toolbars]" + scope + " " + level.toUpperCase() + ": " + message;
    try {
      MessageLog.trace(line);
    } catch (e) {}
    try {
      System.println(line);
    } catch (e2) {}
  }

  return {
    info: function (message) { emit("info", message); },
    warn: function (message) { emit("warn", message); },
    error: function (message) { emit("error", message); },
    child: function (childScope) {
      return create({ scope: (opts.scope ? opts.scope + "/" : "") + childScope });
    },
    counts: function () { return counts; }
  };
}

exports.create = create;
