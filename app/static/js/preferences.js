/* ─────────────────────────────────────────────
   File: app/static/js/preferences.js
   App Version: 2026.03.14 | File Version: 1.1.0
   Last Modified: 2026-03-18
   ───────────────────────────────────────────── */

// ── Price range slider ──────────────────────────────────────
function updatePriceRange(el) {
    const minS = document.getElementById('minPriceSlider');
    const maxS = document.getElementById('maxPriceSlider');
    let minV = parseInt(minS.value);
    let maxV = parseInt(maxS.value);
    if (minV > maxV - 25000) {
        if (el === minS) { maxS.value = minV + 25000; }
        else if (el === maxS) { minS.value = maxV - 25000; }
        minV = parseInt(minS.value);
        maxV = parseInt(maxS.value);
    }
    document.getElementById('minPriceLabel').textContent = '$' + minV.toLocaleString();
    document.getElementById('maxPriceLabel').textContent = '$' + maxV.toLocaleString();
    const pct = v => ((v - 100000) / 1400000) * 100;
    const bar = document.getElementById('priceBar');
    bar.style.left = pct(minV) + '%';
    bar.style.width = (pct(maxV) - pct(minV)) + '%';
    if (el === minS) { minS.style.zIndex = 4; maxS.style.zIndex = 3; }
    else if (el === maxS) { maxS.style.zIndex = 4; minS.style.zIndex = 3; }
}

// ── Importance sliders ──────────────────────────────────────
function updateImpDisplay(el) {
    const val = parseInt(el.value);
    const display = document.getElementById(el.id + '-val');
    display.textContent = val;
    display.className = 'imp-val ' + (val >= 7 ? 'high' : val >= 4 ? 'mid' : val >= 1 ? 'low' : 'off');
}

function resetImportance() {
    const defaults = PREFS_CONFIG.defaults;
    document.querySelectorAll('.imp-slider').forEach(el => {
        if (defaults[el.name] !== undefined) {
            el.value = defaults[el.name];
            updateImpDisplay(el);
        }
    });
}

// ── POI Proximity dropdown ───────────────────────────────────
function onPoiSelect(sel) {
    const opt = sel.options[sel.selectedIndex];
    const nameInput = document.getElementById('proximity_poi_name');
    const latInput  = document.getElementById('proximity_poi_lat');
    const lngInput  = document.getElementById('proximity_poi_lng');
    const slider    = document.getElementById('imp_proximity_poi');

    if (opt.value) {
        nameInput.value = opt.value;
        latInput.value  = opt.dataset.lat || 0;
        lngInput.value  = opt.dataset.lng || 0;
        // Auto-enable slider if it was off
        if (parseInt(slider.value) === 0) {
            slider.value = 5;
            updateImpDisplay(slider);
        }
    } else {
        nameInput.value = '';
        latInput.value  = 0;
        lngInput.value  = 0;
    }
}

// Init price bar on load
updatePriceRange(null);

// ── AJAX FORM SAVE (no page jump) ──────────────────────────
function saveFormAjax(e, form, statusId) {
    e.preventDefault();
    const statusEl = document.getElementById(statusId);
    const btn = form.querySelector('button[type="submit"]');
    const origHtml = btn.innerHTML;

    // Make sure hidden area inputs are current
    if (typeof refreshHiddenInputs === 'function') refreshHiddenInputs();

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';
    statusEl.textContent = '';

    const fd = new FormData(form);
    fetch(form.action || window.location.pathname, {
        method: 'POST',
        body: fd,
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok) {
            statusEl.innerHTML = '<span class="text-success"><i class="bi bi-check-circle me-1"></i>' + data.message + '</span>';
            // Show guest session warning modal after save
            if (!PREFS_CONFIG.isAuth) {
                const modal = document.getElementById('guestSavedModal');
                if (modal) {
                    setTimeout(() => new bootstrap.Modal(modal).show(), 600);
                }
            }
        } else {
            statusEl.innerHTML = '<span class="text-danger"><i class="bi bi-x-circle me-1"></i>' + (data.message || 'Save failed') + '</span>';
        }
        setTimeout(() => { statusEl.textContent = ''; }, 4000);
    })
    .catch(() => {
        statusEl.innerHTML = '<span class="text-danger"><i class="bi bi-x-circle me-1"></i>Network error</span>';
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = origHtml;
    });
    return false;
}

// ── Guest saved modal ──────────────────────────────────────
if (!PREFS_CONFIG.isAuth) {
    if (new URLSearchParams(window.location.search).get('saved') === 'guest') {
        new bootstrap.Modal(document.getElementById('guestSavedModal')).show();
        history.replaceState(null, '', window.location.pathname);
    }
}

// ── AI Preferences Analyst ─────────────────────────────────
if (PREFS_CONFIG.isAuth) {
    window.analyzePreferences = function() {
        const btn = document.getElementById('prefs-analyze-btn');
        const resultDiv = document.getElementById('prefs-ai-result');
        const loading = document.getElementById('prefs-ai-loading');
        const error = document.getElementById('prefs-ai-error');
        const brief = document.getElementById('prefs-ai-brief');

        resultDiv.style.display = 'block';
        loading.style.display = 'block';
        error.style.display = 'none';
        brief.style.display = 'none';
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Analyzing...';
        resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        const formData = new FormData();
        formData.append('min_price', document.getElementById('minPriceSlider').value);
        formData.append('max_price', document.getElementById('maxPriceSlider').value);
        document.querySelectorAll('.imp-slider').forEach(el => formData.append(el.name, el.value));
        ['must_have_garage','must_have_porch','must_have_patio'].forEach(name => {
            const el = document.querySelector(`[name="${name}"]`);
            if (el && el.checked) formData.append(name, 'on');
        });
        ['min_beds','min_baths'].forEach(name => {
            const el = document.querySelector(`[name="${name}"]`);
            if (el) formData.append(name, el.value);
        });

        fetch(PREFS_CONFIG.analyzePreferencesUrl, { method: 'POST', body: formData })
        .then(resp => resp.json())
        .then(data => {
            loading.style.display = 'none';
            if (data.error) {
                error.textContent = data.error; error.style.display = 'block';
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-lightning-charge"></i> Try Again';
                return;
            }
            document.getElementById('pa-headline').textContent    = data.headline     || '';
            document.getElementById('pa-strengths').textContent   = data.strengths    || '';
            document.getElementById('pa-blind-spots').textContent = data.blind_spots  || '';
            document.getElementById('pa-tweaks').textContent      = data.tweaks       || '';
            document.getElementById('pa-local').textContent       = data.local_insight|| '';
            document.getElementById('pa-bottom-line').textContent = data.bottom_line  || '';
            brief.style.display = 'block';
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Re-Analyze';
        })
        .catch(() => {
            loading.style.display = 'none';
            error.textContent = 'Network error.'; error.style.display = 'block';
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-lightning-charge"></i> Try Again';
        });
    };
}
