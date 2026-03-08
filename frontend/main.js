// ============================================
// SonicGuard — Main Application Logic
// ============================================

// ---------- DOM Elements ----------
const sectionForm = document.getElementById('section-form');
const sectionLoading = document.getElementById('section-loading');
const sectionError = document.getElementById('section-error');
const sectionResults = document.getElementById('section-results');

const form = document.getElementById('compare-form');
const sourceAInput = document.getElementById('source-a');
const sourceBInput = document.getElementById('source-b');
const uploadAInput = document.getElementById('upload-a');
const uploadBInput = document.getElementById('upload-b');
const uploadALabel = document.getElementById('upload-a-label');
const uploadBLabel = document.getElementById('upload-b-label');
const btnCompare = document.getElementById('btn-compare');
const btnRetry = document.getElementById('btn-retry');
const btnNew = document.getElementById('btn-new');

const loadingProgressBar = document.getElementById('loading-progress-bar');
const loadingTimer = document.getElementById('loading-timer');
const errorMessage = document.getElementById('error-message');

// Results
const gaugeFill = document.getElementById('gauge-fill');
const gaugeValue = document.getElementById('gauge-value');
const verdictBanner = document.getElementById('verdict-banner');
const verdictIcon = document.getElementById('verdict-icon');
const verdictTitle = document.getElementById('verdict-title');
const verdictDescription = document.getElementById('verdict-description');
const metaElapsed = document.getElementById('meta-elapsed');
const metaDtw = document.getElementById('meta-dtw');
const metaFramesA = document.getElementById('meta-frames-a');
const metaFramesB = document.getElementById('meta-frames-b');

// ---------- Config ----------
const API_URL = '/api/compare';
const EXPECTED_DURATION = 45; // seconds
const FETCH_TIMEOUT = 120000; // 120s

// ---------- State ----------
let timerInterval = null;
let elapsedSeconds = 0;

// ---------- Verdicts ----------
const VERDICTS = {
    alta_similaridade: {
        icon: '🔴',
        title: 'Alta Similaridade',
        description: 'Há indícios significativos de plágio. Considere buscar orientação jurídica (Art. 7º, VIII — Lei 9.610/98).',
        class: 'verdict--high',
        gaugeColor: 'var(--color-high)',
    },
    media_similaridade: {
        icon: '🟡',
        title: 'Média Similaridade',
        description: 'Zona cinzenta — pode ser inspiração ou obra derivada. Recomendável uma perícia detalhada.',
        class: 'verdict--medium',
        gaugeColor: 'var(--color-medium)',
    },
    baixa_similaridade: {
        icon: '🟢',
        title: 'Baixa Similaridade',
        description: 'Não há indícios significativos de plágio. Similaridade dentro do esperado para o gênero.',
        class: 'verdict--low',
        gaugeColor: 'var(--color-low)',
    },
};

// ---------- Section Visibility ----------
function showSection(section) {
    [sectionForm, sectionLoading, sectionError, sectionResults].forEach(s => {
        s.classList.add('hidden');
    });
    section.classList.remove('hidden');
    section.style.animation = 'none';
    // Trigger reflow to restart animation
    void section.offsetWidth;
    section.style.animation = '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ---------- File Upload Handling ----------
function setupFileUpload(input, label, textInput) {
    input.addEventListener('change', () => {
        if (input.files.length > 0) {
            const file = input.files[0];
            label.classList.add('has-file');
            label.querySelector('.form__upload-text').textContent = `📎 ${file.name}`;
            // Disable text input when file is selected
            textInput.value = '';
            textInput.disabled = true;
        }
    });

    textInput.addEventListener('input', () => {
        if (textInput.value.trim()) {
            // Clear file when URL is typed
            input.value = '';
            label.classList.remove('has-file');
            label.querySelector('.form__upload-text').textContent = 'Arraste ou clique para enviar arquivo';
        }
        textInput.disabled = false;
    });

    // Drag & drop
    label.addEventListener('dragover', (e) => {
        e.preventDefault();
        label.classList.add('has-file');
    });

    label.addEventListener('dragleave', () => {
        if (!input.files.length) {
            label.classList.remove('has-file');
        }
    });

    label.addEventListener('drop', (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length) {
            input.files = e.dataTransfer.files;
            input.dispatchEvent(new Event('change'));
        }
    });
}

setupFileUpload(uploadAInput, uploadALabel, sourceAInput);
setupFileUpload(uploadBInput, uploadBLabel, sourceBInput);

// ---------- Timer ----------
function startTimer() {
    elapsedSeconds = 0;
    loadingTimer.textContent = '0s';
    loadingProgressBar.style.width = '0%';

    timerInterval = setInterval(() => {
        elapsedSeconds++;
        loadingTimer.textContent = `${elapsedSeconds}s`;

        // Progress bar — reaches ~90% at expected duration, then slows
        const progress = Math.min(95, (elapsedSeconds / EXPECTED_DURATION) * 90);
        loadingProgressBar.style.width = `${progress}%`;
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    loadingProgressBar.style.width = '100%';
}

// ---------- Validation ----------
function isValidYouTubeUrl(url) {
    return /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)[\w-]+/.test(url);
}

function getSourceInput(textInput, fileInput) {
    const url = textInput.value.trim();
    const file = fileInput.files[0];
    if (file) return { type: 'file', value: file };
    if (url) return { type: 'url', value: url };
    return null;
}

function validateInputs() {
    const sourceA = getSourceInput(sourceAInput, uploadAInput);
    const sourceB = getSourceInput(sourceBInput, uploadBInput);

    if (!sourceA || !sourceB) {
        return { valid: false, error: 'Preencha os dois campos — URL do YouTube ou arquivo de áudio.' };
    }

    if (sourceA.type === 'url' && !isValidYouTubeUrl(sourceA.value)) {
        return { valid: false, error: 'URL do Áudio Original não parece ser um link válido do YouTube.' };
    }

    if (sourceB.type === 'url' && !isValidYouTubeUrl(sourceB.value)) {
        return { valid: false, error: 'URL do Áudio Suspeito não parece ser um link válido do YouTube.' };
    }

    return { valid: true, sourceA, sourceB };
}

// ---------- API Call ----------
async function compareAudios(sourceA, sourceB) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT);

    try {
        let response;

        // If either source is a file, use FormData
        if (sourceA.type === 'file' || sourceB.type === 'file') {
            const formData = new FormData();
            if (sourceA.type === 'file') {
                formData.append('file_a', sourceA.value);
            } else {
                formData.append('source_a', sourceA.value);
            }
            if (sourceB.type === 'file') {
                formData.append('file_b', sourceB.value);
            } else {
                formData.append('source_b', sourceB.value);
            }

            response = await fetch(API_URL, {
                method: 'POST',
                body: formData,
                signal: controller.signal,
            });
        } else {
            // Both are URLs — send JSON
            response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_a: sourceA.value,
                    source_b: sourceB.value,
                }),
                signal: controller.signal,
            });
        }

        clearTimeout(timeout);

        if (!response.ok) {
            let errMsg = `Erro ${response.status}`;
            try {
                const errData = await response.json();
                errMsg = errData.detail || errData.message || errMsg;
            } catch {
                // Couldn't parse JSON error
            }
            throw new Error(errMsg);
        }

        return await response.json();
    } catch (err) {
        clearTimeout(timeout);
        if (err.name === 'AbortError') {
            throw new Error('A requisição excedeu o tempo limite (120s). Tente novamente.');
        }
        throw err;
    }
}

// ---------- Render Results ----------
function renderResults(data) {
    const scorePercent = Math.round(data.score * 100);
    const verdict = VERDICTS[data.verdict] || VERDICTS.baixa_similaridade;

    // Gauge animation
    const circumference = 2 * Math.PI * 85; // r=85
    const offset = circumference - (circumference * scorePercent / 100);

    // Add SVG gradient definition if not exists
    if (!document.getElementById('gauge-gradient')) {
        const svg = document.querySelector('.gauge__svg');
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
        gradient.id = 'gauge-gradient';
        gradient.setAttribute('x1', '0%');
        gradient.setAttribute('y1', '0%');
        gradient.setAttribute('x2', '100%');
        gradient.setAttribute('y2', '100%');

        // Set gradient colors based on verdict
        const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');

        if (data.verdict === 'alta_similaridade') {
            stop1.setAttribute('stop-color', '#ef4444');
            stop2.setAttribute('stop-color', '#f97316');
        } else if (data.verdict === 'media_similaridade') {
            stop1.setAttribute('stop-color', '#f59e0b');
            stop2.setAttribute('stop-color', '#eab308');
        } else {
            stop1.setAttribute('stop-color', '#22c55e');
            stop2.setAttribute('stop-color', '#10b981');
        }
        stop1.setAttribute('offset', '0%');
        stop2.setAttribute('offset', '100%');

        gradient.appendChild(stop1);
        gradient.appendChild(stop2);
        defs.appendChild(gradient);
        svg.insertBefore(defs, svg.firstChild);
    } else {
        // Update existing gradient colors
        const stops = document.querySelectorAll('#gauge-gradient stop');
        if (data.verdict === 'alta_similaridade') {
            stops[0].setAttribute('stop-color', '#ef4444');
            stops[1].setAttribute('stop-color', '#f97316');
        } else if (data.verdict === 'media_similaridade') {
            stops[0].setAttribute('stop-color', '#f59e0b');
            stops[1].setAttribute('stop-color', '#eab308');
        } else {
            stops[0].setAttribute('stop-color', '#22c55e');
            stops[1].setAttribute('stop-color', '#10b981');
        }
    }

    // Animate gauge value
    animateNumber(gaugeValue, 0, scorePercent, 1500, '%');

    // Set gauge fill
    requestAnimationFrame(() => {
        gaugeFill.style.strokeDashoffset = offset;
    });

    // Verdict
    verdictBanner.className = `verdict ${verdict.class}`;
    verdictIcon.textContent = verdict.icon;
    verdictTitle.textContent = verdict.title;
    verdictDescription.textContent = verdict.description;

    // Breakdown bars
    const dimensions = ['melodia', 'harmonia', 'ritmo', 'timbre'];
    dimensions.forEach(dim => {
        if (data.breakdown && data.breakdown[dim]) {
            const pct = Math.round(data.breakdown[dim].score * 100);
            const bar = document.getElementById(`bar-${dim}`);
            const val = document.getElementById(`value-${dim}`);

            animateNumber(val, 0, pct, 1200, '%');

            requestAnimationFrame(() => {
                bar.style.width = `${pct}%`;
            });
        }
    });

    // Meta
    metaElapsed.textContent = data.elapsed_seconds ? data.elapsed_seconds.toFixed(1) : '0';
    metaDtw.textContent = data.dtw_cost ? data.dtw_cost.toFixed(4) : '0';
    metaFramesA.textContent = data.frames_a || '0';
    metaFramesB.textContent = data.frames_b || '0';
}

// ---------- Number Animation ----------
function animateNumber(element, from, to, duration, suffix = '') {
    const start = performance.now();

    function update(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(from + (to - from) * eased);
        element.textContent = `${current}${suffix}`;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// ---------- Reset ----------
function resetForm() {
    sourceAInput.value = '';
    sourceBInput.value = '';
    sourceAInput.disabled = false;
    sourceBInput.disabled = false;
    uploadAInput.value = '';
    uploadBInput.value = '';
    uploadALabel.classList.remove('has-file');
    uploadBLabel.classList.remove('has-file');
    uploadALabel.querySelector('.form__upload-text').textContent = 'Arraste ou clique para enviar arquivo';
    uploadBLabel.querySelector('.form__upload-text').textContent = 'Arraste ou clique para enviar arquivo';

    // Reset gauge
    gaugeFill.style.strokeDashoffset = 534;
    gaugeValue.textContent = '0%';

    // Reset breakdown bars
    ['melodia', 'harmonia', 'ritmo', 'timbre'].forEach(dim => {
        document.getElementById(`bar-${dim}`).style.width = '0%';
        document.getElementById(`value-${dim}`).textContent = '0%';
    });

    btnCompare.disabled = false;
    showSection(sectionForm);
}

// ---------- Form Submit ----------
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const validation = validateInputs();
    if (!validation.valid) {
        alert(validation.error);
        return;
    }

    const { sourceA, sourceB } = validation;

    // Show loading
    btnCompare.disabled = true;
    showSection(sectionLoading);
    startTimer();

    try {
        const data = await compareAudios(sourceA, sourceB);
        stopTimer();
        renderResults(data);
        showSection(sectionResults);
    } catch (err) {
        stopTimer();
        errorMessage.textContent = err.message || 'Erro ao conectar com o servidor. Verifique se o backend está rodando.';
        showSection(sectionError);
    }
});

// ---------- Buttons ----------
btnRetry.addEventListener('click', () => {
    btnCompare.disabled = false;
    showSection(sectionForm);
});

btnNew.addEventListener('click', resetForm);

// ---------- Init ----------
console.log('🛡️ SonicGuard Frontend loaded');
