/**
 * Customize_Toolbars — engine/register.js
 *
 * Replays a plan (from engine/plan.js) against Harmony's ScriptManager API,
 * one guarded call at a time so a single bad entry never sinks the toolbar.
 *
 * Registration order follows docs/specs/lifecycle-and-bootstrap.md:
 *   actions -> menu -> submenus -> menu items -> shortcuts -> toolbar.
 *
 * This module is Harmony-only; it is verified by the in-Harmony smoke checklist
 * in docs/toolbars/, not by the offline suite.
 *
 * @author Lilian Penzo
 */

function makeInfoHandler(body) {
  return function () {
    try {
      MessageBox.information(body);
    } catch (e) {
      MessageLog.trace(body);
    }
  };
}

function apply(plan, deps) {
  var d = deps || {};
  var log = d.log || { info: function () {}, warn: function () {}, error: function () {} };
  var tally = {
    actions: 0, menu: 0, submenus: 0, menuItems: 0, shortcuts: 0, buttons: 0, errors: 0
  };

  function guard(what, fn) {
    try {
      fn();
    } catch (err) {
      tally.errors += 1;
      log.error(what + ": " + err);
    }
  }

  // 1. actions ---------------------------------------------------------------
  for (var a = 0; a < plan.actions.length; a += 1) {
    (function (action) {
      guard("action " + action.id, function () {
        var spec = {
          id: action.id,
          text: action.text,
          icon: action.icon || "",
          longDesc: action.longDesc || action.text
        };
        if (action.kind === "launch") {
          spec.action = action.launch;
        } else if (action.kind === "info" || action.kind === "openMenu") {
          // "openMenu" degrades to the same item listing; Harmony scripting has
          // no reliable "pop this menu" call.
          spec.onTrigger = makeInfoHandler(action.infoBody || action.text);
        } else {
          spec.onTrigger = function () {};
        }
        ScriptManager.addAction(spec);
        tally.actions += 1;
      });
    })(plan.actions[a]);
  }

  // 2. menu container ------------------------------------------------------
  if (plan.menu) {
    guard("menu " + plan.menu.id, function () {
      ScriptManager.addMenu({
        targetMenuId: plan.menu.targetMenuId,
        id: plan.menu.id,
        text: plan.menu.text,
        type: "global"
      });
      tally.menu += 1;
    });
  }

  // 3. submenus -----------------------------------------------------------
  for (var s = 0; s < plan.submenus.length; s += 1) {
    (function (sub) {
      guard("submenu " + sub.id, function () {
        ScriptManager.addMenu({ targetMenuId: sub.targetMenuId, id: sub.id, text: sub.text });
        tally.submenus += 1;
      });
    })(plan.submenus[s]);
  }

  // 4. menu items -------------------------------------------------------
  for (var m = 0; m < plan.menuItems.length; m += 1) {
    (function (mi) {
      guard("menuItem " + mi.id, function () {
        var spec = { targetMenuId: mi.targetMenuId, id: mi.id, text: mi.text, action: mi.action };
        if (mi.shortcut) {
          spec.shortcut = mi.shortcut;
        }
        ScriptManager.addMenuItem(spec);
        tally.menuItems += 1;
      });
    })(plan.menuItems[m]);
  }

  // 5. shortcuts ------------------------------------------------------
  for (var sc = 0; sc < plan.shortcuts.length; sc += 1) {
    (function (shortcut) {
      guard("shortcut " + shortcut.id, function () {
        ScriptManager.addShortcut({
          id: shortcut.id,
          text: shortcut.text,
          action: shortcut.action,
          longDesc: shortcut.longDesc || shortcut.text,
          categoryId: shortcut.categoryId,
          categoryText: shortcut.categoryText
        });
        tally.shortcuts += 1;
      });
    })(plan.shortcuts[sc]);
  }

  // 6. toolbar -----------------------------------------------------
  guard("toolbar " + plan.toolbar.id, function () {
    var def = new ScriptToolbarDef({
      id: plan.toolbar.id,
      text: plan.toolbar.text,
      customizable: plan.toolbar.customizable ? "true" : "false"
    });
    for (var b = 0; b < plan.toolbar.buttons.length; b += 1) {
      var button = plan.toolbar.buttons[b];
      var btnSpec = {
        text: button.text,
        icon: button.icon || "",
        action: button.action,
        checkable: !!button.checkable
      };
      if (button.shortcut) {
        btnSpec.shortcut = button.shortcut;
      }
      def.addButton(btnSpec);
      tally.buttons += 1;
    }
    ScriptManager.addToolbar(def);
  });

  return tally;
}

exports.apply = apply;
