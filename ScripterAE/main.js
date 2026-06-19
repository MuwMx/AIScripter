const csInterface = new CSInterface();
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Функция показа кастомного уведомления вместо системного алерта
function showNotification(msg, type = 'error') {
    const snack = document.getElementById('snackbar');
    snack.innerText = msg;
    
    // Настройка цвета под Material 3 варнинги
    if (type === 'success') {
        snack.style.backgroundColor = 'var(--primary)';
        snack.style.color = 'var(--on-primary)';
    } else {
        snack.style.backgroundColor = 'var(--error)';
        snack.style.color = '#381e70';
    }
    
    snack.classList.add('show');
    setTimeout(() => { snack.classList.remove('show'); }, 3500);
}

// Фикс NotAllowedError: копирование через временный буфер (100% работает в AE)
function copyLogs() {
    const logsBox = document.getElementById('logsBox');
    if (!logsBox) return;
    
    const textToCopy = logsBox.innerText; 
    
    if (textToCopy.trim() === "" || textToCopy.includes("Waiting for tasks...")) {
        showNotification("No logs available to copy", "error");
        return;
    }

    // Создаем временную textarea для обхода ограничений безопасности CEF
    const textarea = document.createElement('textarea');
    textarea.value = textToCopy;
    textarea.style.position = 'fixed'; // Избегаем прокрутки страницы
    document.body.appendChild(textarea);
    textarea.select();
    
    try {
        document.execCommand('copy');
        showNotification("Logs copied to clipboard!", "success");
    } catch (err) {
        showNotification("Failed to copy logs", "error");
    }
    
    document.body.removeChild(textarea);
}

function evalScript(script) {
    return new Promise((resolve) => {
        csInterface.evalScript(script, (res) => resolve(res));
    });
}

function setStatus(msg, progress = null) {
    document.getElementById('status-text').innerText = msg;
    if (progress !== null) {
        document.getElementById('progress-fill').style.width = progress + '%';
    }
}

function toggleButtons(disabled) {
    document.getElementById('btn-run').disabled = disabled;
    document.getElementById('clearCacheBtn').disabled = disabled;
}

// Функции для логгера
function addLog(msg, type = '') {
    const box = document.getElementById('logsBox');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `> ${msg}`;
    box.appendChild(entry);
    box.scrollTop = box.scrollHeight; // Автоскролл вниз
}

function clearLogs() {
    document.getElementById('logsBox').innerHTML = '';
}

// 1. КОНВЕЙЕР (ОЧЕРЕДЬ ЗАДАЧ)
async function runPipeline() {
    // Собираем включенные задачи
    const tasks = [];
    if (document.getElementById('toggle-clean').checked) tasks.push('clean');
    if (document.getElementById('toggle-rife').checked) tasks.push('rife');
    if (document.getElementById('toggle-depth').checked) tasks.push('depth');
    if (document.getElementById('toggle-bg').checked) tasks.push('bg');

    if (tasks.length === 0) {
    showNotification("Select at least one module from the pipeline!", "error");
    return;
    }

    toggleButtons(true);
    clearLogs();
    setStatus("Pipeline started...", 0);
    
    // Выполняем задачи последовательно
    for (let i = 0; i < tasks.length; i++) {
        const task = tasks[i];
        addLog(`--- STARTING TASK [${task.toUpperCase()}] (${i+1}/${tasks.length}) ---`, 'system');
        
        try {
            await executeSingleTask(task);
            addLog(`Task [${task.toUpperCase()}] completed successfully.`, 'success');
        } catch (err) {
            setStatus(`Pipeline aborted on [${task.toUpperCase()}]`, 0);
            addLog(`CRITICAL ERROR: ${err.message}`, 'error');
            toggleButtons(false);
            return; // Прерываем конвейер при ошибке
        }
    }

    setStatus("All Pipeline tasks finished!", 100);
    addLog("--- PIPELINE COMPLETE ---", 'system');
    toggleButtons(false);
}

// 2. ИСПОЛНИТЕЛЬ ОДНОЙ ЗАДАЧИ (Обернут в Promise)
function executeSingleTask(taskType) {
    return new Promise(async (resolve, reject) => {
        try {
            setStatus(`[${taskType.toUpperCase()}] Checking project...`);
            let projDataStr = await evalScript('MyScripterAI.getProjectPath()');
            
           if (projDataStr === "null") {
            showNotification("Save the project (Ctrl+S) first!", "error");
            return reject(new Error("Project not saved"));
            }
            
            let projData = JSON.parse(projDataStr);
            let inputDir = path.join(projData.path, `${projData.name}_Input`);
            let outputDir = path.join(projData.path, `${projData.name}_Output`);

            if (!fs.existsSync(inputDir)) fs.mkdirSync(inputDir);
            if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir);

            let files = fs.existsSync(outputDir) ? fs.readdirSync(outputDir) : [];
            let num = files.length + 1;
            let ext = taskType === 'bg' ? 'mov' : 'mp4';
            let outFileName = `AIScripter_${num}_${taskType}_output.${ext}`;
            let outputVideo = path.join(outputDir, outFileName);
            let inFileName = `chunk_${Date.now()}.mp4`;

            // Экспорт из AE
            setStatus(`[${taskType.toUpperCase()}] Exporting layer...`, 5);
            addLog(`Exporting layer to: ${inFileName}`);
            let safeInputDir = inputDir.replace(/\\/g, '/');
            let aeResponse = await evalScript(`MyScripterAI.exportLayer('${safeInputDir}', '${inFileName}')`);
            let data = JSON.parse(aeResponse);


            if (data.error) {
                showNotification(data.error, "error");
                return reject(new Error("AE Export Failed: " + data.error));
            }

            // Настройка Python
            const roamingPath = csInterface.getSystemPath(SystemPath.USER_DATA);
            const backendDir = path.join(roamingPath, 'MyScripterAE');
            const pythonExe = path.join(backendDir, 'python.exe');
            const backendMain = path.join(backendDir, 'backend', 'main.py');
            const inputVideo = data.inputPath;

            let finalInput = path.resolve(inputVideo);
            let finalOutput = path.resolve(outputVideo);

            if (process.platform === 'win32') {
                if (finalInput[1] === ':') finalInput = finalInput[0].toUpperCase() + finalInput.slice(1);
                if (finalOutput[1] === ':') finalOutput = finalOutput[0].toUpperCase() + finalOutput.slice(1);
            }

            let args = [backendMain, taskType, '--input', inputVideo, '--output', outputVideo];

            if (taskType === 'rife') {
                args.push('--scale', document.getElementById('rife-scale').value);
            } else if (taskType === 'clean') {
                const jsonOut = path.join(outputDir, `AIScripter_${num}_frames.json`);
                args.push('--json', jsonOut, '--threshold', document.getElementById('clean-thresh').value);
            } else if (taskType === 'depth') {
                args.push('--size', document.getElementById('depth-size').value);
            } else if (taskType === 'bg') {
                args.push('--weight', 'birefnet_finetuned_toonout.pth');
            }

            // Запуск Python
            setStatus(`[${taskType.toUpperCase()}] AI Processing...`, 20);
            addLog(`Starting Python Engine for ${taskType.toUpperCase()}...`);
            
            const pyProcess = spawn(pythonExe, args);

            // Перехват логов
            pyProcess.stderr.on('data', (chunk) => {
                const text = chunk.toString().trim();
                if(text) addLog(text);
                
                const match = text.match(/(\d+)%/);
                if (match) setStatus(`[${taskType.toUpperCase()}] Processing: ${match[1]}%`, match[1]);
            });

            pyProcess.stdout.on('data', (chunk) => {
                const text = chunk.toString().trim();
                if(text) addLog(text);
            });

            // Ожидание завершения
            pyProcess.on('close', async (code) => {
                if (code === 0) {
                    setStatus(`[${taskType.toUpperCase()}] Importing result...`, 95);
                    addLog(`Importing ${outFileName} back to timeline...`);
                    
                    const safeOutVideo = outputVideo.replace(/\\/g, '/');
                    let layerName = await evalScript(`MyScripterAI.importResult('${safeOutVideo}', ${data.inPoint})`);
                    
                    if (taskType === 'clean') {
                        const safeJson = path.join(outputDir, `AIScripter_${num}_frames.json`).replace(/\\/g, '/');
                        await evalScript(`MyScripterAI.applyTimeRemap('${layerName}', '${safeJson}')`);
                    }
                    
                    if (fs.existsSync(inputVideo)) {
                        fs.unlinkSync(inputVideo); // Удаляем инпут
                    }
                    resolve(); // Успех, пускаем очередь дальше
                } else {
                    reject(new Error(`Python Engine crashed with code ${code}`));
                }
            });

        } catch (err) {
            reject(err);
        }
    });
}

// 3. ОЧИСТКА КЭША ПО КЛИКУ НА КОРЗИНУ
async function clearCache() {
    setStatus("Purging AE memory...", 0);
    await evalScript('app.purge(PurgeTarget.ALL_CACHES)');
    setStatus("AE Memory fully purged!", 100);
    addLog("After Effects memory and disk cache successfully cleared.", "success");
    
    
    let projData = JSON.parse(projDataStr);
    let inputDir = path.join(projData.path, `${projData.name}_Input`);
    let outputDir = path.join(projData.path, `${projData.name}_Output`);
    
    let deletedCount = 0;
    [inputDir, outputDir].forEach(dir => {
        if (fs.existsSync(dir)) {
            let files = fs.readdirSync(dir);
            files.forEach(file => {
                fs.unlinkSync(path.join(dir, file));
                deletedCount++;
            });
        }
    });
    
    setStatus("Cache cleared.", 0);
    addLog(`Cache cleared. Removed ${deletedCount} temporary files.`, 'success');
}
