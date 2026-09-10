/**
 * Apply each selected READ drawing pivot to its upstream PEG pivot.
 *
 * Workflow:
 * 1) Select one or more READ nodes.
 * 2) Run this script to copy each selected READ drawing pivot
 *    to that READ's upstream PEG pivot.
 */

function LP_use_drawing_pivot() {
    try {
        var readNodes = getSelectedReadNodes();
        if (!readNodes || readNodes.length === 0) {
            return;
        }

        var frameNumber = getCurrentFrame();

        scene.beginUndoRedoAccum("Apply Drawing Pivot To Upstream PEGs");
        try {
            var appliedCount = 0;
            var skippedCount = 0;

            for (var i = 0; i < readNodes.length; i++) {
                var readNode = readNodes[i];

                var drawingPivot = getDrawingPivotForReadNode(readNode, frameNumber);
                if (!drawingPivot) {
                    skippedCount += 1;
                    notifyInfo("Skipped (no valid drawing pivot on READ at current frame): " + readNode);
                    continue;
                }

                // Convert directly from drawing coordinates to peg pivot units.
                // This keeps pivot placement independent from the node position in scene.
                var pegPivot = convertPointToPegPivot(drawingPivot);
                if (!pegPivot) {
                    skippedCount += 1;
                    notifyInfo("Skipped (could not convert drawing pivot): " + readNode);
                    continue;
                }

                var pegNode = findUpstreamPeg(readNode, {});
                if (!pegNode) {
                    skippedCount += 1;
                    notifyInfo("Skipped (no upstream PEG): " + readNode);
                    continue;
                }

                var pivX = node.getAttr(pegNode, frameNumber, "pivot.x") || node.getAttr(pegNode, frameNumber, "PIVOT.X");
                var pivY = node.getAttr(pegNode, frameNumber, "pivot.y") || node.getAttr(pegNode, frameNumber, "PIVOT.Y");

                if (!pivX || !pivY) {
                    skippedCount += 1;
                    notifyInfo("Skipped (pivot attrs not found): " + pegNode + " (from " + readNode + ")");
                    continue;
                }

                pivX.setValue(pegPivot.x);
                pivY.setValue(pegPivot.y);
                appliedCount += 1;

                notifyInfo(
                    "Applied " + readNode + " -> " + pegNode
                    + " | drawingPivot=(" + drawingPivot.x + ", " + drawingPivot.y + ")"
                    + " | pegPivot=(" + pegPivot.x + ", " + pegPivot.y + ")"
                );
            }

            if (appliedCount === 0) {
                notifyWarn("No upstream PEG pivots were updated from the selected READ nodes.");
                return;
            }

            notifyInfo(
                "Applied drawing pivot to " + appliedCount + " upstream PEG(s)"
                + " | skipped=" + skippedCount
            );
        } finally {
            scene.endUndoRedoAccum();
        }
    } catch (error) {
        notifyWarn("LP_use_drawing_pivot failed: " + String(error));
    }
}


function getCurrentDrawingPivot() {
    if (typeof Tools === "undefined" || !Tools || typeof Tools.getToolSettings !== "function") {
        notifyInfo("Tools.getToolSettings is unavailable in this context.");
        return null;
    }

    var settings = Tools.getToolSettings();
    if (!settings || !settings.currentDrawing) {
        notifyInfo("No currentDrawing in tool settings.");
        return null;
    }

    if (typeof Drawing === "undefined" || !Drawing || typeof Drawing.getPivot !== "function") {
        notifyInfo("Drawing.getPivot is unavailable in this context.");
        return null;
    }

    var config = {
        drawing: settings.currentDrawing
    };

    var pivot = Drawing.getPivot(config);
    if (!pivot || pivot === false) {
        return null;
    }

    var px = Number(pivot.x);
    var py = Number(pivot.y);
    if (!isFinite(px) || !isFinite(py)) {
        return null;
    }

    return { x: px, y: py };
}


function getDrawingPivotForReadNode(readNode, frameNumber) {
    if (!readNode || node.type(readNode) !== "READ") {
        return null;
    }

    if (typeof Drawing === "undefined" || !Drawing || typeof Drawing.getPivot !== "function") {
        notifyInfo("Drawing.getPivot is unavailable in this context.");
        return null;
    }

    var pivot = null;
    try {
        pivot = Drawing.getPivot({
            drawing: {
                node: readNode,
                frame: frameNumber
            }
        });
    } catch (_e) {
        pivot = null;
    }

    if (!pivot || pivot === false) {
        return null;
    }

    var px = Number(pivot.x);
    var py = Number(pivot.y);
    if (!isFinite(px) || !isFinite(py)) {
        return null;
    }

    return { x: px, y: py };
}


function getSelectedReadNodes() {
    var count = selection.numberOfNodesSelected();
    if (count === 0) {
        notifyWarn("Select one or more READ nodes.");
        return null;
    }

    var reads = [];
    for (var i = 0; i < count; i++) {
        var nodePath = selection.selectedNode(i);
        if (!nodePath) {
            continue;
        }
        if (node.type(nodePath) === "READ") {
            reads.push(nodePath);
        }
    }

    if (reads.length === 0) {
        notifyWarn("No READ nodes found in selection.");
        return null;
    }

    return reads;
}


function findUpstreamPeg(startNode, visited) {
    if (!startNode) {
        return null;
    }
    if (visited[startNode]) {
        return null;
    }
    visited[startNode] = true;

    if (node.type(startNode) === "PEG") {
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


function getCurrentFrame() {
    try {
        return Number(frame.current());
    } catch (_e) {
        return 1;
    }
}


function convertPointToPegPivot(point) {
    var conv = getOglToFieldConversion();
    return {
        x: point.x / conv.resX,
        y: point.y / conv.resY
    };
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
        notifyInfo("No currentDrawing for mapping context.");
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
            notifyInfo("Invalid drawing box for proportional mapping: " + JSON.stringify(drawingRaw));
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
        notifyInfo("Invalid READ scene box for mapping: " + JSON.stringify(sceneRaw));
    }

    var readMatrix = null;
    try {
        readMatrix = node.getMatrix(readNode, frameNumber);
    } catch (_e3) {
        readMatrix = null;
    }

    if (readMatrix) {
        notifyInfo("Using READ matrix fallback for drawing->scene conversion.");
        return {
            mode: "matrix",
            readMatrix: readMatrix
        };
    }

    notifyInfo("No valid drawing->scene mapping path available.");
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
        notifyInfo("PEG matrix unavailable, using scene point directly as fallback.");
        return {
            x: Number(scenePoint.x),
            y: Number(scenePoint.y)
        };
    }

    var inv = invertMatrix(world);
    if (!inv) {
        notifyInfo("Could not invert PEG matrix, using scene point directly as fallback.");
        return {
            x: Number(scenePoint.x),
            y: Number(scenePoint.y)
        };
    }

    var local = transformPoint(inv, scenePoint);
    if (!local) {
        notifyInfo("Could not transform scene point with inverse matrix, using scene point directly as fallback.");
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
        notifyInfo("Inverse-matrix transform returned invalid coordinates, using scene point directly as fallback.");
        return {
            x: Number(scenePoint.x),
            y: Number(scenePoint.y)
        };
    }

    var normalized = normalizeLikelyUnscaledPegPivot(lx, ly, scenePoint);
    if (normalized.applied) {
        notifyInfo(
            "Applied legacy unit-scale fallback for PEG pivot."
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


function numberOrNaN(value) {
    var n = Number(value);
    return isFinite(n) ? n : Number.NaN;
}


function notifyWarn(message) {
    var text = "[UseDrawingPivot] " + message;
    try {
        MessageBox.warning(text);
    } catch (_e) {
        try {
            MessageLog.trace(text);
        } catch (_e2) {}
    }
}


function notifyInfo(message) {
    try {
        MessageLog.trace("[UseDrawingPivot] " + message);
    } catch (_e) {}
}
