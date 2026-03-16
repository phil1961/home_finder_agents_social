/* ─────────────────────────────────────────────
   File: app/static/js/landmarks.js
   App Version: 2026.03.14 | File Version: 1.0.0
   Last Modified: 2026-03-15
   ───────────────────────────────────────────── */

// ══════════════ USER LANDMARKS (personal, up to 3) ══════════════
if (PREFS_CONFIG.isAuth) {
(function() {
    const _siteLat  = PREFS_CONFIG.siteLat;
    const _siteLon  = PREFS_CONFIG.siteLon;
    const _siteZoom = PREFS_CONFIG.siteZoom;
    const _siteDisplayName = PREFS_CONFIG.siteDisplayName;
    const _siteZips = PREFS_CONFIG.siteZipCodes || [];

    let _ulTimer = null;
    let _ulHighlight = -1;
    let _ulResults = [];

    function ulTypeahead() {
        clearTimeout(_ulTimer);
        const q = document.getElementById('ul-search').value.trim();
        const results = document.getElementById('ul-search-results');
        if (q.length < 2) {
            results.style.display = 'none';
            document.getElementById('ul-search-spinner').style.display = 'none';
            return;
        }
        document.getElementById('ul-search-spinner').style.display = '';
        _ulTimer = setTimeout(() => ulSearch(q), 300);
    }
    window.ulTypeahead = ulTypeahead;

    function ulSearchKeydown(e) {
        const results = document.getElementById('ul-search-results');
        const items = results.querySelectorAll('.list-group-item-action');
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            _ulHighlight = Math.min(_ulHighlight + 1, items.length - 1);
            items.forEach((el, i) => el.style.background = i === _ulHighlight ? '#e8f0fe' : '');
            if (items[_ulHighlight]) items[_ulHighlight].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            _ulHighlight = Math.max(_ulHighlight - 1, 0);
            items.forEach((el, i) => el.style.background = i === _ulHighlight ? '#e8f0fe' : '');
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (_ulHighlight >= 0 && _ulHighlight < items.length) {
                items[_ulHighlight].click();
            }
        } else if (e.key === 'Escape') {
            results.style.display = 'none';
        }
    }
    window.ulSearchKeydown = ulSearchKeydown;

    // Extract state abbreviation from display name (e.g., "Dover, DE" -> "DE")
    const _siteState = (() => {
        const parts = _siteDisplayName.split(',');
        return parts.length > 1 ? parts[parts.length - 1].trim() : '';
    })();
    const _siteCity = (() => {
        const parts = _siteDisplayName.split(',');
        return parts[0].trim();
    })();

    // Clean a pasted full address down to just the street part
    function ulCleanAddress(raw) {
        let q = raw.trim();
        q = q.replace(/,?\s*(United States|USA|US)\s*$/i, '').trim();
        q = q.replace(/,?\s*\d{5}(-\d{4})?\s*$/, '').trim();
        q = q.replace(/,?\s*[A-Z]{2}\s*$/i, '').trim();
        const parts = q.split(',');
        if (/^\d/.test(parts[0].trim())) {
            return parts[0].trim();
        }
        return parts.slice(0, 2).join(',').trim();
    }

    function ulSearch(q) {
        if (!q) q = document.getElementById('ul-search').value.trim();
        if (!q || q.length < 2) return;
        const results = document.getElementById('ul-search-results');
        _ulHighlight = -1;
        _ulResults = [];
        const _r = 0.5;

        const cleaned = ulCleanAddress(q);

        let url;
        if (/^\d/.test(cleaned) && _siteState) {
            url = `https://nominatim.openstreetmap.org/search?format=json&street=${encodeURIComponent(cleaned)}&state=${encodeURIComponent(_siteState)}&country=US&addressdetails=1&limit=10`;
        } else {
            const searchQ = _siteState ? cleaned + ', ' + _siteState : cleaned;
            url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQ)}&limit=10&countrycodes=us&addressdetails=1&viewbox=${_siteLon-_r},${_siteLat+_r},${_siteLon+_r},${_siteLat-_r}&bounded=0`;
        }
        fetch(url, {headers:{'Accept':'application/json'}}).then(r=>r.json()).then(data=>{
            document.getElementById('ul-search-spinner').style.display = 'none';
            results.innerHTML = '';

            const _maxDist = 0.5;
            let filtered = data.filter(r => {
                const rlat = parseFloat(r.lat), rlng = parseFloat(r.lon);
                return Math.abs(rlat - _siteLat) < _maxDist && Math.abs(rlng - _siteLon) < _maxDist;
            });

            if (!filtered.length) {
                let hint;
                if (/^\d+$/.test(q)) {
                    hint = 'Include a street name (e.g. "' + q + ' Main St")';
                } else {
                    hint = '<a href="#" onclick="ulOpenGoogleMaps(); return false;">Open Google Maps</a> — find it, copy the address, paste it here';
                }
                results.innerHTML = `<div class="list-group-item small py-2">Not found. ${hint}</div>`;
            } else {
                _ulResults = filtered;
                filtered.forEach((r, idx) => {
                    const item = document.createElement('a');
                    item.href = '#';
                    item.className = 'list-group-item list-group-item-action py-1 px-2';
                    item.style.cursor = 'pointer';
                    const addr = r.address || {};
                    const road = addr.road || '';
                    const houseNum = addr.house_number || '';
                    const friendlyName = houseNum && road ? `${houseNum} ${road}` :
                                         road ? road :
                                         r.display_name.split(',').slice(0, 2).join(',').trim();
                    const zip = addr.postcode || '';
                    const town = addr.city || addr.town || addr.village || '';
                    const zipBadge = zip ? `<span class="badge bg-light text-muted border ms-1" style="font-size:0.55rem;">${zip}</span>` : '';
                    item.innerHTML = `<div class="fw-semibold small">${r.display_name.split(',').slice(0,3).join(', ')}${zipBadge}</div>`;
                    item.onmouseenter = () => {
                        _ulHighlight = idx;
                        results.querySelectorAll('.list-group-item-action').forEach((el, i) => el.style.background = i === idx ? '#e8f0fe' : '');
                    };
                    item.onclick = function(e) {
                        e.preventDefault();
                        const rlat = parseFloat(r.lat), rlng = parseFloat(r.lon);
                        document.getElementById('ul-lat').value = rlat.toFixed(6);
                        document.getElementById('ul-lng').value = rlng.toFixed(6);
                        if (!document.getElementById('ul-name').value.trim()) {
                            document.getElementById('ul-name').value = friendlyName;
                        }
                        document.getElementById('ul-search').value = friendlyName + (town ? ', ' + town : '');
                        results.style.display = 'none';
                        ulSetMapPoint(rlat, rlng);
                        document.getElementById('ul-name').focus();
                    };
                    results.appendChild(item);
                });
            }
            results.style.display = 'block';
        }).catch(()=>{
            document.getElementById('ul-search-spinner').style.display = 'none';
            results.innerHTML = '<div class="list-group-item text-danger small">Search failed</div>';
            results.style.display = 'block';
        });
    }

    document.addEventListener('click', function(e) {
        const results = document.getElementById('ul-search-results');
        if (results && !results.contains(e.target) && e.target.id !== 'ul-search') results.style.display = 'none';
    });

    // ── Mini map picker ───────────────────────────────────────
    let ulMap = null;
    let ulMarker = null;

    function ulInitMap() {
        const el = document.getElementById('ul-map');
        if (!el || ulMap) return;
        const _b = L.latLngBounds([_siteLat - 0.4, _siteLon - 0.4], [_siteLat + 0.4, _siteLon + 0.4]);
        ulMap = L.map('ul-map', {
            zoomControl: true, maxBounds: _b.pad(0.1), maxBoundsViscosity: 1.0, minZoom: 10,
        }).setView([_siteLat, _siteLon], _siteZoom);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap'
        }).addTo(ulMap);

        // Show existing user landmarks — populated from PREFS_CONFIG
        if (PREFS_CONFIG.userLandmarks) {
            PREFS_CONFIG.userLandmarks.forEach(function(lm) {
                L.marker([lm.lat, lm.lng], {
                    icon: L.divIcon({className:'', html:'<i class="bi bi-geo-alt-fill" style="font-size:1.2rem;color:#dc2626;"></i>', iconSize:[16,22], iconAnchor:[8,22]})
                }).addTo(ulMap).bindTooltip(lm.name, {permanent:false, direction:'top'});
            });
        }

        ulMap.on('click', function(e) {
            const lat = e.latlng.lat, lng = e.latlng.lng;
            document.getElementById('ul-lat').value = lat.toFixed(6);
            document.getElementById('ul-lng').value = lng.toFixed(6);
            document.getElementById('ul-map-hint').textContent = `Marked: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
            if (ulMarker) ulMap.removeLayer(ulMarker);
            ulMarker = L.marker([lat, lng], {
                icon: L.divIcon({className:'', html:'<i class="bi bi-pin-fill" style="font-size:1.4rem;color:#2563eb;"></i>', iconSize:[18,26], iconAnchor:[9,26]})
            }).addTo(ulMap);
            document.getElementById('ul-name').focus();
        });
    }

    function ulSetMapPoint(lat, lng) {
        if (!ulMap) return;
        if (ulMarker) ulMap.removeLayer(ulMarker);
        ulMarker = L.marker([lat, lng], {
            icon: L.divIcon({className:'', html:'<i class="bi bi-pin-fill" style="font-size:1.4rem;color:#2563eb;"></i>', iconSize:[18,26], iconAnchor:[9,26]})
        }).addTo(ulMap);
        ulMap.setView([lat, lng], Math.max(ulMap.getZoom(), 14));
        document.getElementById('ul-map-hint').textContent = `Marked: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    }

    // Open Google Maps to help find a business not in Nominatim
    window.ulOpenGoogleMaps = function() {
        const q = document.getElementById('ul-search').value.trim();
        const searchTerm = q ? q + ', ' + _siteDisplayName : _siteDisplayName;
        window.open('https://www.google.com/maps/search/' + encodeURIComponent(searchTerm), '_blank');
    };

    // Toggle map between small and large
    let ulMapExpanded = false;
    window.ulToggleMapSize = function() {
        const el = document.getElementById('ul-map');
        const btn = document.getElementById('ul-map-expand');
        ulMapExpanded = !ulMapExpanded;
        el.style.height = ulMapExpanded ? '400px' : '150px';
        btn.innerHTML = ulMapExpanded
            ? '<i class="bi bi-fullscreen-exit"></i>'
            : '<i class="bi bi-arrows-fullscreen"></i>';
        if (ulMap) setTimeout(() => ulMap.invalidateSize(), 250);
    };

    // Init map when panel is first opened
    const panelToggle = document.querySelector('[onclick*="my-landmarks-panel"]');
    if (panelToggle) {
        panelToggle.addEventListener('click', function() {
            setTimeout(function() {
                ulInitMap();
                if (ulMap) ulMap.invalidateSize();
            }, 100);
        });
    }

    window.ulAdd = function() {
        const name = document.getElementById('ul-name').value.trim();
        const lat = document.getElementById('ul-lat').value;
        const lng = document.getElementById('ul-lng').value;
        if (!name || !lat || !lng) { alert('Search for a place and give it a name.'); return; }

        const fd = new FormData();
        fd.append('landmark_action', 'add');
        fd.append('landmark_name', name);
        fd.append('landmark_lat', lat);
        fd.append('landmark_lng', lng);

        fetch(PREFS_CONFIG.userLandmarksUrl, {
            method: 'POST', body: fd, credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).then(r=>r.json()).then(data=>{
            if (data.ok) {
                ulRebuild(data.user_landmarks);
                document.getElementById('ul-name').value = '';
                document.getElementById('ul-lat').value = '';
                document.getElementById('ul-lng').value = '';
                document.getElementById('ul-search').value = '';
            } else {
                alert(data.error || 'Failed to add');
            }
        }).catch(err=>alert('Error: '+err.message));
    };

    window.ulDelete = function(name) {
        if (!confirm('Remove "'+name+'"?')) return;
        const fd = new FormData();
        fd.append('landmark_action', 'delete');
        fd.append('landmark_name', name);
        fetch(PREFS_CONFIG.userLandmarksUrl, {
            method: 'POST', body: fd, credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).then(r=>r.json()).then(data=>{
            if (data.ok) ulRebuild(data.user_landmarks);
        }).catch(err=>alert('Error: '+err.message));
    };

    function ulRebuild(lms) {
        const list = document.getElementById('ul-list');
        document.getElementById('ul-count').textContent = `(${lms.length}/3)`;
        if (lms.length === 0) {
            list.innerHTML = '<p class="small text-muted mb-0" id="ul-empty">No personal landmarks yet.</p>';
        } else {
            list.innerHTML = lms.map((lm, i) =>
                `<div class="d-flex align-items-center justify-content-between py-1 ${i<lms.length-1?'border-bottom':''} ul-row">
                    <div class="d-flex align-items-center gap-2">
                        <span class="text-muted fw-bold" style="font-size:0.68rem;">${i+1}.</span>
                        <span class="small">${lm.name}</span>
                        <span class="text-muted" style="font-size:0.6rem;">${lm.lat.toFixed(4)}, ${lm.lng.toFixed(4)}</span>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-danger py-0 px-1" style="font-size:0.6rem;"
                            onclick="ulDelete('${lm.name.replace(/'/g,"\\'")}')"><i class="bi bi-trash"></i></button>
                </div>`
            ).join('');
        }
        document.getElementById('ul-add-section').classList.toggle('d-none', lms.length >= 3);
        document.getElementById('ul-maxed').classList.toggle('d-none', lms.length < 3);

        // Update the POI dropdown — rebuild the "My Landmarks" optgroup
        const sel = document.getElementById('proximity_poi_select');
        let grp = document.getElementById('poi-user-optgroup');
        if (grp) grp.remove();
        if (lms.length > 0) {
            grp = document.createElement('optgroup');
            grp.label = 'My Landmarks';
            grp.id = 'poi-user-optgroup';
            lms.forEach(lm => {
                const opt = document.createElement('option');
                opt.value = lm.name;
                opt.textContent = lm.name;
                opt.dataset.lat = lm.lat;
                opt.dataset.lng = lm.lng;
                grp.appendChild(opt);
            });
            sel.appendChild(grp);
        }
    }
})();
}

// ══════════════ LANDMARK MAP PICKER (Owner+) ══════════════
if (PREFS_CONFIG.isOwner) {
(function() {
    const _siteLat  = PREFS_CONFIG.siteLat;
    const _siteLon  = PREFS_CONFIG.siteLon;
    const _siteZoom = PREFS_CONFIG.siteZoom;

    const mapEl = document.getElementById('lm-picker-map');
    if (!mapEl) return;

    const _lmBounds = L.latLngBounds([_siteLat - 0.5, _siteLon - 0.5], [_siteLat + 0.5, _siteLon + 0.5]);
    const lmMap = L.map('lm-picker-map', {
        zoomControl: true,
        maxBounds: _lmBounds.pad(0.1),
        maxBoundsViscosity: 1.0,
        minZoom: 9,
    }).setView([_siteLat, _siteLon], _siteZoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap'
    }).addTo(lmMap);

    // Show existing landmarks on the map — populated from PREFS_CONFIG
    if (PREFS_CONFIG.ownerLandmarks) {
        PREFS_CONFIG.ownerLandmarks.forEach(function(lm) {
            L.marker([lm.lat, lm.lng], {
                icon: L.divIcon({className:'', html:'<i class="bi bi-geo-alt-fill" style="font-size:1.4rem;color:#dc2626;"></i>', iconSize:[20,28], iconAnchor:[10,28]})
            }).addTo(lmMap).bindTooltip(lm.name, {permanent: false, direction: 'top'});
        });
    }

    let pickerMarker = null;

    function setLandmarkPoint(lat, lng, name) {
        document.getElementById('lm-lat').value = lat.toFixed(6);
        document.getElementById('lm-lng').value = lng.toFixed(6);
        if (name) document.getElementById('lm-name').value = name;

        if (pickerMarker) lmMap.removeLayer(pickerMarker);
        pickerMarker = L.marker([lat, lng], {
            icon: L.divIcon({className:'', html:'<i class="bi bi-pin-fill" style="font-size:1.6rem;color:#2563eb;"></i>', iconSize:[20,30], iconAnchor:[10,30]})
        }).addTo(lmMap);
        lmMap.setView([lat, lng], Math.max(lmMap.getZoom(), 13));
        document.getElementById('lm-map-hint').textContent = `Selected: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    }

    // Click map to place pin
    lmMap.on('click', function(e) {
        const distLat = Math.abs(e.latlng.lat - _siteLat);
        const distLng = Math.abs(e.latlng.lng - _siteLon);
        if (distLat > 0.5 || distLng > 0.5) {
            document.getElementById('lm-map-hint').textContent = 'Too far from the site area. Click closer to the map center.';
            return;
        }
        setLandmarkPoint(e.latlng.lat, e.latlng.lng, '');
        document.getElementById('lm-name').focus();
    });

    // Search via Nominatim
    const searchInput = document.getElementById('lm-search-input');
    const searchResults = document.getElementById('lm-search-results');

    window.lmSearch = function() {
        const q = searchInput.value.trim();
        if (!q) return;
        const btn = document.getElementById('lm-search-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        const _r = 0.4;
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=8&countrycodes=us&viewbox=${_siteLon-_r},${_siteLat+_r},${_siteLon+_r},${_siteLat-_r}&bounded=1`;
        fetch(url, { headers: { 'Accept': 'application/json' } })
            .then(r => r.json())
            .then(results => {
                searchResults.innerHTML = '';
                if (results.length === 0) {
                    searchResults.innerHTML = '<div class="list-group-item text-muted small">No results found</div>';
                } else {
                    results.forEach(r => {
                        const item = document.createElement('a');
                        item.href = '#';
                        item.className = 'list-group-item list-group-item-action py-1 px-2';
                        item.innerHTML = `<div class="fw-semibold">${r.display_name.split(',').slice(0,3).join(', ')}</div>
                                          <div class="text-muted" style="font-size:0.65rem;">${r.type} &middot; ${parseFloat(r.lat).toFixed(4)}, ${parseFloat(r.lon).toFixed(4)}</div>`;
                        item.onclick = function(e) {
                            e.preventDefault();
                            const shortName = r.display_name.split(',')[0].trim();
                            setLandmarkPoint(parseFloat(r.lat), parseFloat(r.lon), shortName);
                            searchResults.style.display = 'none';
                            searchInput.value = shortName;
                        };
                        searchResults.appendChild(item);
                    });
                }
                searchResults.style.display = 'block';
            })
            .catch(() => {
                searchResults.innerHTML = '<div class="list-group-item text-danger small">Search failed</div>';
                searchResults.style.display = 'block';
            })
            .finally(() => {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-search"></i>';
            });
    };

    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); lmSearch(); }
    });

    document.addEventListener('click', function(e) {
        if (!searchResults.contains(e.target) && e.target !== searchInput) {
            searchResults.style.display = 'none';
        }
    });

    // Famous places dropdown
    window.lmFamousSelect = function(sel) {
        const category = sel.value;
        if (!category) return;
        searchInput.value = category;
        sel.selectedIndex = 0;
        lmSearch();
    };

    // Fix map rendering
    setTimeout(function() { lmMap.invalidateSize(); }, 200);

    // ── AJAX Add landmark ──────────────────────────────────────
    window.lmAdd = function(e) {
        e.preventDefault();
        const name = document.getElementById('lm-name').value.trim();
        const lat = document.getElementById('lm-lat').value;
        const lng = document.getElementById('lm-lng').value;
        if (!name || !lat || !lng) { alert('Name and coordinates are required.'); return false; }

        const fd = new FormData();
        fd.append('landmark_action', 'add');
        fd.append('landmark_name', name);
        fd.append('landmark_lat', lat);
        fd.append('landmark_lng', lng);

        fetch(PREFS_CONFIG.adminLandmarksUrl, {
            method: 'POST',
            body: fd,
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).then(r => r.json()).then(data => {
            if (data.ok) {
                rebuildLandmarkList(data.landmarks);
                document.getElementById('lm-name').value = '';
                document.getElementById('lm-lat').value = '';
                document.getElementById('lm-lng').value = '';
                document.getElementById('lm-map-hint').textContent = 'Landmark added!';
                if (pickerMarker) { lmMap.removeLayer(pickerMarker); pickerMarker = null; }
                const mk = L.marker([parseFloat(lat), parseFloat(lng)], {
                    icon: L.divIcon({className:'', html:'<i class="bi bi-geo-alt-fill" style="font-size:1.4rem;color:#dc2626;"></i>', iconSize:[20,28], iconAnchor:[10,28]})
                }).addTo(lmMap).bindTooltip(name, {permanent:false, direction:'top'});
                updatePoiDropdown(data.landmarks);
            } else {
                alert(data.error || 'Failed to add landmark.');
            }
        }).catch(err => alert('Error: ' + err.message));
        return false;
    };

    // ── AJAX Delete landmark ──────────────────────────────────
    window.lmDelete = function(name, btn) {
        if (!confirm('Remove landmark "' + name + '"?')) return;
        btn.disabled = true;

        const fd = new FormData();
        fd.append('landmark_action', 'delete');
        fd.append('landmark_name', name);

        fetch(PREFS_CONFIG.adminLandmarksUrl, {
            method: 'POST',
            body: fd,
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).then(r => r.json()).then(data => {
            if (data.ok) {
                rebuildLandmarkList(data.landmarks);
                updatePoiDropdown(data.landmarks);
            }
        }).catch(err => { btn.disabled = false; alert('Error: ' + err.message); });
    };

    // ── Rebuild the landmark list in-place ─────────────────────
    function rebuildLandmarkList(landmarks) {
        const list = document.getElementById('lm-list');
        const badge = document.getElementById('lm-count-badge');
        badge.textContent = landmarks.length;

        if (landmarks.length === 0) {
            list.innerHTML = '<p class="small text-muted mb-0" id="lm-empty-msg">No landmarks yet. Search, pick from the list, or click the map below.</p>';
            return;
        }
        let html = '';
        landmarks.forEach((lm, i) => {
            html += `<div class="d-flex align-items-center justify-content-between py-1 ${i < landmarks.length-1 ? 'border-bottom' : ''} lm-row" data-name="${lm.name}">
                <div class="d-flex align-items-center gap-2">
                    <span class="text-muted fw-bold" style="font-size:0.72rem; min-width:18px;">${i+1}.</span>
                    <div>
                        <span class="fw-semibold small">${lm.name}</span>
                        <span class="text-muted" style="font-size:0.65rem;"> ${lm.lat.toFixed(4)}, ${lm.lng.toFixed(4)}</span>
                    </div>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger py-0 px-1" style="font-size:0.65rem;"
                        onclick="lmDelete('${lm.name.replace(/'/g,"\\'")}', this)">
                    <i class="bi bi-trash"></i>
                </button>
            </div>`;
        });
        list.innerHTML = html;
    }

    // ── Update the POI dropdown in the scoring section ─────────
    function updatePoiDropdown(landmarks) {
        const sel = document.getElementById('proximity_poi_select');
        if (!sel) return;
        const currentVal = sel.value;
        while (sel.options.length > 1) sel.remove(1);
        landmarks.forEach(lm => {
            const opt = document.createElement('option');
            opt.value = lm.name;
            opt.textContent = lm.name;
            opt.dataset.lat = lm.lat;
            opt.dataset.lng = lm.lng;
            if (lm.name === currentVal) opt.selected = true;
            sel.appendChild(opt);
        });
    }
})();
}
