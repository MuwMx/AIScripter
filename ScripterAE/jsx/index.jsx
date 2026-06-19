




function forceCloseUndoGroups() {
    
    for (var i = 0; i < 5; i++) {
        try {
            app.endUndoGroup();
        } catch (e) {
            
        }
    }
}

var MyScripterAI = {
    
    
    getProjectPath: function() {
        try {
            if (!app.project.file) return "null";
            
            var rawName = app.project.file.name.replace(/\.aep$/i, "");
            var projName = rawName;
            
            
            try { 
                projName = decodeURI(rawName); 
            } catch(e) {}
            
            var projPath = app.project.file.parent.fsName.replace(/\\/g, '\\\\');
            return '{"path": "' + projPath + '", "name": "' + projName + '"}';
        } catch (e) {
            return "null"; 
        }
    },

    
    exportLayer: function(inputFolder, fileName) {
        var comp = app.project.activeItem;
        
        if (!comp || !(comp instanceof CompItem)) return '{"error": "Select a composition!"}';
        if (comp.selectedLayers.length === 0) return '{"error": "Select a layer!"}';

        var layer = comp.selectedLayers[0];
        
        var outDir = new Folder(inputFolder);
        if (!outDir.exists) outDir.create();

        var tempOutPath = outDir.fsName + "/" + fileName;
        var fileOut = new File(tempOutPath);
        if (fileOut.exists) fileOut.remove();

        var tempComp; 
        forceCloseUndoGroups(); 
        
        app.beginUndoGroup("Export for AI");
        try {
            tempComp = comp.duplicate();
            tempComp.name = "AI_Temp_Render";
            var tempLayer = tempComp.layer(layer.index);

            for (var i = 1; i <= tempComp.numLayers; i++) {
                tempComp.layer(i).enabled = false;
            }
            tempLayer.enabled = true;

            
            var waStart = tempLayer.inPoint;
            var waDuration = tempLayer.outPoint - tempLayer.inPoint;

            
            if (waStart < 0) waStart = 0;
            if (waStart > tempComp.duration) waStart = tempComp.duration;

            
            
            if (waStart + waDuration > tempComp.duration) {
                waDuration = tempComp.duration - waStart;
            }

            
            if (waDuration < tempComp.frameDuration) {
                waDuration = tempComp.frameDuration;
            }

            
            tempComp.workAreaStart = waStart;
            tempComp.workAreaDuration = waDuration;

            var rqItem = app.project.renderQueue.items.add(tempComp);
            var om = rqItem.outputModule(1);
            om.file = fileOut; 
        } catch (e) {
            app.endUndoGroup();
            return '{"error": "' + e.toString().replace(/"/g, '\\"') + '"}';
        }
        app.endUndoGroup(); 

        try {
            app.project.renderQueue.render();
        } catch (e) {
            return '{"error": "' + e.toString().replace(/"/g, '\\"') + '"}';
        }

        app.beginUndoGroup("Export for AI - Cleanup");
        try {
            if (tempComp) tempComp.remove();
            app.project.renderQueue.showWindow(false);
            comp.openInViewer(); 

            
            var safeInputPath = fileOut.fsName.replace(/\\/g, '\\\\');
            
            
            return '{"status": "success", "inputPath": "' + safeInputPath + '", "inPoint": ' + layer.inPoint + ', "fps": ' + comp.frameRate + '}';
        } catch (e) {
            return '{"error": "' + e.toString().replace(/"/g, '\\"') + '"}';
        } finally {
            app.endUndoGroup();
        }
    },

    
    importResult: function(filePath, inPoint) {
        var comp = app.project.activeItem;
        if (!comp) return "error";

        var layerName = "";
        
        forceCloseUndoGroups(); 
        app.beginUndoGroup("Import AI Result");
        try {
            var io = new ImportOptions(new File(filePath));
            var importedItem = app.project.importFile(io);
            
            var newLayer = comp.layers.add(importedItem);
            if (comp.selectedLayers.length > 1) {
                newLayer.moveBefore(comp.selectedLayers[1]);
            }
            
            newLayer.startTime = parseFloat(inPoint);
            layerName = newLayer.name;
        } catch (e) {
            return "error";
        } finally {
            app.endUndoGroup();
        }
        return layerName;
    },

    
    applyTimeRemap: function(layerName, jsonPath) {
        var comp = app.project.activeItem;
        var layer = comp.layer(layerName);
        if (!layer) return;

        var jsonFile = new File(jsonPath);
        if (!jsonFile.open("r")) return;
        var content = jsonFile.read();
        jsonFile.close();

        var data = JSON.parse(content);
        var frames = data.frames;
        var fps = data.original_fps;

        forceCloseUndoGroups();
        app.beginUndoGroup("Apply AI Time Remap");
        try {
            layer.timeRemapEnabled = true;
            var trProp = layer.property("Time Remap");
            
            while (trProp.numKeys > 0) { trProp.removeKey(1); }

            for (var i = 0; i < frames.length; i++) {
                var originalFrameIndex = frames[i];
                var newTime = originalFrameIndex / fps;
                var sourceTime = i / fps;
                
                var keyIndex = trProp.addKey(newTime);
                trProp.setValueAtKey(keyIndex, sourceTime);
                trProp.setInterpolationTypeAtKey(keyIndex, KeyframeInterpolationType.HOLD, KeyframeInterpolationType.HOLD);
            }
        } catch (e) {
            
        } finally {
            app.endUndoGroup();
        }
    },
};