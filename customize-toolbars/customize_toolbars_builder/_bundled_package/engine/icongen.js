/**
 * Customize_Toolbars — engine/icongen.js
 *
 * PURE: builds tiny SVG "badge" icons from 1-3 letters, used when a button has
 * no real icon file. The toolbar's leading title button always uses one (the
 * user's `abbr`); script buttons fall back to a monogram of their label unless
 * `iconFallback: "none"`.
 *
 * Qt's SVG renderer is picky — plain attributes only, no CSS, no
 * dominant-baseline. Unit-tested offline (harmony/tests/toolbars/).
 *
 * @author Lilian Penzo
 */

(function (root) {
  "use strict";

  function escapeXml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** Up to 3 A-Z/0-9 chars from a free-form string (word initials, else prefix). */
  function abbreviate(source, max) {
    var limit = max || 3;
    var clean = String(source == null ? "" : source).toUpperCase();
    var words = clean.split(/[^A-Z0-9]+/);
    var real = [];
    for (var i = 0; i < words.length; i += 1) {
      if (words[i]) {
        real.push(words[i]);
      }
    }
    if (real.length >= 2) {
      var initials = "";
      for (var j = 0; j < real.length && initials.length < limit; j += 1) {
        initials += real[j].charAt(0);
      }
      return initials;
    }
    return (real[0] || "").slice(0, limit) || "?";
  }

  /**
   * badgeSvg(text, opts)
   *   opts.color   stroke + text colour        (default "#d0d0d0")
   *   opts.border  draw the rounded outline    (default true)
   */
  function badgeSvg(text, opts) {
    var o = opts || {};
    var label = String(text || "?").slice(0, 3).toUpperCase();
    var color = o.color || "#d0d0d0";
    var border = o.border === undefined ? true : !!o.border;

    var w = 30;
    var h = 22;
    var fontSize = label.length >= 3 ? 9.5 : (label.length === 2 ? 12 : 14);
    var baseline = h / 2 + fontSize * 0.35; // optical vertical centre, no dominant-baseline

    var parts = [];
    parts.push(
      '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h +
      '" viewBox="0 0 ' + w + ' ' + h + '">'
    );
    if (border) {
      parts.push(
        '<rect x="1" y="1" width="' + (w - 2) + '" height="' + (h - 2) +
        '" rx="3.5" ry="3.5" fill="none" stroke="' + color +
        '" stroke-opacity="0.55" stroke-width="1.5"/>'
      );
    }
    parts.push(
      '<text x="' + (w / 2) + '" y="' + baseline.toFixed(1) + '" fill="' + color +
      '" font-family="Arial, Helvetica, sans-serif" font-size="' + fontSize +
      '" font-weight="700" text-anchor="middle" letter-spacing="0.5">' +
      escapeXml(label) + '</text>'
    );
    parts.push('</svg>');
    return parts.join("");
  }

  var api = { badgeSvg: badgeSvg, abbreviate: abbreviate, escapeXml: escapeXml };

  if (typeof exports !== "undefined") {
    exports.badgeSvg = badgeSvg;
    exports.abbreviate = abbreviate;
    exports.escapeXml = escapeXml;
  }
  root.CustomizeToolbarsIconGen = api;
})(this);
