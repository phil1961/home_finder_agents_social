# Mobile & PWA Strategy — HomeFinder Social

Last updated: 2026-03-15

## Current State: Progressive Web App (PWA)

HomeFinder Social runs as a PWA — a website that can be installed on a phone's home screen and behaves like a native app. No app store submission, no build toolchain, no separate codebase.

### What's Deployed

| Component | File | Purpose |
|-----------|------|---------|
| Web App Manifest | `app/static/manifest.json` | App name, icons, theme, display mode |
| Service Worker | `app/static/sw.js` | Caches static assets, network-first HTML |
| App Icons | `app/static/icons/icon-192.png`, `icon-512.png` | Home screen + splash icons |
| Mobile CSS | `app/static/css/style.css` | Responsive layout, touch targets |
| SW Route | `/sw.js` (Flask route in `__init__.py`) | Serves SW from app root for correct scope |

### How Users Install It

**Android (Chrome):**
1. Visit any page on the site
2. Chrome may show an "Add to Home Screen" banner automatically
3. Or: tap the three-dot menu > "Add to Home Screen"
4. Icon appears on home screen, opens in standalone mode

**iOS (Safari):**
1. Visit any page on the site
2. Tap the share button (box with arrow)
3. Tap "Add to Home Screen"
4. Icon appears on home screen, opens in standalone mode

### What the PWA Provides

**Manifest (`manifest.json`):**
- App name: "HomeFinder Social"
- Short name: "HomeFinder"
- Display: standalone (no browser chrome)
- Theme color: #1a1a2e (dark ink)
- Background color: #1a1a2e
- Start URL: `/home_finder_agents_social/welcome`
- Scope: `/home_finder_agents_social/`
- Icons: 192px and 512px with maskable purpose

**Service Worker (`sw.js`):**
- Cache name: `homefinder-v1`
- Static assets: cache-first (CSS, icons load instantly after first visit)
- HTML pages: network-first with cache fallback (pages load from network, fall back to cache if offline)
- Activates immediately (`skipWaiting` + `clients.claim`)
- Old caches cleaned on activation

**Mobile CSS (3 breakpoints):**
- `>= 992px` (desktop): stacked icon-over-text nav links
- `< 992px` (tablet/phone): larger touch targets (10px padding), hamburger menu, listing cards stack photo on top, modals nearly full-width, maps fill viewport
- `< 576px` (small phone): tighter feature tags, single-column power grid on welcome page, stacked role pills, wrapped source badges
- PWA standalone mode: extra padding for `env(safe-area-inset-top)` (notch phones)
- Safe area bottom padding for iPhone home indicator

**Meta Tags (in `base.html` and `welcome.html`):**
- `<meta name="mobile-web-app-capable" content="yes">`
- `<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">`
- `<meta name="apple-mobile-web-app-title" content="HomeFinder">`
- `<meta name="theme-color" content="#1a1a2e">`
- `<link rel="apple-touch-icon" ...>` for iOS icon
- `<link rel="manifest" ...>` for the web app manifest

---

## What the PWA Does NOT Provide

| Capability | Status | Why |
|-----------|--------|-----|
| App Store presence | Not available | PWAs are installed from the browser, not searchable in stores |
| Push notifications | Not implemented | Service worker supports it, but subscription flow + server push not built |
| Camera integration | Basic only | "Add a Home" uses standard file picker, not native camera API |
| GPS "homes near me" | Not implemented | Browser geolocation API available but not wired up |
| Offline listing data | Not implemented | SW caches pages but not listing JSON data |
| Background sync | Not implemented | Could sync flags/shares when connection returns |

---

## Roadmap

### Tier 1: Quick Wins (No New Infrastructure)

**Install Prompt Banner**
- Show a dismissible banner on the dashboard: "Add HomeFinder to your home screen for the best experience"
- Only show to mobile users who haven't installed yet
- Use the `beforeinstallprompt` event (Chrome) or detect standalone mode
- Cookie-based dismiss so it doesn't nag

**"Homes Near Me" Sort**
- Add a sort option to the dashboard filter bar: "Nearest to Me"
- Use `navigator.geolocation.getCurrentPosition()` to get the user's lat/lng
- Sort listings by Haversine distance from their current position
- Show distance on each listing card (like the POI distance badge)
- Permission prompt is handled by the browser

**Offline Recent Listings**
- Cache the last 20 listing detail pages in the service worker
- When offline, show a banner "You're offline — showing cached data" and serve cached pages
- Dashboard won't load (requires live DB query), but detail pages you've visited will work

**Estimated effort:** 1-2 hours each. No server changes for install prompt or geolocation.

### Tier 2: Push Notifications (Moderate Effort)

**What it enables:**
- Street Watch alerts pushed to the phone instantly
- "Someone reacted to your share" notifications
- Price drop alerts on favorited listings
- Weekly digest as a push instead of (or in addition to) email

**What's needed:**
- Web Push API integration in the service worker
- `PushSubscription` storage per user in the DB (new model: `UserPushSubscription`)
- Server-side push sending via `pywebpush` library (VAPID keys)
- UI: "Enable Notifications" toggle in user settings
- Trigger points: Street Watch match, social reaction, price drop detection

**Platform support:**
- Android Chrome: full support, reliable
- iOS Safari: supported since iOS 16.4 (2023), but requires the PWA to be installed (Add to Home Screen). Limited — no badges, no sounds, no background refresh.
- Desktop Chrome/Firefox/Edge: full support

**Estimated effort:** 2-3 days. New DB model, VAPID key setup, push trigger wiring.

### Tier 3: Native App Store Presence (When You Have Users)

**Approach: Capacitor wrapper**
- [Capacitor](https://capacitorjs.com/) (by Ionic, free/open source) wraps a web app in a native shell
- Your Flask app stays as-is — Capacitor loads it in a WebView
- Native plugins for: push notifications (Firebase Cloud Messaging), camera, geolocation, biometrics
- Submit to Google Play Store and Apple App Store

**What it adds over PWA:**
- App Store discoverability (users search "HomeFinder" and find you)
- Ratings and reviews
- Real push notifications on iOS (not limited like web push)
- Native camera for "Add a Home" photo capture
- Biometric login (Face ID, fingerprint)
- App update prompts

**What's needed:**
- Capacitor project setup (wraps your production URL)
- Firebase project for push notifications
- Apple Developer account ($99/year) for App Store
- Google Play Developer account ($25 one-time) for Play Store
- App Store review process (1-2 weeks for initial approval)
- Ongoing: app store metadata, screenshots, privacy policy

**Estimated effort:** 1-2 weeks for wrapper + store submission. Ongoing maintenance for app updates and store compliance.

---

## Current File Inventory

```
app/
  static/
    manifest.json          — PWA manifest
    sw.js                  — Service worker
    icons/
      icon-192.png         — Home screen icon
      icon-512.png         — Splash screen icon
    css/
      style.css            — Mobile responsive CSS (lines 62-170)
  __init__.py              — /sw.js route (serves SW from app root)
  templates/
    base.html              — PWA meta tags, SW registration
    dashboard/
      welcome.html         — PWA meta tags, SW registration (standalone page)
```

## Decision Framework

| Signal | Action |
|--------|--------|
| You're the only user | Stay with PWA (current state) |
| First paying customer asks about mobile | Build Tier 1 (install prompt, GPS sort) |
| Users complain about missing notifications | Build Tier 2 (web push) |
| Users say "I looked for you in the App Store" | Build Tier 3 (Capacitor wrapper) |
| Competitor has a native app | Build Tier 3 |

The PWA is the right foundation. Each tier builds on the previous one without throwaway work — the Capacitor wrapper in Tier 3 loads the same web app that Tier 1 and 2 improved.
