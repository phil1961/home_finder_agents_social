/* ─────────────────────────────────────────────
   File: app/static/js/site-manager.js
   App Version: 1.0.0 | File Version: 1.0.0
   Last Modified: 2026-03-15
   ───────────────────────────────────────────── */

/* ── Map Picker ─────────────────────────────────────────────────────────── */
let _mpMap = null, _mpCenter = null, _mpRect = null;
let _mpDrawing = false, _mpStartLL = null;

function openMapPicker() {
    const modal = new bootstrap.Modal(document.getElementById('mapPickerModal'));
    modal.show();
    document.getElementById('mapPickerModal').addEventListener('shown.bs.modal', _initMapPicker, { once: true });
}

function _initMapPicker() {
    if (_mpMap) { _mpMap.invalidateSize(); return; }

    // Seed from form values if present
    const clat = parseFloat(document.getElementById('create_center_lat').value) || 39.5;
    const clng = parseFloat(document.getElementById('create_center_lon').value) || -98.35;
    const zoom = parseInt(document.getElementById('create_zoom').value)        || 4;

    _mpMap = L.map('map-picker-leaflet', { zoomControl: true }).setView([clat, clng], zoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors', maxZoom: 18
    }).addTo(_mpMap);

    // Restore existing center marker if coords already filled
    if (document.getElementById('create_center_lat').value) {
        _mpCenter = L.marker([clat, clng], { draggable: true })
            .addTo(_mpMap)
            .bindTooltip('Map Center', { permanent: false });
        _mpCenter.on('dragend', _updateCenterDisplay);
        _updateCenterDisplay();
    }

    // Restore existing bounding box if coords already filled
    const swlat = parseFloat(document.getElementById('sw_lat').value);
    const swlng = parseFloat(document.getElementById('sw_lon').value);
    const nelat = parseFloat(document.getElementById('ne_lat').value);
    const nelng = parseFloat(document.getElementById('ne_lon').value);
    if (swlat && swlng && nelat && nelng) {
        _mpRect = L.rectangle([[swlat, swlng], [nelat, nelng]], {
            color: '#198754', weight: 2, fillOpacity: 0.08
        }).addTo(_mpMap);
        _updateBoundsDisplay([[swlat, swlng], [nelat, nelng]]);
    }

    // Click → place/move center marker
    _mpMap.on('click', function(e) {
        if (_mpDrawing) return;
        if (_mpCenter) _mpMap.removeLayer(_mpCenter);
        _mpCenter = L.marker(e.latlng, { draggable: true })
            .addTo(_mpMap)
            .bindTooltip('Map Center', { permanent: false })
            .openTooltip();
        _mpCenter.on('dragend', _updateCenterDisplay);
        _updateCenterDisplay();
    });

    // Mousedown on map → start rectangle draw
    _mpMap.on('mousedown', function(e) {
        if (!e.originalEvent.shiftKey) return;   // Shift+drag to draw rectangle
        _mpDrawing = true;
        _mpStartLL = e.latlng;
        _mpMap.dragging.disable();
        if (_mpRect) { _mpMap.removeLayer(_mpRect); _mpRect = null; }
    });

    _mpMap.on('mousemove', function(e) {
        if (!_mpDrawing || !_mpStartLL) return;
        if (_mpRect) _mpMap.removeLayer(_mpRect);
        _mpRect = L.rectangle([_mpStartLL, e.latlng], {
            color: '#198754', weight: 2, fillOpacity: 0.08
        }).addTo(_mpMap);
        _updateBoundsDisplay([_mpStartLL, e.latlng]);
    });

    _mpMap.on('mouseup', function(e) {
        if (!_mpDrawing) return;
        _mpDrawing = false;
        _mpMap.dragging.enable();
        _mpStartLL = null;
    });

    _mpMap.on('zoomend', function() {
        document.getElementById('mp-zoom-display').textContent = _mpMap.getZoom();
    });
}

function _updateCenterDisplay() {
    if (!_mpCenter) return;
    const ll = _mpCenter.getLatLng();
    document.getElementById('mp-center-display').textContent =
        ll.lat.toFixed(4) + ', ' + ll.lng.toFixed(4);
}

function _updateBoundsDisplay(corners) {
    const lats = [corners[0].lat ?? corners[0][0], corners[1].lat ?? corners[1][0]];
    const lngs = [corners[0].lng ?? corners[0][1], corners[1].lng ?? corners[1][1]];
    const sw = [Math.min(...lats), Math.min(...lngs)];
    const ne = [Math.max(...lats), Math.max(...lngs)];
    document.getElementById('mp-bounds-display').textContent =
        `SW ${sw[0].toFixed(4)},${sw[1].toFixed(4)}  NE ${ne[0].toFixed(4)},${ne[1].toFixed(4)}`;
}

function applyMapPicker() {
    if (_mpCenter) {
        const ll = _mpCenter.getLatLng();
        document.getElementById('create_center_lat').value = ll.lat.toFixed(4);
        document.getElementById('create_center_lon').value = ll.lng.toFixed(4);
    }
    if (_mpRect) {
        const b = _mpRect.getBounds();
        document.getElementById('sw_lat').value = b.getSouth().toFixed(4);
        document.getElementById('sw_lon').value = b.getWest().toFixed(4);
        document.getElementById('ne_lat').value = b.getNorth().toFixed(4);
        document.getElementById('ne_lon').value = b.getEast().toFixed(4);
    }
    if (_mpMap) {
        document.getElementById('create_zoom').value = _mpMap.getZoom();
    }
    // Update hint text
    document.getElementById('map-picker-hint').innerHTML =
        '<span class="text-success"><i class="bi bi-check-circle me-1"></i>Coordinates applied from map.</span>';
    bootstrap.Modal.getInstance(document.getElementById('mapPickerModal')).hide();
}
/* ── Nominatim Geocoder ─────────────────────────────────────────────────── */
async function mpSearch() {
    const q = document.getElementById('mp-search-input').value.trim();
    if (!q) return;
    const ul = document.getElementById('mp-search-results');
    ul.innerHTML = '<li class="list-group-item list-group-item-action text-muted small">Searching…</li>';
    ul.style.display = 'block';
    try {
        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=6&addressdetails=0`;
        const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
        const data = await res.json();
        ul.innerHTML = '';
        if (!data.length) {
            ul.innerHTML = '<li class="list-group-item small text-muted">No results found.</li>';
            return;
        }
        data.forEach(item => {
            const li = document.createElement('li');
            li.className = 'list-group-item list-group-item-action small py-1';
            li.textContent = item.display_name;
            li.onclick = () => mpSelectResult(item, ul);
            ul.appendChild(li);
        });
    } catch(e) {
        ul.innerHTML = '<li class="list-group-item small text-danger">Search failed — check network.</li>';
    }
}

function mpSelectResult(item, ul) {
    ul.style.display = 'none';
    document.getElementById('mp-search-input').value = item.display_name.split(',')[0];

    const lat = parseFloat(item.lat);
    const lng = parseFloat(item.lon);
    const zoom = 10;

    if (!_mpMap) return;
    _mpMap.setView([lat, lng], zoom);

    // Place center marker
    if (_mpCenter) _mpMap.removeLayer(_mpCenter);
    _mpCenter = L.marker([lat, lng], { draggable: true })
        .addTo(_mpMap)
        .bindTooltip('Map Center', { permanent: false })
        .openTooltip();
    _mpCenter.on('dragend', _updateCenterDisplay);
    _updateCenterDisplay();

    // Auto-draw bounding box from Nominatim's boundingbox if available
    if (item.boundingbox) {
        const bb = item.boundingbox.map(parseFloat); // [s, n, w, e]
        if (_mpRect) _mpMap.removeLayer(_mpRect);
        _mpRect = L.rectangle([[bb[0], bb[2]], [bb[1], bb[3]]], {
            color: '#198754', weight: 2, fillOpacity: 0.08
        }).addTo(_mpMap);
        _mpMap.fitBounds(_mpRect.getBounds(), { padding: [20, 20] });
        _updateBoundsDisplay([[bb[0], bb[2]], [bb[1], bb[3]]]);
    }
}
/* ── End Geocoder ───────────────────────────────────────────────────────── */

/* ── Location Picker ────────────────────────────────────────────────────── */
let _lpTimer = null;
let _lpHighlight = -1;
let _lpResults = [];

function openLocationPicker() {
    document.getElementById('lp-search-input').value = '';
    document.getElementById('lp-search-results').style.display = 'none';
    document.getElementById('lp-search-results').innerHTML = '';
    document.getElementById('lp-status').textContent = '';
    _lpHighlight = -1;
    _lpResults = [];
    const modal = new bootstrap.Modal(document.getElementById('locationPickerModal'));
    modal.show();
    // Focus the input after modal animation
    document.getElementById('locationPickerModal').addEventListener('shown.bs.modal', function handler() {
        document.getElementById('lp-search-input').focus();
        document.getElementById('locationPickerModal').removeEventListener('shown.bs.modal', handler);
    });
}

function lpTypeahead() {
    clearTimeout(_lpTimer);
    const q = document.getElementById('lp-search-input').value.trim();
    if (q.length < 2) {
        document.getElementById('lp-search-results').style.display = 'none';
        document.getElementById('lp-spinner').style.display = 'none';
        return;
    }
    document.getElementById('lp-spinner').style.display = '';
    _lpTimer = setTimeout(() => lpSearch(q), 300);
}

function lpKeydown(e) {
    const ul = document.getElementById('lp-search-results');
    const items = ul.querySelectorAll('.list-group-item-action');
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        _lpHighlight = Math.min(_lpHighlight + 1, items.length - 1);
        lpHighlightItem(items);
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        _lpHighlight = Math.max(_lpHighlight - 1, 0);
        lpHighlightItem(items);
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (_lpHighlight >= 0 && _lpHighlight < _lpResults.length) {
            lpApply(_lpResults[_lpHighlight], ul);
        } else {
            // Force search on Enter if no item highlighted
            clearTimeout(_lpTimer);
            const q = document.getElementById('lp-search-input').value.trim();
            if (q.length >= 2) lpSearch(q);
        }
    } else if (e.key === 'Escape') {
        ul.style.display = 'none';
    }
}

function lpHighlightItem(items) {
    items.forEach((el, i) => {
        el.style.background = i === _lpHighlight ? '#e8f0fe' : '';
    });
    if (items[_lpHighlight]) items[_lpHighlight].scrollIntoView({ block: 'nearest' });
}

async function lpSearch(q) {
    if (!q) q = document.getElementById('lp-search-input').value.trim();
    if (!q) return;
    const ul = document.getElementById('lp-search-results');
    _lpHighlight = -1;
    _lpResults = [];
    try {
        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=8&addressdetails=1&countrycodes=us`;
        const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
        const data = await res.json();
        document.getElementById('lp-spinner').style.display = 'none';
        ul.innerHTML = '';
        if (!data.length) {
            ul.innerHTML = '<li class="list-group-item small text-muted py-2">No US results found. Try adding a state abbreviation.</li>';
            ul.style.display = 'block';
            return;
        }
        _lpResults = data;
        data.forEach((item, idx) => {
            const li = document.createElement('li');
            li.className = 'list-group-item list-group-item-action py-2';
            li.style.cursor = 'pointer';
            const addr = item.address || {};
            const city  = addr.city || addr.town || addr.village || addr.county || item.display_name.split(',')[0];
            const state = addr.state || '';
            const stAbbr = _lpStateAbbr(state) || state;
            const typeLabel = item.type ? `<span class="badge bg-light text-muted border ms-2" style="font-size:.6rem;">${item.type}</span>` : '';
            li.innerHTML = `<div class="fw-semibold small">${city}${state ? ', ' + stAbbr : ''}${typeLabel}</div>
                            <div class="text-muted text-truncate" style="font-size:.7rem;">${item.display_name}</div>`;
            li.onmouseenter = () => { _lpHighlight = idx; lpHighlightItem(ul.querySelectorAll('.list-group-item-action')); };
            li.onclick = () => lpApply(item, ul);
            ul.appendChild(li);
        });
        ul.style.display = 'block';
    } catch(e) {
        document.getElementById('lp-spinner').style.display = 'none';
        ul.innerHTML = '<li class="list-group-item small text-danger py-2">Search failed — check network.</li>';
        ul.style.display = 'block';
    }
}

async function lpApply(item, ul) {
    ul.style.display = 'none';
    const status = document.getElementById('lp-status');
    status.textContent = 'Fetching zip code…';
    status.className = 'small text-muted mt-2';

    const addr   = item.address || {};
    const lat    = parseFloat(item.lat);
    const lng    = parseFloat(item.lon);
    const city   = addr.city || addr.town || addr.village || addr.county || item.display_name.split(',')[0];
    const state  = addr.state || '';
    const stAbbr = _lpStateAbbr(state) || state.trim();

    // ── Display Name
    const displayName = stAbbr ? `${city.trim()}, ${stAbbr}` : city.trim();
    const dnEl = document.getElementById('create_display_name');
    if (dnEl) dnEl.value = displayName;

    // ── Site Key: city + state abbr, lowercase, only [a-z0-9]
    const siteKey = (city.trim() + stAbbr).toLowerCase().replace(/[^a-z0-9]/g, '');
    const skEl = document.getElementById('create_site_key');
    if (skEl) { skEl.value = siteKey; updateDbFilename(siteKey); }

    // ── Map center
    const centerLatEl = document.getElementById('create_center_lat');
    const centerLonEl = document.getElementById('create_center_lon');
    if (centerLatEl) centerLatEl.value = lat.toFixed(4);
    if (centerLonEl) centerLonEl.value = lng.toFixed(4);

    // ── Bounding box from Nominatim boundingbox [s, n, w, e]
    if (item.boundingbox) {
        const bb = item.boundingbox.map(parseFloat); // [s, n, w, e]
        const swLatEl = document.getElementById('sw_lat');
        const swLonEl = document.getElementById('sw_lon');
        const neLatEl = document.getElementById('ne_lat');
        const neLonEl = document.getElementById('ne_lon');
        if (swLatEl) swLatEl.value = bb[0].toFixed(4);
        if (swLonEl) swLonEl.value = bb[2].toFixed(4);
        if (neLatEl) neLatEl.value = bb[1].toFixed(4);
        if (neLonEl) neLonEl.value = bb[3].toFixed(4);

        // ── Zoom: estimate from bounding box span
        const latSpan = bb[1] - bb[0];
        const lngSpan = bb[3] - bb[2];
        const maxSpan = Math.max(latSpan, lngSpan);
        let zoom = 10;
        if      (maxSpan > 5)   zoom = 7;
        else if (maxSpan > 2)   zoom = 8;
        else if (maxSpan > 0.8) zoom = 9;
        else if (maxSpan > 0.3) zoom = 10;
        else if (maxSpan > 0.1) zoom = 11;
        else                    zoom = 12;
        const zoomEl = document.getElementById('create_zoom');
        if (zoomEl) zoomEl.value = zoom;
    }

    // ── Zip code: reverse geocode center to extract postcode
    let zip = addr.postcode ? addr.postcode.split('-')[0].trim() : null;
    if (!zip || !/^\d{5}$/.test(zip)) {
        try {
            const rurl = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`;
            const rres = await fetch(rurl, { headers: { 'Accept-Language': 'en' } });
            const rdata = await rres.json();
            const raw = rdata?.address?.postcode;
            if (raw) zip = raw.split('-')[0].trim();
        } catch(e) { /* skip */ }
    }
    if (zip && /^\d{5}$/.test(zip)) {
        _zpZips.clear();
        _zpZips.add(zip);
        const zcEl = document.getElementById('create_zip_codes');
        if (zcEl) zcEl.value = zip;
    }

    // ── Close modal and update hint
    bootstrap.Modal.getInstance(document.getElementById('locationPickerModal')).hide();
    const hint = document.getElementById('lp-hint');
    if (hint) hint.innerHTML =
        `<span class="text-success"><i class="bi bi-check-circle me-1"></i>
        Auto-filled from <strong>${displayName}</strong>. Edit any field before creating.</span>`;
}

// Full state name → abbreviation lookup (reuses ZP_STATE_FILES keys)
function _lpStateAbbr(stateName) {
    if (!stateName) return null;
    const up = stateName.trim().toUpperCase();
    // Already an abbreviation?
    if (up.length === 2 && typeof ZP_STATE_FILES !== 'undefined' && ZP_STATE_FILES[up]) return up;
    // Walk ZP_STATE_FILES slugs to match full name
    if (typeof ZP_STATE_FILES !== 'undefined') {
        for (const [abbr, slug] of Object.entries(ZP_STATE_FILES)) {
            const name = slug.replace(/^[a-z]{2}_/, '').replace(/_/g, ' ');
            if (name === stateName.trim().toLowerCase()) return abbr;
        }
    }
    return null;
}
/* ── End Location Picker ────────────────────────────────────────────────── */

/* ── ZIP Picker (polygon / GeoJSON edition) ─────────────────────────────── */
let _zpMap      = null;
let _zpZips     = new Set();          // currently selected zip codes
let _zpLayers   = {};                 // zip → Leaflet GeoJSON layer feature ref
let _zpGeoLayer = null;               // current state GeoJSON layer
let _zpLoadedState = null;            // state abbr whose GeoJSON is loaded

// OpenDataDE state GeoJSON file map  (abbr → slug used in filename)
const ZP_STATE_FILES = {
    AL:'al_alabama',AK:'ak_alaska',AZ:'az_arizona',AR:'ar_arkansas',
    CA:'ca_california',CO:'co_colorado',CT:'ct_connecticut',DE:'de_delaware',
    FL:'fl_florida',GA:'ga_georgia',HI:'hi_hawaii',ID:'id_idaho',
    IL:'il_illinois',IN:'in_indiana',IA:'ia_iowa',KS:'ks_kansas',
    KY:'ky_kentucky',LA:'la_louisiana',ME:'me_maine',MD:'md_maryland',
    MA:'ma_massachusetts',MI:'mi_michigan',MN:'mn_minnesota',MS:'ms_mississippi',
    MO:'mo_missouri',MT:'mt_montana',NE:'ne_nebraska',NV:'nv_nevada',
    NH:'nh_new_hampshire',NJ:'nj_new_jersey',NM:'nm_new_mexico',NY:'ny_new_york',
    NC:'nc_north_carolina',ND:'nd_north_dakota',OH:'oh_ohio',OK:'ok_oklahoma',
    OR:'or_oregon',PA:'pa_pennsylvania',RI:'ri_rhode_island',SC:'sc_south_carolina',
    SD:'sd_south_dakota',TN:'tn_tennessee',TX:'tx_texas',UT:'ut_utah',
    VT:'vt_vermont',VA:'va_virginia',WA:'wa_washington',WV:'wv_west_virginia',
    WI:'wi_wisconsin',WY:'wy_wyoming',DC:'dc_district_of_columbia'
};

function openZipPicker() {
    const modalEl = document.getElementById('zipPickerModal');
    modalEl.removeEventListener('shown.bs.modal', _initZipPicker);
    modalEl.addEventListener('shown.bs.modal', _initZipPicker, { once: true });
    // Pre-load existing zips from textarea
    _zpZips.clear();
    const textarea = document.getElementById('create_zip_codes');
    if (textarea && textarea.value.trim()) {
        textarea.value.split(',').forEach(z => {
            const t = z.trim();
            if (/^\d{5}$/.test(t)) _zpZips.add(t);
        });
    }
    new bootstrap.Modal(modalEl).show();
}

async function _initZipPicker() {
    _renderZipChips();

    const clat = parseFloat(document.getElementById('create_center_lat')?.value);
    const clng = parseFloat(document.getElementById('create_center_lon')?.value);
    const hasCenter = !isNaN(clat) && !isNaN(clng);

    if (_zpMap) {
        _zpMap.invalidateSize();
        if (hasCenter) _zpMap.setView([clat, clng], 10);
        return;
    }

    const initLat  = hasCenter ? clat  : 39.5;
    const initLng  = hasCenter ? clng  : -98.35;
    const initZoom = hasCenter ? 10    : 4;

    _zpMap = L.map('zip-picker-leaflet', { zoomControl: true }).setView([initLat, initLng], initZoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors', maxZoom: 18
    }).addTo(_zpMap);

    // Auto-load state GeoJSON if we have a center point
    if (hasCenter) {
        _zpSetStatus('Detecting state…', 'text-muted');
        try {
            const url = `https://nominatim.openstreetmap.org/reverse?lat=${clat}&lon=${clng}&format=json`;
            const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
            const data = await res.json();
            const stateAbbr = _zpStateAbbr(data?.address?.state);
            if (stateAbbr) await _zpLoadState(stateAbbr);
        } catch(e) {
            _zpSetStatus('Could not auto-detect state — use search to load boundaries.', 'text-warning');
        }
    }
}

// Style helpers
function _zpStyleDefault(feature) {
    const z = feature.properties.ZCTA5CE10 || feature.properties.ZIP_CODE || feature.properties.GEOID10;
    const sel = _zpZips.has(z);
    return {
        color: sel ? '#0d6efd' : '#6c757d',
        weight: sel ? 2 : 1,
        fillColor: sel ? '#0d6efd' : '#adb5bd',
        fillOpacity: sel ? 0.45 : 0.12
    };
}

function _zpOnEachFeature(feature, layer) {
    const z = feature.properties.ZCTA5CE10 || feature.properties.ZIP_CODE || feature.properties.GEOID10;
    if (!z) return;
    _zpLayers[z] = layer;
    layer.on('click', function() {
        if (_zpZips.has(z)) {
            _zpZips.delete(z);
        } else {
            _zpZips.add(z);
        }
        layer.setStyle(_zpStyleDefault(feature));
        _renderZipChips();
    });
    layer.bindTooltip(z, { sticky: true, className: 'leaflet-tooltip-zip' });
}

async function _zpLoadState(stateAbbr) {
    const slug = ZP_STATE_FILES[stateAbbr.toUpperCase()];
    if (!slug) { _zpSetStatus(`No GeoJSON available for "${stateAbbr}".`, 'text-warning'); return; }
    if (_zpLoadedState === stateAbbr) return;   // already loaded

    _zpSetStatus('Loading zip boundaries…', 'text-muted');
    if (_zpGeoLayer) { _zpMap.removeLayer(_zpGeoLayer); _zpGeoLayer = null; _zpLayers = {}; }

    const url = `https://raw.githubusercontent.com/OpenDataDE/State-zip-code-GeoJSON/master/${slug}_zip_codes_geo.min.json`;
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const geojson = await res.json();
        _zpGeoLayer = L.geoJSON(geojson, {
            style: _zpStyleDefault,
            onEachFeature: _zpOnEachFeature
        }).addTo(_zpMap);
        _zpLoadedState = stateAbbr;
        _zpSetStatus(`${stateAbbr} zip boundaries loaded — click polygons to select.`, 'text-success');
    } catch(err) {
        _zpSetStatus(`Failed to load ${stateAbbr} boundaries: ${err.message}`, 'text-danger');
    }
}

function _zpSetStatus(msg, cls) {
    const el = document.getElementById('zp-status');
    if (el) { el.textContent = msg; el.className = `small ${cls}`; }
}

function _renderZipChips() {
    // Also re-style any loaded polygons
    if (_zpGeoLayer) {
        _zpGeoLayer.eachLayer(layer => {
            if (layer.feature) layer.setStyle(_zpStyleDefault(layer.feature));
        });
    }
    const container = document.getElementById('zp-chips');
    if (!container) return;
    if (_zpZips.size === 0) {
        container.innerHTML = '<span class="text-muted small">No zip codes selected yet.</span>';
        return;
    }
    container.innerHTML = '';
    [..._zpZips].sort().forEach(z => {
        const chip = document.createElement('span');
        chip.className = 'badge bg-primary d-inline-flex align-items-center gap-1';
        chip.style.cssText = 'font-size:.78rem; padding:4px 8px; cursor:pointer;';
        chip.title = `Click to remove ${z}`;
        chip.innerHTML = `${z} <button type="button" class="btn-close btn-close-white"
            style="font-size:.55em;" aria-label="Remove ${z}"></button>`;
        chip.addEventListener('click', () => { _zpZips.delete(z); _renderZipChips(); });
        container.appendChild(chip);
    });
}

async function zpSearch() {
    const q = document.getElementById('zp-search-input').value.trim();
    if (!q) return;
    const ul = document.getElementById('zp-search-results');
    ul.innerHTML = '<li class="list-group-item small text-muted py-1">Searching…</li>';
    ul.style.display = 'block';
    try {
        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=6&addressdetails=1`;
        const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
        const data = await res.json();
        ul.innerHTML = '';
        if (!data.length) {
            ul.innerHTML = '<li class="list-group-item small text-muted py-1">No results found.</li>';
            return;
        }
        data.forEach(item => {
            const li = document.createElement('li');
            li.className = 'list-group-item list-group-item-action small py-1';
            li.textContent = item.display_name;
            li.onclick = async () => {
                ul.style.display = 'none';
                const lat = parseFloat(item.lat), lng = parseFloat(item.lon);
                _zpMap.setView([lat, lng], 10);

                // Detect state abbreviation from Nominatim address
                const addr = item.address || {};
                const stateAbbr = _zpStateAbbr(addr.state);
                if (stateAbbr) await _zpLoadState(stateAbbr);

                // Suggest display name if field empty
                const dn = document.getElementById('create_display_name');
                if (dn && !dn.value.trim()) {
                    const city = addr.city || addr.town || addr.county || item.display_name.split(',')[0];
                    const st   = addr.state || '';
                    dn.value = st ? `${city.trim()}, ${_zpStateAbbr(st) || st.trim()}` : city.trim();
                }
            };
            ul.appendChild(li);
        });
    } catch(e) {
        ul.innerHTML = '<li class="list-group-item small text-danger py-1">Search failed — check network.</li>';
    }
}

// Map full state name → abbreviation
const _ZP_NAME_TO_ABBR = Object.fromEntries(
    Object.entries(ZP_STATE_FILES).map(([abbr, slug]) => [
        slug.replace(/^[a-z]{2}_/, '').replace(/_/g, ' '), abbr
    ])
);
function _zpStateAbbr(stateName) {
    if (!stateName) return null;
    const up = stateName.trim().toUpperCase();
    if (ZP_STATE_FILES[up]) return up;
    const lower = stateName.trim().toLowerCase().replace(/_/g, ' ');
    return _ZP_NAME_TO_ABBR[lower] || null;
}

function applyZipPicker() {
    const textarea = document.getElementById('create_zip_codes');
    if (textarea) textarea.value = [..._zpZips].sort().join(', ');
    bootstrap.Modal.getInstance(document.getElementById('zipPickerModal')).hide();
}
/* ── End ZIP Picker ─────────────────────────────────────────────────────── */

function updateDbFilename(val) {
    const el = document.getElementById('db-filename-input');
    if (el && !el.value) {
        el.placeholder = val ? val + '.db' : 'atlanta.db';
    }
}

async function showNginx(siteKey, siteName) {
    document.getElementById('nginx-site-name').textContent = siteName;
    document.getElementById('nginx-snippet').textContent = 'Loading…';
    const modal = new bootstrap.Modal(document.getElementById('nginxModal'));
    modal.show();
    try {
        const r = await fetch(`/admin/sites/${siteKey}/nginx`);
        const data = await r.json();
        document.getElementById('nginx-snippet').textContent = data.nginx;
    } catch (e) {
        document.getElementById('nginx-snippet').textContent = 'Error loading config.';
    }
}

function copyNginx() {
    const text = document.getElementById('nginx-snippet').textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target.closest('button');
        btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Copied!';
        setTimeout(() => btn.innerHTML = '<i class="bi bi-clipboard me-1"></i>Copy', 2000);
    });
}
