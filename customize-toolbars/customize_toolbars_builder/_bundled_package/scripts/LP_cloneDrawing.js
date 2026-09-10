/**
 * Script to make a copy (selection) "clone only drawing" for nodes(not in a group) and backdrop, replace 
 * on "B" the F name. When you hold Shift while running, you can modify the text patterns to find and replace.
 * The script needs to be on the Node View
 * @software  Toon Boom Harmony v 24.0.2 (23443)
 * @author Lilian Penzo
 * @version 1.0
 */

// Default replacement patterns
var NAME_TO_CHANGE = "F_";
var NEW_CHANGED_NAME = "B_";
var NUMBER_TO_REMOVE = "_1";

/**
 * Main function to clone selected nodes and rename them by replacing F_ with B_ (or custom patterns)
 * Also renames selected backdrops with the same pattern
 */
function LP_cloneDrawing() {
    scene.beginUndoRedoAccum("LP_cloneDrawing");
    MessageLog.trace("___________________________Starting script: LP_cloneDrawing___________________________");
    
    // Save view/group information before opening any dialogs
    var savedView = view.currentView();
    var savedGroup = view.group(savedView);
    
    if (!savedGroup) {
        MessageBox.warning('<font color="red"><b>Could not determine current view or group.<br>Make sure you are in the Node View.</b></font>', 0, 1, 0);
        scene.endUndoRedoAccum();
        return;
    }

    // Set up replacement patterns, potentially customized by user
    var nameToChange = NAME_TO_CHANGE;
    var newChangedName = NEW_CHANGED_NAME;

    // Allow custom values if Shift is pressed
    if (KeyModifiers.IsShiftPressed()) {
        var changed_names = choose_text_interface(nameToChange, newChangedName);
        
        if (changed_names) {
            nameToChange = changed_names.name_to_find;
            newChangedName = changed_names.name_to_replace;
            MessageLog.trace("Using custom values - Find: '" + nameToChange + "', Replace: '" + newChangedName + "'");
        }
    }
    
    // Get and validate selected nodes
    var list_sel_nodes_to_clone = selection.selectedNodes();
    
    if (list_sel_nodes_to_clone.length === 0) {
        MessageBox.warning('<font color="red"><b>' + "<br>No nodes selected</br>"+'</b></font>', 0, 1, 0);
        scene.endUndoRedoAccum();
        return;
    }
    
    // Clone the selected nodes
    callFunctionCloneNodeView(list_sel_nodes_to_clone);
    
    // Get the newly cloned nodes (they will be selected)
    var list_sel_nodes_cloned = selection.selectedNodes();
    
    if (list_sel_nodes_cloned.length === 0) {
        MessageBox.warning('<font color="red"><b>' + "<br>No nodes were cloned</br>"+'</b></font>', 0, 1, 0);
        scene.endUndoRedoAccum();
        return;
    }
    
    // Process each cloned node
    for (var i = 0; i < list_sel_nodes_cloned.length; i++) {
        var nodePath = list_sel_nodes_cloned[i];
        var node_name = node.getName(nodePath);
        
        // Create the new name by replacing the pattern
        var new_node_name = node_name.replace(nameToChange, newChangedName);
        MessageLog.trace("Renaming node: '" + node_name + "' to '" + new_node_name + "'");

        // Rename the node
        renamer_nodes(nodePath, new_node_name);
    }
    
    // Process backdrops with the same pattern
    renamer_selected_backdrops(nameToChange, newChangedName, savedGroup);

    MessageLog.trace("___________________________Finishing script: LP_cloneDrawing___________________________");
    scene.endUndoRedoAccum();
}

/**
 * Clones the selected nodes using the "Clone Drawings Only" action
 * 
 * @param {Array} list_nodes - Array of node paths to clone
 */
function callFunctionCloneNodeView(list_nodes) {
    Action.perform("onActionCloneElement_DrawingsOnly()", "Node View", list_nodes);
}

/**
 * Safely renames a node with error handling and suffix removal
 * 
 * @param {string} target_path - Path of the node to rename
 * @param {string} new_name - New name for the node
 * @returns {boolean} - True if successful, false otherwise
 */
function renamer_nodes(target_path, new_name) {
    // Check if target exists
    var target_name = node.getName(target_path);
    if (target_name === "") {
        MessageLog.trace("WARNING: Can't rename, target doesn't exist: " + target_path);
        return false;
    }
    
    // Remove NUMBER_TO_REMOVE from the end of new_name if it exists there
    if (NUMBER_TO_REMOVE) {
        var suffixPosition = new_name.lastIndexOf(NUMBER_TO_REMOVE);
        if (suffixPosition !== -1 && suffixPosition === new_name.length - NUMBER_TO_REMOVE.length) {
            new_name = new_name.substring(0, suffixPosition);
        }
    }

    // Get the parent node path
    var root = node.parentNode(target_path);
    var full_new_name = root + "/" + new_name;

    // Check if a node with the new name already exists
    var exists_name = node.getName(full_new_name);
    if (exists_name !== "") {
        MessageLog.trace("WARNING: Can't rename: " + target_path + " to: " + full_new_name + " - name already used");
        return false;
    }

    // Rename the node
    var rename_result = node.rename(target_path, new_name);
    if (!rename_result) {
        MessageLog.trace("WARNING: Error renaming: " + target_path + " to: " + full_new_name);
        return false;
    }
    
    return true;
}

/**
 * Creates a dialog interface for the user to input custom find/replace text
 * 
 * @param {string} name_to_find - Default text to find
 * @param {string} name_to_replace - Default replacement text
 * @returns {Object} - Object with name_to_find and name_to_replace properties
 */
function choose_text_interface(name_to_find, name_to_replace) {
    var choose_text_dialog = new Dialog;
    choose_text_dialog.title = "Find Clone Text to Replace";

    var inputLineFind = new LineEdit();
    inputLineFind.label = "Find";
    inputLineFind.text = name_to_find;
    choose_text_dialog.add(inputLineFind);

    var inputLineReplace = new LineEdit();
    inputLineReplace.label = "Replace";
    inputLineReplace.text = name_to_replace;
    choose_text_dialog.add(inputLineReplace);

    var results = choose_text_dialog.exec();
    
    if (!results) {
        // If dialog was cancelled, return the original values
        return {
            name_to_find: name_to_find,
            name_to_replace: name_to_replace
        };
    }

    // Return object with new values
    return {
        name_to_find: inputLineFind.text,
        name_to_replace: inputLineReplace.text
    };
}

/**
 * Renames selected backdrops by replacing text in their titles
 * Handles case-sensitive replacement and preserves uppercase/lowercase
 * 
 * @param {string} name_to_change - Text to find in backdrop titles
 * @param {string} new_name - Text to replace with
 * @param {Object} saved_group - Group context for backdrop operations
 * @returns {boolean} - True if any backdrops were modified, false otherwise
 */
function renamer_selected_backdrops(name_to_change, new_name, saved_group) {
    var current_group = saved_group;
    
    // Validate group context
    if (!current_group) {
        var my_view = view.currentView();
        current_group = view.group(my_view);
    }
    
    if (!current_group) {
        MessageBox.warning('<font color="red"><b>Could not determine current view or group.<br>Make sure you are in the Node View.</b></font>', 0, 1, 0);
        return false;
    }

    // Get all backdrops in the current group
    var all_backdrops = Backdrop.backdrops(current_group);
    if (!all_backdrops || all_backdrops.length === 0) {
        return false;
    }

    // Get selected backdrops
    var list_backdrops_selected = selection.selectedBackdrops();
    if (list_backdrops_selected.length === 0) {
        return false;
    }

    // Track changes
    var any_backdrop_modified = false;
    var backdrop_with_name_found = false;

    // Process each selected backdrop
    for (var n = 0; n < list_backdrops_selected.length; n++) {
        var selected_backdrop = list_backdrops_selected[n];
        var title_backdrop = selected_backdrop.title.text;
        
        // Case-insensitive search
        var title_lower = title_backdrop.toLowerCase();
        var search_lower = name_to_change.toLowerCase();
        var indexOf_result = title_lower.indexOf(search_lower);
        
        if (indexOf_result !== -1) {
            backdrop_with_name_found = true;
            
            // Check if original title was uppercase for the matching part
            var matched_part = title_backdrop.substring(indexOf_result, indexOf_result + name_to_change.length);
            var is_uppercase = matched_part === matched_part.toUpperCase();
            
            // Choose replacement text based on case of original
            var replacement = is_uppercase ? new_name.toUpperCase() : new_name;
            
            // Create custom replace function for case-insensitive replacement
            function replaceIgnoreCase(str, find, replace) {
                var regex = new RegExp(find.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'), 'i');
                return str.replace(regex, replace);
            }
            
            // Replace the text
            var new_backdrop_title = replaceIgnoreCase(title_backdrop, name_to_change, replacement);
            selected_backdrop.title.text = new_backdrop_title;
            
            // Find and update this backdrop in the full list
            for (var i = 0; i < all_backdrops.length; i++) {
                if (all_backdrops[i].position.x === selected_backdrop.position.x && 
                    all_backdrops[i].position.y === selected_backdrop.position.y) {
                    all_backdrops[i] = selected_backdrop;
                    any_backdrop_modified = true;
                    break;
                }
            }
        }
    }

    // Show warning if no backdrops matched the pattern
    if (list_backdrops_selected.length > 0 && !backdrop_with_name_found) {
        MessageBox.warning('<font color="orange"><b>' + "Selected backdrops don't contain '" + 
                          name_to_change + "' in their title" + "</b></font>", 0, 1, 0);
    }

    // Apply changes if any were made
    if (any_backdrop_modified) {
        try {
            Backdrop.setBackdrops(current_group, all_backdrops);
            return true;
        } catch (error) {
            MessageLog.trace("ERROR updating backdrops: " + error);
            return false;
        }
    }
    
    return false;
}
