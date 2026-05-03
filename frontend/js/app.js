// Anime AI Agent - Frontend Application

let ws = null;
let currentProjectId = null;
let isLogCollapsed = true;

// ──────── WebSocket Connection ────────
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        updateStatus('connected', 'Agent Online');
        addLog('Connected to Anime AI Agent', 'success');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onerror = () => {
        updateStatus('error', 'Connection Error');
    };

    ws.onclose = () => {
        updateStatus('disconnected', 'Disconnected');
        addLog('Connection lost. Reconnecting...', 'warning');
        setTimeout(connectWebSocket, 3000);
    };

    // Ping every 30s
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
        }
    }, 30000);
}

// ──────── Message Handler ────────
function handleMessage(data) {
    switch (data.type) {
        case 'progress':
            handleProgress(data);
            break;
        case 'complete':
            handleComplete(data.result);
            break;
        case 'error':
            handleError(data);
            break;
        case 'pong':
            break;
    }
}

function handleProgress(data) {
    const { stage, step, progress, message, data: stageData } = data;

    // Update overall progress
    document.getElementById('overall-progress-bar').style.width = `${progress}%`;
    document.getElementById('progress-percent').textContent = `${Math.round(progress)}%`;
    document.getElementById('progress-message').textContent = message;

    // Update stage indicators
    updateStage(stage, step, progress);

    // Log
    addLog(`[${stage}] ${message}`, step === 'complete' ? 'success' : 'info');

    // Show details
    if (stageData) {
        showStageDetails(stage, stageData);
    }
}

function updateStage(stageName, step, progress) {
    const stages = ['text_analysis', 'storyboard', 'character_design', 'scene_generation', 'animation', 'video_assembly'];
    const stageIndex = stages.indexOf(stageName);

    stages.forEach((s, i) => {
        const el = document.getElementById(`stage-${s}`);
        if (!el) return;

        if (i < stageIndex) {
            el.className = 'stage complete';
            el.querySelector('.stage-status').textContent = 'Done';
        } else if (i === stageIndex) {
            if (step === 'complete') {
                el.className = 'stage complete';
                el.querySelector('.stage-status').textContent = 'Done';
            } else {
                el.className = 'stage active';
                el.querySelector('.stage-status').innerHTML = '<span class="spinner"></span> Running';
                const bar = el.querySelector('.stage-progress-bar');
                // Estimate inner progress
                const stageStart = (stageIndex / stages.length) * 100;
                const stageEnd = ((stageIndex + 1) / stages.length) * 100;
                const innerProgress = ((progress - stageStart) / (stageEnd - stageStart)) * 100;
                bar.style.width = `${Math.min(Math.max(innerProgress, 5), 100)}%`;
            }
        } else {
            el.className = 'stage';
            el.querySelector('.stage-status').textContent = 'Waiting';
        }
    });
}

function showStageDetails(stage, data) {
    const detailsSection = document.getElementById('details-section');
    detailsSection.classList.remove('hidden');

    if (stage === 'text_analysis' && data.analysis) {
        showAnalysis(data.analysis);
    } else if (stage === 'storyboard' && data.storyboard) {
        showStoryboard(data.storyboard);
    } else if (stage === 'character_design' && data.characters) {
        showCharacters(data.characters);
    } else if (stage === 'scene_generation' && data.scenes) {
        showScenes(data.scenes);
    }
}

// ──────── Detail Renderers ────────
function showAnalysis(analysis) {
    const card = document.getElementById('analysis-card');
    card.classList.remove('hidden');

    const content = document.getElementById('analysis-content');
    content.innerHTML = `
        <div class="analysis-grid">
            <div class="analysis-item">
                <label>Title</label>
                <div class="value">${escapeHtml(analysis.title)}</div>
            </div>
            <div class="analysis-item">
                <label>Genre</label>
                <div class="value">${escapeHtml(analysis.genre)}</div>
            </div>
            <div class="analysis-item">
                <label>Mood</label>
                <div class="value">${escapeHtml(analysis.mood)}</div>
            </div>
            <div class="analysis-item">
                <label>Themes</label>
                <div class="value">${(analysis.themes || []).map(t => escapeHtml(t)).join(', ')}</div>
            </div>
            <div class="analysis-item">
                <label>Setting</label>
                <div class="value">${escapeHtml(analysis.setting?.location || 'N/A')}</div>
            </div>
            <div class="analysis-item">
                <label>Characters</label>
                <div class="value">${(analysis.characters || []).map(c => escapeHtml(c.name)).join(', ')}</div>
            </div>
            <div class="analysis-item">
                <label>Scenes</label>
                <div class="value">${analysis.estimated_scenes || 'N/A'}</div>
            </div>
            <div class="analysis-item">
                <label>Atmosphere</label>
                <div class="value">${escapeHtml(analysis.setting?.atmosphere || 'N/A')}</div>
            </div>
        </div>
        <div class="analysis-item" style="margin-top: 12px;">
            <label>Summary</label>
            <div class="value" style="font-size: 14px; line-height: 1.6;">${escapeHtml(analysis.summary || '')}</div>
        </div>
    `;
}

function showStoryboard(storyboard) {
    const card = document.getElementById('storyboard-card');
    card.classList.remove('hidden');

    const content = document.getElementById('storyboard-content');
    const scenes = storyboard.scenes || [];

    content.innerHTML = `
        <div style="margin-bottom: 12px; color: var(--text-muted);">
            ${scenes.length} scenes | ${storyboard.total_duration || 0}s total duration
        </div>
        <div class="storyboard-timeline">
            ${scenes.map(scene => `
                <div class="storyboard-scene">
                    <div class="scene-num">${scene.scene_number || '?'}</div>
                    <div class="scene-details">
                        <h4>${escapeHtml(scene.title || 'Untitled Scene')}</h4>
                        <div class="meta">
                            ${escapeHtml(scene.camera || '')} | ${scene.duration || 0}s | ${escapeHtml(scene.mood || '')}
                        </div>
                        <div class="meta">${escapeHtml(scene.description || '')}</div>
                        ${scene.dialogue ? `<div class="dialogue-preview">"${escapeHtml(scene.dialogue)}"</div>` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function showCharacters(characters) {
    const card = document.getElementById('characters-card');
    card.classList.remove('hidden');

    const gallery = document.getElementById('characters-gallery');
    gallery.innerHTML = characters.map(char => {
        const imgSrc = char.images && char.images.length > 0
            ? `/api/project/${currentProjectId}/assets/characters/${char.name.toLowerCase().replace(/ /g, '_')}/${char.images[0].split('/').pop()}`
            : '';

        return `
            <div class="character-card">
                ${imgSrc ? `<img src="${imgSrc}" alt="${escapeHtml(char.name)}" onerror="this.style.display='none'">` : ''}
                <div class="char-info">
                    <div class="char-name">${escapeHtml(char.name)}</div>
                    <div class="char-role">${escapeHtml(char.description || '')}</div>
                </div>
            </div>
        `;
    }).join('');
}

function showScenes(scenes) {
    const card = document.getElementById('scenes-card');
    card.classList.remove('hidden');

    const gallery = document.getElementById('scenes-gallery');
    gallery.innerHTML = scenes.map(scene => {
        const bgFile = scene.background ? scene.background.split('/').pop() : '';
        const imgSrc = bgFile ? `/api/project/${currentProjectId}/assets/scenes/${bgFile}` : '';

        return `
            <div class="scene-card">
                ${imgSrc ? `<img src="${imgSrc}" alt="Scene ${scene.scene_number}" onerror="this.style.display='none'">` : ''}
                <div class="scene-info">
                    <div class="scene-title">Scene ${scene.scene_number}: ${escapeHtml(scene.title || '')}</div>
                    ${scene.dialogue ? `<div class="scene-dialogue">"${escapeHtml(scene.dialogue)}"</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ──────── Completion & Error Handlers ────────
function handleComplete(result) {
    addLog('Anime creation complete!', 'success');

    // Show result section
    document.getElementById('result-section').classList.remove('hidden');

    const video = document.getElementById('result-video');
    video.querySelector('source').src = `/api/project/${result.project_id}/video`;
    video.load();

    document.getElementById('result-info').innerHTML = `
        <div class="result-stat">
            <div class="stat-value">${result.scenes || 0}</div>
            <div class="stat-label">Scenes</div>
        </div>
        <div class="result-stat">
            <div class="stat-value">${result.characters || 0}</div>
            <div class="stat-label">Characters</div>
        </div>
        <div class="result-stat">
            <div class="stat-value">${result.duration || 0}s</div>
            <div class="stat-label">Duration</div>
        </div>
    `;

    // Update progress to 100%
    document.getElementById('overall-progress-bar').style.width = '100%';
    document.getElementById('progress-percent').textContent = '100%';
    document.getElementById('progress-message').textContent = 'Anime creation complete!';
}

function handleError(data) {
    addLog(`Error in ${data.stage}: ${data.message}`, 'error');

    document.getElementById('error-section').classList.remove('hidden');
    document.getElementById('error-message').textContent = data.message;
}

// ──────── Actions ────────
async function startCreation() {
    const text = document.getElementById('story-input').value.trim();
    if (!text) {
        alert('Please describe your anime story first!');
        return;
    }

    // Disable button
    const btn = document.getElementById('create-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Creating...';

    // Show pipeline, hide other sections
    document.getElementById('pipeline-section').classList.remove('hidden');
    document.getElementById('details-section').classList.remove('hidden');
    document.getElementById('result-section').classList.add('hidden');
    document.getElementById('error-section').classList.add('hidden');

    // Reset stages
    document.querySelectorAll('.stage').forEach(el => {
        el.className = 'stage';
        el.querySelector('.stage-status').textContent = 'Waiting';
        el.querySelector('.stage-progress-bar').style.width = '0%';
    });

    // Reset details
    ['analysis-card', 'storyboard-card', 'characters-card', 'scenes-card'].forEach(id => {
        document.getElementById(id).classList.add('hidden');
    });

    addLog('Starting anime creation...', 'info');

    try {
        const resp = await fetch('/api/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });

        const data = await resp.json();
        if (resp.ok) {
            currentProjectId = data.project_id;
            addLog(`Project started: ${data.project_id}`, 'success');
        } else {
            addLog(`Failed to start: ${data.error || 'Unknown error'}`, 'error');
            btn.disabled = false;
            btn.innerHTML = '<span class="btn-icon">&#x1F3AC;</span> Create Anime';
        }
    } catch (err) {
        addLog(`Request failed: ${err.message}`, 'error');
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">&#x1F3AC;</span> Create Anime';
    }
}

function loadExample() {
    document.getElementById('story-input').value = `In a world where ancient spirits roam hidden realms, a young girl named Sakura discovers she can see these spirits after finding a mysterious crystal pendant in her grandmother's attic. The pendant once belonged to a legendary spirit guardian who protected the barrier between the human world and the spirit realm.

When dark spirits begin breaking through the weakening barrier, Sakura must team up with Ren, a half-spirit boy who has been watching over the pendant for centuries, and Miko, a fierce spirit warrior cat who speaks in riddles. Together, they must journey to the five sacred shrines across Japan to restore the barrier's power.

Their journey takes them through the neon-lit streets of modern Tokyo, ancient bamboo forests shrouded in mist, floating islands above the clouds, an underwater crystal palace, and finally to the peak of a volcanic mountain where the final shrine awaits. Along the way, they face shadow creatures, solve ancient puzzles, and discover that Sakura's connection to the spirit world runs deeper than anyone imagined.`;
}

function downloadVideo() {
    if (currentProjectId) {
        window.open(`/api/project/${currentProjectId}/video`, '_blank');
    }
}

function createNew() {
    document.getElementById('input-section').scrollIntoView({ behavior: 'smooth' });
    document.getElementById('pipeline-section').classList.add('hidden');
    document.getElementById('result-section').classList.add('hidden');
    document.getElementById('error-section').classList.add('hidden');
    document.getElementById('details-section').classList.add('hidden');

    const btn = document.getElementById('create-btn');
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">&#x1F3AC;</span> Create Anime';

    document.getElementById('overall-progress-bar').style.width = '0%';
    document.getElementById('progress-percent').textContent = '0%';

    currentProjectId = null;
}

// ──────── Status & Logging ────────
function updateStatus(state, text) {
    const dot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');

    dot.className = 'status-dot';
    if (state === 'connected') dot.classList.add('connected');
    else if (state === 'error') dot.classList.add('error');

    statusText.textContent = text;
}

function addLog(message, type = 'info') {
    const content = document.getElementById('log-content');
    const time = new Date().toLocaleTimeString();

    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${time}] ${message}`;

    content.appendChild(entry);
    content.scrollTop = content.scrollHeight;
}

function toggleLog() {
    const panel = document.getElementById('log-panel');
    isLogCollapsed = !isLogCollapsed;
    panel.classList.toggle('collapsed', isLogCollapsed);
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ──────── Init ────────
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();

    // Start with log collapsed
    document.getElementById('log-panel').classList.add('collapsed');

    // Allow Ctrl+Enter to submit
    document.getElementById('story-input').addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            startCreation();
        }
    });
});
