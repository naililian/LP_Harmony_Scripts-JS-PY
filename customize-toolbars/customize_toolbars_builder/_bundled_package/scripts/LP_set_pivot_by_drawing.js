/**
 * Set a PEG pivot to the center of selected drawing strokes, or to the center
 * of downstream drawings when a PEG is selected.
 *
 * This implementation stays fully in Harmony's JS runtime because drawing-tool
 * selection context is not reliably available through the Python bridge.
 */

function LP_set_pivot_by_drawing() {
    try {
        MessageLog.trace("[Pivot] LP_set_pivot_by_drawing loaded from: " + getCurrentScriptPathForLog());
        var selected = getSingleSelectedReadOrPegNode();
        if (!selected) {
            return;
        }

        if (isPegNode(selected)) {
            setSelectedPegPivotToDownstreamCenter(selected);
            return;
        }

        var readNode = selected;
        var pegNode = findUpstreamPeg(readNode, {});
        if (!pegNode) {
            MessageBox.warning("No upstream PEG found for the selected READ node.");
            return;
        }

        var strokes = getSelectedLayerStrokes();
        var drawingBBox = null;
        var drawingPivot = null;
        var sourceLabel = "selected-stroke";

        if (strokes.length) {
            drawingBBox = getSelectionBoundingBox(strokes);
        } else {
            drawingBBox = getCurrentDrawingBoundingBox();
            sourceLabel = "drawing-bounds";

            // Drawing.query.getBox can be empty for invalid/empty drawings.
            // In that case, fallback to the drawing pivot set manually in Harmony.
            if (!drawingBBox) {
                drawingPivot = getCurrentDrawingPivot();
                if (drawingPivot) {
                    sourceLabel = "drawing-pivot";
                }
            }
        }

        if (!drawingBBox && !drawingPivot) {
            MessageBox.warning("Could not compute drawing bounds, and no valid drawing pivot was found.");
            return;
        }

        var centerX = drawingPivot ? drawingPivot.x : (drawingBBox.left + drawingBBox.right) / 2;
        var centerY = drawingPivot ? drawingPivot.y : (drawingBBox.top + drawingBBox.bottom) / 2;
        if (!isFinite(centerX) || !isFinite(centerY)) {
            MessageLog.trace("[Pivot] Invalid bbox center values: x=" + centerX + " y=" + centerY);
            MessageBox.warning("Drawing bounding box center is invalid. Open the drawing and ensure visible vector strokes exist.");
            return;
        }

        // Convert directly from drawing coordinates to peg pivot units.
        // This keeps pivot placement independent from the node position in scene.
        var pivot = convertPointToPegPivot({
            x: centerX,
            y: centerY
        });

        if (!pivot || !isFinite(pivot.x) || !isFinite(pivot.y)) {
            MessageLog.trace("[Pivot] Invalid converted pivot: " + JSON.stringify(pivot));
            MessageBox.warning("Converted peg pivot is invalid. Aborting to avoid writing NaN values.");
            return;
        }

        var frameNumber = getCurrentFrame();
        scene.beginUndoRedoAccum("Set Peg Pivot From Selected Strokes");
        try {
            if (!setPegPivotAttrs(pegNode, frameNumber, pivot.x, pivot.y)) {
                return;
            }

            MessageLog.trace(
                "[Pivot] Applied " + sourceLabel + " center to " + pegNode
                + "  drawingCenter=(" + centerX + ", " + centerY + ")"
                + "  pegPivot=(" + pivot.x + ", " + pivot.y + ")"
            );
        } finally {
            scene.endUndoRedoAccum();
        }
    } catch (error) {
        MessageLog.trace("[Pivot] Script failed: " + String(error));
        MessageBox.warning("LP_set_pivot_by_drawing failed: " + String(error));
    }
}


function getSingleSelectedReadOrPegNode() {
    var count = selection.numberOfNodesSelected();
    if (count === 0) {
        MessageBox.warning("Select exactly one READ or PEG node.");
        return null;
    }
    if (count > 1) {
        MessageBox.warning("Multiple nodes selected. Select exactly one READ or PEG node.");
        return null;
    }

    var nodePath = selection.selectedNode(0);
    var nodeType = nodePath ? node.type(nodePath) : "";
    if (!nodePath || (nodeType !== "READ" && !isPegType(nodeType))) {
        MessageBox.warning("The selected node must be a READ or PEG node.");
        MessageLog.trace("[Pivot] Unsupported selected node type: " + nodeType + " path=" + nodePath);
        return null;
    }
    return nodePath;
}


function isPegNode(nodePath) {
    if (!nodePath) {
        return false;
    }
    try {
        return isPegType(node.type(nodePath));
    } catch (_e) {
        return false;
    }
}


function isPegType(nodeType) {
    return String(nodeType || "").toUpperCase() === "PEG";
}


function getCurrentScriptPathForLog() {
    try {
        if (typeof __file__ !== "undefined") {
            return String(__file__);
        }
    } catch (_e) {}
    return "<unknown>";
}


function setSelectedPegPivotToDownstreamCenter(pegNode) {
    var frameNumber = getCurrentFrame();
    var reads = collectDownstreamReadNodes(pegNode);
    if (!reads.length) {
        MessageBox.warning("No downstream READ nodes found for selected PEG.");
        return;
    }

    var visualUnionData = getReadNodesUnionBox(reads, frameNumber);
    if (visualUnionData.bbox) {
        var centerScene = {
            x: (visualUnionData.bbox.left + visualUnionData.bbox.right) / 2,
            y: (visualUnionData.bbox.bottom + visualUnionData.bbox.top) / 2
        };

        var pivotLocal = scenePointToPegLocal(pegNode, frameNumber, centerScene);
        if (pivotLocal && isFinite(pivotLocal.x) && isFinite(pivotLocal.y)) {
            applyPegPivotValues(pegNode, frameNumber, pivotLocal.x, pivotLocal.y, {
                sourceLabel: "downstream-visual-bounds",
                readCount: reads.length,
                usedBoxes: visualUnionData.used,
                centerLabel: "sceneCenter",
                center: centerScene
            }, "Set Selected Peg Pivot From Visual BBox");
            return;
        }

        MessageLog.trace("[Pivot] Visual bbox conversion failed, falling back to downstream drawing bbox: " + JSON.stringify(pivotLocal));
    }

    var unionData = getReadNodesDrawingUnionBox(reads, frameNumber);
    if (!unionData.bbox) {
        MessageBox.warning("Could not compute drawing bounds from downstream READ nodes.");
        return;
    }

    var centerDrawing = {
        x: (unionData.bbox.left + unionData.bbox.right) / 2,
        y: (unionData.bbox.bottom + unionData.bbox.top) / 2
    };

    if (!isFinite(centerDrawing.x) || !isFinite(centerDrawing.y)) {
        MessageLog.trace("[Pivot] Invalid downstream bbox center: " + JSON.stringify(unionData.bbox));
        MessageBox.warning("Downstream drawing bounding box center is invalid.");
        return;
    }

    applyPivotTargetToPeg(pegNode, frameNumber, {
        point: centerDrawing,
        sourceLabel: "downstream-drawing-bounds",
        readCount: reads.length,
        usedBoxes: unionData.used
    }, "Set Selected Peg Pivot To Center");
}


function applyPegPivotValues(pegNode, frameNumber, x, y, logData, undoLabel) {
    if (!isFinite(x) || !isFinite(y)) {
        MessageBox.warning("Converted PEG pivot is invalid. Aborting to avoid writing NaN values.");
        return false;
    }

    scene.beginUndoRedoAccum(undoLabel || "Set Selected Peg Pivot To Center");
    try {
        if (!setPegPivotAttrs(pegNode, frameNumber, x, y)) {
            return false;
        }
    } finally {
        scene.endUndoRedoAccum();
    }

    var centerLabel = logData && logData.centerLabel ? logData.centerLabel : "center";
    var center = logData && logData.center ? logData.center : null;
    MessageLog.trace(
        "[Pivot] Applied " + ((logData && logData.sourceLabel) || "pivot") + " center to selected PEG " + pegNode
        + (logData && logData.readCount !== undefined ? " reads=" + logData.readCount : "")
        + (logData && logData.usedBoxes !== undefined ? " usedBoxes=" + logData.usedBoxes : "")
        + (center ? " " + centerLabel + "=(" + center.x + ", " + center.y + ")" : "")
        + " pegPivot=(" + x + ", " + y + ")"
    );
    return true;
}


function getCurrentDrawingPivotTarget() {
    var strokes = getSelectedLayerStrokes();
    var drawingBBox = null;
    var drawingPivot = null;
    var sourceLabel = "selected-stroke";

    if (strokes.length) {
        drawingBBox = getSelectionBoundingBox(strokes);
    } else {
        drawingBBox = getCurrentDrawingBoundingBox();
        sourceLabel = "current-drawing-bounds";

        if (!drawingBBox) {
            drawingPivot = getCurrentDrawingPivot();
            if (drawingPivot) {
                sourceLabel = "current-drawing-pivot";
            }
        }
    }

    if (!drawingBBox && !drawingPivot) {
        return null;
    }

    var point = drawingPivot ? drawingPivot : {
        x: (drawingBBox.left + drawingBBox.right) / 2,
        y: (drawingBBox.top + drawingBBox.bottom) / 2
    };

    if (!isFinite(point.x) || !isFinite(point.y)) {
        MessageLog.trace("[Pivot] Invalid current drawing target: " + JSON.stringify(point));
        return null;
    }

    return {
        point: point,
        sourceLabel: sourceLabel
    };
}


function applyPivotTargetToPeg(pegNode, frameNumber, target, undoLabel) {
    var point = target && target.point;
    if (!point || !isFinite(point.x) || !isFinite(point.y)) {
        MessageBox.warning("Drawing bounding box center is invalid. Open the drawing and ensure visible vector strokes exist.");
        return false;
    }

    // Match the READ-selection path exactly: drawing coordinates become PEG
    // pivot units directly, independent of the node's scene transform.
    var pivot = convertPointToPegPivot(point);
    if (!pivot || !isFinite(pivot.x) || !isFinite(pivot.y)) {
        MessageLog.trace("[Pivot] Invalid downstream converted pivot: " + JSON.stringify(pivot));
        MessageBox.warning("Converted PEG pivot is invalid. Aborting to avoid writing NaN values.");
        return false;
    }

    scene.beginUndoRedoAccum(undoLabel || "Set Selected Peg Pivot To Center");
    try {
        if (!setPegPivotAttrs(pegNode, frameNumber, pivot.x, pivot.y)) {
            return false;
        }
    } finally {
        scene.endUndoRedoAccum();
    }

    MessageLog.trace(
        "[Pivot] Applied " + (target.sourceLabel || "drawing") + " center to selected PEG " + pegNode
        + (target.readCount !== undefined ? " reads=" + target.readCount : "")
        + (target.usedBoxes !== undefined ? " usedBoxes=" + target.usedBoxes : "")
        + " drawingCenter=(" + point.x + ", " + point.y + ")"
        + " pegPivot=(" + pivot.x + ", " + pivot.y + ")"
    );
    return true;
}


function setPegPivotAttrs(pegNode, frameNumber, x, y) {
    var pivX = node.getAttr(pegNode, frameNumber, "pivot.x") || node.getAttr(pegNode, frameNumber, "PIVOT.X");
    var pivY = node.getAttr(pegNode, frameNumber, "pivot.y") || node.getAttr(pegNode, frameNumber, "PIVOT.Y");
    if (!pivX || !pivY) {
        MessageBox.warning("Pivot attributes not found on PEG: " + pegNode);
        return false;
    }

    pivX.setValue(x);
    pivY.setValue(y);
    return true;
}


function collectDownstreamReadNodes(startNode) {
    var visited = {};
    var readSet = {};
    var result = [];
    var stack = [startNode];

    while (stack.length) {
        var current = stack.pop();
        if (!current || visited[current]) {
            continue;
        }
        visited[current] = true;

        var type = "";
        try {
            type = node.type(current);
        } catch (_e1) {
            type = "";
        }

        if (type === "READ") {
            if (!readSet[current]) {
                readSet[current] = true;
                result.push(current);
            }
            continue;
        }

        var outPorts = 0;
        try {
            outPorts = node.numberOfOutputPorts(current);
        } catch (_e2) {
            outPorts = 0;
        }

        for (var p = 0; p < outPorts; p++) {
            var links = 0;
            try {
                links = node.numberOfOutputLinks(current, p);
            } catch (_e3) {
                links = 0;
            }

            for (var l = 0; l < links; l++) {
                var dst = "";
                try {
                    dst = node.dstNode(current, p, l);
                } catch (_e4) {
                    dst = "";
                }
                if (dst && !visited[dst]) {
                    stack.push(dst);
                }
            }
        }
    }

    return result;
}


function getReadNodesUnionBox(readNodes, frameNumber) {
    var bbox = null;
    var used = 0;

    for (var i = 0; i < readNodes.length; i++) {
        var parsed = getReadNodeSceneBox(readNodes[i], frameNumber);
        if (!parsed) {
            MessageLog.trace("[Pivot] No usable bbox for downstream READ: " + readNodes[i]);
            continue;
        }

        used += 1;
        if (!bbox) {
            bbox = {
                left: parsed.left,
                right: parsed.right,
                bottom: parsed.bottom,
                top: parsed.top
            };
        } else {
            bbox.left = Math.min(bbox.left, parsed.left);
            bbox.right = Math.max(bbox.right, parsed.right);
            bbox.bottom = Math.min(bbox.bottom, parsed.bottom);
            bbox.top = Math.max(bbox.top, parsed.top);
        }
    }

    return {
        bbox: bbox,
        used: used
    };
}


function getReadNodesDrawingUnionBox(readNodes, frameNumber) {
    var bbox = null;
    var used = 0;

    for (var i = 0; i < readNodes.length; i++) {
        var parsed = getReadDrawingQueryBox(readNodes[i], frameNumber);
        if (!parsed) {
            MessageLog.trace("[Pivot] No usable drawing bbox for downstream READ: " + readNodes[i]);
            continue;
        }

        used += 1;
        if (!bbox) {
            bbox = {
                left: parsed.left,
                right: parsed.right,
                bottom: parsed.bottom,
                top: parsed.top
            };
        } else {
            bbox.left = Math.min(bbox.left, parsed.left);
            bbox.right = Math.max(bbox.right, parsed.right);
            bbox.bottom = Math.min(bbox.bottom, parsed.bottom);
            bbox.top = Math.max(bbox.top, parsed.top);
        }
    }

    return {
        bbox: bbox,
        used: used
    };
}


function getReadDrawingQueryBox(readNode, frameNumber) {
    if (typeof Drawing === "undefined" || !Drawing || !Drawing.query || typeof Drawing.query.getBox !== "function") {
        MessageLog.trace("[Pivot] Drawing.query.getBox is unavailable.");
        return null;
    }

    var drawingBox = null;
    for (var art = 0; art < 4; art++) {
        var raw = null;
        try {
            raw = Drawing.query.getBox({
                drawing: {
                    node: readNode,
                    frame: frameNumber
                },
                art: art
            });
        } catch (_e) {
            raw = null;
        }

        var parsed = parseDrawingQueryBox(raw);
        if (!parsed) {
            continue;
        }

        if (!drawingBox) {
            drawingBox = parsed;
        } else {
            drawingBox.left = Math.min(drawingBox.left, parsed.left);
            drawingBox.right = Math.max(drawingBox.right, parsed.right);
            drawingBox.bottom = Math.min(drawingBox.bottom, parsed.bottom);
            drawingBox.top = Math.max(drawingBox.top, parsed.top);
        }
    }

    if (drawingBox) {
        MessageLog.trace(
            "[Pivot] Drawing bbox for " + readNode
            + " drawing=(" + drawingBox.left + "," + drawingBox.bottom + ")-(" + drawingBox.right + "," + drawingBox.top + ")"
        );
    }

    return drawingBox;
}


function getReadNodeSceneBox(readNode, frameNumber) {
    var raw = null;
    try {
        raw = node.getBox(readNode, frameNumber);
    } catch (_e1) {
        raw = null;
    }

    var parsed = parseBox(raw);
    if (parsed) {
        return parsed;
    }

    MessageLog.trace("[Pivot] node.getBox failed for READ, trying Drawing.query.getBox: " + readNode + " raw=" + JSON.stringify(raw));
    return getReadDrawingQuerySceneBox(readNode, frameNumber);
}


function getReadDrawingQuerySceneBox(readNode, frameNumber) {
    if (typeof Drawing === "undefined" || !Drawing || !Drawing.query || typeof Drawing.query.getBox !== "function") {
        MessageLog.trace("[Pivot] Drawing.query.getBox is unavailable.");
        return null;
    }

    var drawingBox = null;
    for (var art = 0; art < 4; art++) {
        var raw = null;
        try {
            raw = Drawing.query.getBox({
                drawing: {
                    node: readNode,
                    frame: frameNumber
                },
                art: art
            });
        } catch (_e) {
            raw = null;
        }

        var parsed = parseDrawingQueryBox(raw);
        if (!parsed) {
            continue;
        }

        if (!drawingBox) {
            drawingBox = parsed;
        } else {
            drawingBox.left = Math.min(drawingBox.left, parsed.left);
            drawingBox.right = Math.max(drawingBox.right, parsed.right);
            drawingBox.bottom = Math.min(drawingBox.bottom, parsed.bottom);
            drawingBox.top = Math.max(drawingBox.top, parsed.top);
        }
    }

    if (!drawingBox) {
        return null;
    }

    var sceneCorners = [];
    var corners = [
        { x: drawingBox.left, y: drawingBox.bottom },
        { x: drawingBox.right, y: drawingBox.bottom },
        { x: drawingBox.right, y: drawingBox.top },
        { x: drawingBox.left, y: drawingBox.top }
    ];

    var readMatrix = null;
    try {
        readMatrix = node.getMatrix(readNode, frameNumber);
    } catch (_e2) {
        readMatrix = null;
    }

    for (var i = 0; i < corners.length; i++) {
        var fieldPoint = drawingQueryPointToField(corners[i]);
        var scenePoint = fieldPoint;

        if (readMatrix) {
            var transformed = transformPoint(readMatrix, fieldPoint);
            if (transformed && transformed.x !== undefined && transformed.y !== undefined) {
                scenePoint = {
                    x: Number(transformed.x),
                    y: Number(transformed.y)
                };
            }
        }

        if (isFinite(scenePoint.x) && isFinite(scenePoint.y)) {
            sceneCorners.push(scenePoint);
        }
    }

    if (!sceneCorners.length) {
        return null;
    }

    var sceneBox = {
        left: sceneCorners[0].x,
        right: sceneCorners[0].x,
        bottom: sceneCorners[0].y,
        top: sceneCorners[0].y
    };

    for (var c = 1; c < sceneCorners.length; c++) {
        sceneBox.left = Math.min(sceneBox.left, sceneCorners[c].x);
        sceneBox.right = Math.max(sceneBox.right, sceneCorners[c].x);
        sceneBox.bottom = Math.min(sceneBox.bottom, sceneCorners[c].y);
        sceneBox.top = Math.max(sceneBox.top, sceneCorners[c].y);
    }

    MessageLog.trace(
        "[Pivot] Drawing.query fallback bbox for " + readNode
        + " drawing=(" + drawingBox.left + "," + drawingBox.bottom + ")-(" + drawingBox.right + "," + drawingBox.top + ")"
        + " scene=(" + sceneBox.left + "," + sceneBox.bottom + ")-(" + sceneBox.right + "," + sceneBox.top + ")"
    );

    return sceneBox;
}


function parseDrawingQueryBox(rawBox) {
    if (!rawBox || rawBox === false || rawBox.empty) {
        return null;
    }

    var left = numberOrNaN(rawBox.x0);
    var right = numberOrNaN(rawBox.x1);
    var bottom = numberOrNaN(rawBox.y0);
    var top = numberOrNaN(rawBox.y1);

    if (!isFinite(left)) {
        left = numberOrNaN(rawBox.left);
    }
    if (!isFinite(right)) {
        right = numberOrNaN(rawBox.right);
    }
    if (!isFinite(bottom)) {
        bottom = numberOrNaN(rawBox.bottom);
    }
    if (!isFinite(top)) {
        top = numberOrNaN(rawBox.top);
    }

    if (!isFinite(left) || !isFinite(right) || !isFinite(bottom) || !isFinite(top)) {
        MessageLog.trace("[Pivot] Drawing.query.getBox returned invalid READ bounds: " + JSON.stringify(rawBox));
        return null;
    }

    var minX = Math.min(left, right);
    var maxX = Math.max(left, right);
    var minY = Math.min(bottom, top);
    var maxY = Math.max(bottom, top);

    return {
        left: minX,
        right: maxX,
        bottom: minY,
        top: maxY
    };
}


function drawingQueryPointToField(point) {
    var oglX = Number(point.x) / 1875;
    var oglY = Number(point.y) / 1875;

    var fieldX = oglX;
    var fieldY = oglY;

    try {
        if (scene && typeof scene.fromOGLX === "function") {
            fieldX = Number(scene.fromOGLX(oglX));
        }
    } catch (_e1) {}

    try {
        if (scene && typeof scene.fromOGLY === "function") {
            fieldY = Number(scene.fromOGLY(oglY));
        }
    } catch (_e2) {}

    return {
        x: isFinite(fieldX) ? fieldX : oglX,
        y: isFinite(fieldY) ? fieldY : oglY
    };
}


function findUpstreamPeg(startNode, visited) {
    if (!startNode) {
        return null;
    }
    if (visited[startNode]) {
        return null;
    }
    visited[startNode] = true;

    if (isPegNode(startNode)) {
        return startNode;
    }

    var inputCount = node.numberOfInputPorts(startNode);
    for (var i = 0; i < inputCount; i++) {
        var upstream = node.srcNode(startNode, i);
        if (!upstream || upstream === "") {
            continue;
        }
        var found = findUpstreamPeg(upstream, visited);
        if (found) {
            return found;
        }
    }

    return null;
}


function getSelectedLayerStrokes() {
    var settings = Tools.getToolSettings();
    if (!settings || !settings.currentDrawing) {
        MessageLog.trace("[Pivot] No current drawing in tool settings.");
        return [];
    }

    var config = {
        drawing: settings.currentDrawing,
        art: settings.activeArt
    };

    var selectionData = Drawing.selection.get(config);
    if (!selectionData || !selectionData.selectedLayers) {
        MessageLog.trace("[Pivot] No selectedLayers found in drawing selection.");
        return [];
    }

    var strokes = [];
    var selectedLayers = selectionData.selectedLayers;
    for (var key in selectedLayers) {
        var layerConfig = {
            drawing: settings.currentDrawing,
            art: settings.activeArt,
            layers: [selectedLayers[key]]
        };
        var layerDescription = Drawing.query.getLayerStrokes(layerConfig);
        var layers = layerDescription && layerDescription.layers ? layerDescription.layers : [];
        for (var layerIndex in layers) {
            var layer = layers[layerIndex];
            if (layer && layer.strokes) {
                strokes = strokes.concat(layer.strokes);
            }
        }
    }

    return strokes;
}


function getSelectionBoundingBox(strokes) {
    if (!strokes || !strokes.length) {
        return null;
    }

    var bbox = {
        top: Number.NEGATIVE_INFINITY,
        left: Number.POSITIVE_INFINITY,
        bottom: Number.POSITIVE_INFINITY,
        right: Number.NEGATIVE_INFINITY
    };

    for (var s = 0; s < strokes.length; s++) {
        var points = strokes[s] && strokes[s].path ? strokes[s].path : [];
        for (var p = 0; p < points.length; p++) {
            var point = points[p];
            bbox.left = Math.min(bbox.left, point.x);
            bbox.right = Math.max(bbox.right, point.x);
            bbox.bottom = Math.min(bbox.bottom, point.y);
            bbox.top = Math.max(bbox.top, point.y);
        }
    }

    if (!isFinite(bbox.left) || !isFinite(bbox.right) || !isFinite(bbox.bottom) || !isFinite(bbox.top)) {
        return null;
    }

    return bbox;
}


function getCurrentDrawingBoundingBox() {
    var settings = Tools.getToolSettings();
    if (!settings || !settings.currentDrawing) {
        MessageLog.trace("[Pivot] No current drawing available for full drawing bounds.");
        return null;
    }

    var config = {
        drawing: settings.currentDrawing,
        art: settings.activeArt
    };

    var bounds = Drawing.query.getBox(config);
    if (!bounds) {
        return null;
    }

    var left = numberOrNaN(bounds.x0);
    var right = numberOrNaN(bounds.x1);
    var top = numberOrNaN(bounds.y1);
    var bottom = numberOrNaN(bounds.y0);

    // Fallback for API variants exposing left/right/top/bottom.
    if (!isFinite(left)) {
        left = numberOrNaN(bounds.left);
    }
    if (!isFinite(right)) {
        right = numberOrNaN(bounds.right);
    }
    if (!isFinite(top)) {
        top = numberOrNaN(bounds.top);
    }
    if (!isFinite(bottom)) {
        bottom = numberOrNaN(bounds.bottom);
    }

    if (!isFinite(left) || !isFinite(right) || !isFinite(top) || !isFinite(bottom)) {
        MessageLog.trace("[Pivot] Drawing.query.getBox returned invalid bounds: " + JSON.stringify(bounds));
        return null;
    }

    return {
        left: left,
        right: right,
        top: top,
        bottom: bottom
    };
}


function getCurrentFrame() {
    try {
        return Number(frame.current());
    } catch (_e) {
        return 1;
    }
}


function parseBox(rawBox) {
    if (!rawBox) {
        return null;
    }

    var left = numberOrNaN(rawBox.x0);
    var right = numberOrNaN(rawBox.x1);
    var bottom = numberOrNaN(rawBox.y0);
    var top = numberOrNaN(rawBox.y1);

    if (!isFinite(left)) {
        left = numberOrNaN(rawBox.left);
    }
    if (!isFinite(right)) {
        right = numberOrNaN(rawBox.right);
    }
    if (!isFinite(bottom)) {
        bottom = numberOrNaN(rawBox.bottom);
    }
    if (!isFinite(top)) {
        top = numberOrNaN(rawBox.top);
    }

    if (!isFinite(left) || !isFinite(right) || !isFinite(bottom) || !isFinite(top)) {
        return null;
    }

    return {
        left: left,
        right: right,
        bottom: bottom,
        top: top
    };
}


function getDrawingToSceneMappingContext(readNode, frameNumber) {
    var settings = Tools.getToolSettings();
    if (!settings || !settings.currentDrawing) {
        MessageLog.trace("[Pivot] No currentDrawing for mapping context.");
    }

    var drawingBox = null;
    var drawingRaw = null;
    if (settings && settings.currentDrawing) {
        try {
            drawingRaw = Drawing.query.getBox({ drawing: settings.currentDrawing, art: settings.activeArt });
        } catch (_e1) {
            drawingRaw = null;
        }
        drawingBox = parseBox(drawingRaw);
        if (!drawingBox) {
            MessageLog.trace("[Pivot] Invalid drawing box for proportional mapping: " + JSON.stringify(drawingRaw));
        }
    }

    var sceneRaw = null;
    try {
        sceneRaw = node.getBox(readNode, frameNumber);
    } catch (_e2) {
        sceneRaw = null;
    }
    var sceneBox = parseBox(sceneRaw);
    if (sceneBox && drawingBox) {
        return {
            mode: "box",
            drawing: drawingBox,
            scene: sceneBox
        };
    }

    if (!sceneBox) {
        MessageLog.trace("[Pivot] Invalid READ scene box for mapping: " + JSON.stringify(sceneRaw));
    }

    var readMatrix = null;
    try {
        readMatrix = node.getMatrix(readNode, frameNumber);
    } catch (_e3) {
        readMatrix = null;
    }

    if (readMatrix) {
        MessageLog.trace("[Pivot] Using READ matrix fallback for drawing->scene conversion.");
        return {
            mode: "matrix",
            readMatrix: readMatrix
        };
    }

    MessageLog.trace("[Pivot] No valid drawing->scene mapping path available.");
    return null;
}


function mapDrawingPointToScene(drawingPoint, mappingContext) {
    if (mappingContext.mode === "matrix" && mappingContext.readMatrix) {
        var mapped = transformPoint(mappingContext.readMatrix, drawingPoint);
        if (!mapped || mapped.x === undefined || mapped.y === undefined) {
            return null;
        }
        return {
            x: Number(mapped.x),
            y: Number(mapped.y)
        };
    }

    if (mappingContext.mode !== "box") {
        return null;
    }

    var d = mappingContext.drawing;
    var s = mappingContext.scene;

    var dWidth = d.right - d.left;
    var dHeight = d.top - d.bottom;
    if (!isFinite(dWidth) || !isFinite(dHeight) || dWidth === 0 || dHeight === 0) {
        return null;
    }

    var u = (drawingPoint.x - d.left) / dWidth;
    var v = (drawingPoint.y - d.bottom) / dHeight;

    return {
        x: s.left + u * (s.right - s.left),
        y: s.bottom + v * (s.top - s.bottom)
    };
}


function invertMatrix(matrixObj) {
    if (!matrixObj) {
        return null;
    }

    try {
        if (typeof matrixObj.inverse === "function") {
            var inv = matrixObj.inverse();
            if (inv) {
                return inv;
            }
        }
    } catch (_e1) {}

    try {
        if (typeof matrixObj.inverted === "function") {
            return matrixObj.inverted();
        }
    } catch (_e2) {}

    try {
        if (typeof matrixObj.getInverse === "function") {
            return matrixObj.getInverse();
        }
    } catch (_e3) {}

    try {
        if (typeof matrixObj.get_inverse === "function") {
            return matrixObj.get_inverse();
        }
    } catch (_e4) {}

    try {
        if (typeof matrixObj.inv === "function") {
            return matrixObj.inv();
        }
    } catch (_e5) {}

    return null;
}


function transformPoint(matrixObj, point) {
    if (!matrixObj) {
        return null;
    }

    var p3 = null;
    try {
        p3 = new Point3d(point.x, point.y, 0.0);
    } catch (_e0) {
        try {
            p3 = new Point3D(point.x, point.y, 0.0);
        } catch (_e00) {
            try {
                p3 = new Vector3d(point.x, point.y, 0.0);
            } catch (_e000) {
                p3 = { x: point.x, y: point.y, z: 0.0 };
            }
        }
    }

    try {
        if (typeof matrixObj.multiply === "function") {
            return matrixObj.multiply(p3);
        }
    } catch (_e1) {}

    try {
        if (typeof matrixObj.map === "function") {
            return matrixObj.map(p3);
        }
    } catch (_e2) {}

    try {
        if (typeof matrixObj.transform === "function") {
            return matrixObj.transform(p3);
        }
    } catch (_e3) {}

    try {
        if (typeof matrixObj.apply === "function") {
            return matrixObj.apply(p3);
        }
    } catch (_e4) {}

    try {
        if (typeof matrixObj.mult === "function") {
            return matrixObj.mult(p3);
        }
    } catch (_e5) {}

    return null;
}


function scenePointToPegLocal(pegNode, frameNumber, scenePoint) {
    var world = null;
    try {
        world = node.getMatrix(pegNode, frameNumber);
    } catch (_e) {
        world = null;
    }
    if (!world) {
        MessageLog.trace("[Pivot] PEG matrix unavailable, using scene point directly as fallback.");
        return {
            x: Number(scenePoint.x),
            y: Number(scenePoint.y)
        };
    }

    var inv = invertMatrix(world);
    if (!inv) {
        MessageLog.trace("[Pivot] Could not invert PEG matrix, using scene point directly as fallback.");
        return {
            x: Number(scenePoint.x),
            y: Number(scenePoint.y)
        };
    }

    var local = transformPoint(inv, scenePoint);
    if (!local) {
        MessageLog.trace("[Pivot] Could not transform scene point with inverse matrix, using scene point directly as fallback.");
        return {
            x: Number(scenePoint.x),
            y: Number(scenePoint.y)
        };
    }

    var lx = Number(local.x);
    var ly = Number(local.y);

    if ((!isFinite(lx) || !isFinite(ly)) && local.length && local.length >= 2) {
        lx = Number(local[0]);
        ly = Number(local[1]);
    }

    if (!isFinite(lx) || !isFinite(ly)) {
        MessageLog.trace("[Pivot] Inverse-matrix transform returned invalid coordinates, using scene point directly as fallback.");
        return {
            x: Number(scenePoint.x),
            y: Number(scenePoint.y)
        };
    }

    var normalized = normalizeLikelyUnscaledPegPivot(lx, ly, scenePoint);
    if (normalized.applied) {
        MessageLog.trace(
            "[Pivot] Applied legacy unit-scale fallback for PEG pivot."
            + " scene=(" + scenePoint.x + ", " + scenePoint.y + ")"
            + " localRaw=(" + lx + ", " + ly + ")"
            + " localScaled=(" + normalized.x + ", " + normalized.y + ")"
        );
    }

    return {
        x: normalized.x,
        y: normalized.y
    };
}


function normalizeLikelyUnscaledPegPivot(localX, localY, scenePoint) {
    var sx = Number(scenePoint && scenePoint.x);
    var sy = Number(scenePoint && scenePoint.y);

    if (!isFinite(localX) || !isFinite(localY) || !isFinite(sx) || !isFinite(sy)) {
        return { x: localX, y: localY, applied: false };
    }

    var sameAsScene = Math.abs(localX - sx) < 1e-6 && Math.abs(localY - sy) < 1e-6;
    var looksTooLarge = Math.abs(localX) > 50 || Math.abs(localY) > 50;
    var closeToScene = Math.abs(localX - sx) < 25 && Math.abs(localY - sy) < 25;

    if (sameAsScene && looksTooLarge) {
        var conv = getOglToFieldConversion();
        return {
            x: sx / conv.resX,
            y: sy / conv.resY,
            applied: true
        };
    }

    // Some Harmony contexts return transformed values still expressed in
    // drawing/OGL-like units. If values are very large, normalize using the
    // same scene conversion rule.
    if (looksTooLarge && closeToScene) {
        var conv2 = getOglToFieldConversion();
        return {
            x: localX / conv2.resX,
            y: localY / conv2.resY,
            applied: true
        };
    }

    return { x: localX, y: localY, applied: false };
}


function getOglToFieldConversion() {
    var aspect = getSceneAspectXY();
    var resY = 156.25;
    var resX = resY * (aspect.x / aspect.y);

    if (!isFinite(resX) || resX === 0) {
        resX = 208.33333333333334;
    }
    if (!isFinite(resY) || resY === 0) {
        resY = 156.25;
    }

    return {
        resX: resX,
        resY: resY
    };
}


function getSceneAspectXY() {
    var ax = Number.NaN;
    var ay = Number.NaN;

    try {
        if (scene && scene.aspect) {
            ax = Number(scene.aspect.x);
            ay = Number(scene.aspect.y);
        }
    } catch (_e1) {}

    try {
        if ((!isFinite(ax) || !isFinite(ay)) && scene && typeof scene.aspectRatioX === "function" && typeof scene.aspectRatioY === "function") {
            ax = Number(scene.aspectRatioX());
            ay = Number(scene.aspectRatioY());
        }
    } catch (_e2) {}

    try {
        if ((!isFinite(ax) || !isFinite(ay)) && scene && typeof scene.unitsAspectRatioX === "function" && typeof scene.unitsAspectRatioY === "function") {
            ax = Number(scene.unitsAspectRatioX());
            ay = Number(scene.unitsAspectRatioY());
        }
    } catch (_e3) {}

    if (!isFinite(ax) || !isFinite(ay) || ay === 0) {
        ax = 4;
        ay = 3;
    }

    return {
        x: ax,
        y: ay
    };
}


function getCurrentDrawingPivot() {
    var settings = Tools.getToolSettings();
    if (!settings || !settings.currentDrawing) {
        MessageLog.trace("[Pivot] No current drawing available for drawing pivot.");
        return null;
    }

    if (typeof Drawing === "undefined" || !Drawing || typeof Drawing.getPivot !== "function") {
        MessageLog.trace("[Pivot] Drawing.getPivot is unavailable in this context.");
        return null;
    }

    var pivot = Drawing.getPivot({ drawing: settings.currentDrawing });
    if (!pivot || pivot === false) {
        return null;
    }

    var px = numberOrNaN(pivot.x);
    var py = numberOrNaN(pivot.y);
    if (!isFinite(px) || !isFinite(py)) {
        return null;
    }

    return {
        x: px,
        y: py
    };
}


function convertPointToPegPivot(point) {
    var conv = getOglToFieldConversion();
    return {
        x: point.x / conv.resX,
        y: point.y / conv.resY,
        drawingX: point.x,
        drawingY: point.y
    };
}


function numberOrNaN(value) {
    var n = Number(value);
    return isFinite(n) ? n : Number.NaN;
}
