/* ─────────────────────────────────────────────
   File: app/static/js/help-hints.js
   App Version: 2026.03.14 | File Version: 1.1.0
   Last Modified: 2026-03-19
   ───────────────────────────────────────────── */

/**
 * Help Hints System
 *
 * Reads window.HF_HELP_LEVEL (1/2/3) and activates contextual help:
 *   Level 1 (Expert)  — no tooltips, hide all .help-hint elements
 *   Level 2 (Standard)— Bootstrap tooltips on [data-help] elements
 *   Level 3 (Guided)  — tooltips + show .help-hint inline elements
 */
(function () {
    'use strict';

    const level = window.HF_HELP_LEVEL || 2;

    document.addEventListener('DOMContentLoaded', function () {
        // ── Level 2+: Activate Bootstrap tooltips on [data-help] ──
        if (level >= 2) {
            document.querySelectorAll('[data-help]').forEach(function (el) {
                // Nav links: place tooltip below so it doesn't cover neighboring icons
                var placement = el.dataset.helpPlacement || 'top';
                if (el.classList.contains('nav-link')) {
                    placement = 'bottom';
                }
                el.setAttribute('data-bs-toggle', 'tooltip');
                el.setAttribute('data-bs-placement', placement);
                el.setAttribute('title', el.dataset.help);
                new bootstrap.Tooltip(el, {
                    trigger: 'hover focus',
                    delay: { show: 400, hide: 100 },
                    html: false,
                });
            });
        }

        // ── Level 3: Show inline .help-hint elements ──────────────
        if (level >= 3) {
            document.querySelectorAll('.help-hint').forEach(function (el) {
                el.classList.remove('d-none');
            });
        }

        // ── Level 1: Ensure hints are hidden (they are by default) ──
        if (level < 3) {
            document.querySelectorAll('.help-hint').forEach(function (el) {
                el.classList.add('d-none');
            });
        }
    });
})();
