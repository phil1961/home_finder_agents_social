<!--
  File: docs/master/UI_SPECIFICATION.md
  App Version: 2026.03.15 | File Version: 1.1.0
  Last Modified: 2026-03-15
-->

# UI Specification -- HomeFinder Social

Version: 2026-03-15

---

## 1. Design System

### 1.1 Color Palette

| Token       | Hex       | Usage                                                    |
|-------------|-----------|----------------------------------------------------------|
| `--ink`     | `#1a1a2e` | Primary dark: navbar background, hero section, body text |
| `--gold`    | `#c9a84c` | Accent: headings, labels, hover states, hero highlights  |
| `--cream`   | `#faf8f2` | Welcome page body background                            |
| `--rule`    | `#e2d9c5` | Borders, dividers, card outlines on welcome page         |
| `--slate`   | `#4a5568` | Secondary text, descriptions, muted content              |
| `--social`  | `#f093fb` | Social features accent (share icon, points badge)        |
| `--green`   | `#22c55e` | Neighborhood Tips accent, friend listing borders         |

**Source badges:**
- Zillow: `#006AFF` background, white text
- Realtor: `#D92228` background, white text
- Agent/Community: Bootstrap `.bg-secondary`

**Score ring colors (per-user composite):**
- High (>= 75): background `#d1fae5`, text `#065f46`, border `#10b981`
- Mid (>= 50): background `#dbeafe`, text `#1e40af`, border `#3b82f6`
- Low (< 50): background `#fee2e2`, text `#991b1b`, border `#ef4444`

**Admin nav icon color:** `#94a3b8` (slate-400) -- used for all right-side admin nav items

**Left nav icon colors (pastel palette):**
- Dashboard: `#7dd3fc` (sky-300)
- Map: `#86efac` (green-300)
- Digest: `#fcd34d` (amber-300)
- Favorites: `#fbbf24` (amber-400)
- Watch: `#c4b5fd` (violet-300)
- Social: `#f0abfc` (fuchsia-300)
- Tour: `#fdba74` (orange-300)
- Preferences: `#a5b4fc` (indigo-300)
- Contact Agent: `#67e8f9` (cyan-300)
- Help: `#d9f99d` (lime-200)

**Street Watch accent:** `#8b5cf6` (violet-500)
**Share & Collect accent:** `#667eea` (indigo-400)

### 1.2 Typography

- **Font family:** `'Segoe UI', system-ui, sans-serif` (welcome page explicitly); Bootstrap 5 defaults elsewhere
- **Navbar brand:** `font-weight: 700`
- **Nav link text (desktop):** `0.72rem`, stacked icon-over-text layout
- **Nav link text (mobile):** `0.95rem`, inline icon + text
- **Feature tags:** `0.7rem`, `2px 6px` padding
- **Stat labels:** `0.65rem`, uppercase, `letter-spacing: 0.5px`, color `#6b7280`
- **Stat values:** `1.1rem`, `font-weight: 600`
- **Cross-reference links:** `0.75rem`
- **Welcome page hero h1:** `clamp(1.8rem, 4vw, 2.8rem)`, `font-weight: 800`
- **Welcome page section labels:** `0.68rem`, `letter-spacing: 3px`, uppercase, gold color, `font-weight: 600`

### 1.3 Component Patterns

**Cards:**
- `border-radius: 10px` (global `.card` override)
- Listing cards: `border: 0`, `.shadow-sm`, great-deal variant has `border-left: 4px solid #198754`
- Sidebar cards: `border: 0`, `.shadow-sm`

**Score ring (dashboard card):**
- `width: 48px`, `height: 48px`, `border-radius: 50%`
- `font-weight: 700`, `font-size: 0.85rem`
- Color classes: `.score-high`, `.score-mid`, `.score-low`
- Mobile: `42px x 42px`, `font-size: 0.8rem`

**Score ring (detail page):**
- Large `<h2>` text with color utility classes
- Sub-scores displayed as progress bars (6px height) with color-coded fills

**Badges:**
- `font-weight: 500` (global override)
- Source badges: Zillow blue, Realtor red
- Feature tags: `.bg-secondary`, `font-size: 0.7rem`, `padding: 2px 6px`
- POI distance badge: color varies by distance (green <= 2mi, primary <= 5mi, warning <= 10mi, danger > 10mi)
- Neighborhood Tip badge: `background: #dcfce7`, `color: #166534`, `font-size: 0.6rem`
- Share count badge: `.bg-primary`, `font-size: 0.55rem`
- Points badge in nav: `background: #f093fb`, `font-size: 0.6rem`, gem icon

**Modals:**
- All modals use `modal-dialog-centered`
- Welcome modal and Join modal: `border-0`, `shadow-lg`
- Share modals: `modal-sm`
- Contact Agent modal: standard centered
- Mobile: `margin: 8px`, max-width `calc(100vw - 16px)`

**Listing card layout (desktop):**
- Two-column grid (`.col-lg-6`)
- Horizontal layout: 140px photo on left, card body on right
- Photo: `border-radius: 10px 0 0 10px`, `object-fit: cover`, `loading="lazy"`
- Fallback: gray bg with house icon if no photo

**Listing card layout (mobile):**
- Full-width cards
- Photo stacks on top: `width: 100%`, `height: 160px`, `border-radius: 10px 10px 0 0`

### 1.4 Responsive Breakpoints

| Breakpoint       | Value       | Behavior                                                  |
|------------------|-------------|-----------------------------------------------------------|
| Desktop nav      | >= 992px    | Stacked icon-over-text nav links, two-column listing grid |
| Mobile nav       | < 992px     | Hamburger collapse, full-width nav links, 10px padding    |
| Small phone      | < 576px     | Single-column power grid, vertical role pills, tighter feature tags |
| PWA standalone   | `display-mode: standalone` | Extra `env(safe-area-inset-top)` padding |
| Safe area insets | `@supports` | Bottom padding for notch phones                           |

### 1.5 PWA Configuration

- `<meta name="mobile-web-app-capable" content="yes">`
- `<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">`
- `<meta name="theme-color" content="#1a1a2e">`
- Manifest: `/static/manifest.json`
- Apple touch icon: `/static/icons/icon-192.png`
- Service worker: `/home_finder_agents_social/sw.js` (scope: `/home_finder_agents_social/`)
- Service worker registered on every page (base.html and welcome.html)

---

## 2. Navigation

### 2.1 Navbar Structure

The navbar is a Bootstrap 5 `navbar-dark bg-dark` inside a `.container`. It collapses at 992px.

**Agent branding override:** When a logged-in user has an `assigned_agent`, the navbar background color changes to the agent's `brand_color` via an inline `<style>` tag. The brand in the navbar shows the agent's name, icon/logo, and optional tagline with configurable style (plain, italic, bold, caps, badge, elegant).

**Twemoji:** Brand emoji in the navbar and elements with `.twemoji-parse` are parsed into SVG via Twemoji CDN on `DOMContentLoaded`.

### 2.2 Left Nav Items (All Users)

These items are always visible regardless of authentication state:

| Item        | Icon                    | Icon Color | Route                                    |
|-------------|-------------------------|------------|------------------------------------------|
| Dashboard   | `bi-grid`               | `#7dd3fc`  | `dashboard.index`                        |
| Map         | `bi-geo-alt`            | `#86efac`  | `dashboard.map_view`                     |
| Digest      | `bi-newspaper`          | `#fcd34d`  | `dashboard.digest`                       |
| Favorites   | `bi-star`               | `#fbbf24`  | `dashboard.index` with `?flag=favorite`  |
| Watch       | `bi-eye`                | `#c4b5fd`  | `dashboard.watch_manage`                 |
| Social (dd) | `bi-share`              | `#f0abfc`  | Dropdown (see below)                     |
| Tour*       | `bi-map`                | `#fdba74`  | `dashboard.itinerary`                    |
| Preferences | `bi-sliders`            | `#a5b4fc`  | `dashboard.preferences`                  |
| Contact**   | `bi-chat-dots`          | `#67e8f9`  | Opens `#contactAgentModal`               |
| Help (dd)   | `bi-question-circle`    | `#d9f99d`  | Dropdown (see below)                     |

*Tour only visible when authenticated
**Contact Agent only visible when authenticated AND user has an assigned_agent

### 2.3 Social Dropdown

**Authenticated users:**
- Shared With Me (`bi-inbox`)
- My Shares (`bi-send`)
- ---
- My Collections (`bi-collection`)
- Neighborhood Tips (`bi-house-add`)
- ---
- My Points (`bi-gem`)
- Leaderboard (`bi-trophy`)
- ---
- Refer a Friend (`bi-people`)
- Social Analytics* (`bi-graph-up`) -- *only if `current_user.is_admin`*

**Points badge:** If user has `points_account.balance > 0`, a pink pill badge (`background: #f093fb`) appears next to "Social" showing the gem icon and balance.

**Guest users:**
- Neighborhood Tips (`bi-house-add`)
- Muted text: "Sign in for more social features"

### 2.4 Help Dropdown

- Help & Guide (`bi-book`) -- `dashboard.help_page`
- Version number (muted, `0.7rem`) -- from `app_version` context variable
- ---
- Why HomeFinder? (Buyers) (`bi-person`) -- `dashboard.why_user`
- Why HomeFinder? (Agents) (`bi-briefcase`) -- `dashboard.why_agent`
- Owner Operations Guide* (`bi-shield-check`) -- `dashboard.why_owner` -- *only if `current_user.is_owner`*

### 2.5 Right Nav Items (Authenticated)

**Owner/Master items** (visible when `current_user.is_owner`):

| Item     | Icon                  | Icon Color | Route                    |
|----------|-----------------------|------------|--------------------------|
| Admin    | `bi-shield-check`     | `#94a3b8`  | `dashboard.admin_agents` |
| Users    | `bi-people-fill`      | `#94a3b8`  | `dashboard.admin_users`  |
| Metrics  | `bi-bar-chart-line`   | `#94a3b8`  | `dashboard.admin_metrics`|
| Billing  | `bi-credit-card`      | `#94a3b8`  | `dashboard.admin_billing`|
| Prompts  | `bi-pencil-square`    | `#94a3b8`  | `dashboard.admin_prompts`|

**Master-only items** (visible when `current_user.is_master`):

| Item   | Icon         | Icon Color | Route                                             |
|--------|--------------|------------|----------------------------------------------------|
| Sites  | `bi-globe2`  | `#94a3b8`  | `/home_finder_agents_social/welcome?chooser=1`     |
| Manage | `bi-gear`    | `#94a3b8`  | `site_manager.sites_list` (uses `url_for`, not `site_url`) |

**Agent items** (visible when `current_user.is_agent`):

| Item       | Icon              | Icon Color | Route                     |
|------------|-------------------|------------|---------------------------|
| My Clients | `bi-people`       | `#94a3b8`  | `dashboard.agent_dashboard`|
| Prompts    | `bi-pencil-square` | `#94a3b8` | `dashboard.agent_prompts` |

**Admin items** (visible when `current_user.is_admin`, i.e., owner, agent, or master):

| Item | Icon              | Icon Color | Route       |
|------|-------------------|------------|-------------|
| Docs | `bi-folder2-open` | `#94a3b8`  | `docs.index`|

**Masquerade indicator** (visible when `session['masquerade_original_id']` is set):
- "End Preview" link with warning text color, `bi-eye-slash` icon
- Routes to `auth.end_masquerade`

**User dropdown** (always visible when authenticated):
- User email (muted text)
- ---
- **Switch Role** section (master only, not during masquerade): lists all sibling accounts sharing the same email, each with a role badge and colored icon. Clicking a sibling triggers one-click masquerade via `auth.masquerade`. Populated by the `inject_siblings` context processor.
- ---
- Close Account (`bi-x-circle`) -- `auth.close_account`
- Sign Out (`bi-box-arrow-right`) -- `auth.logout`

### 2.6 Right Nav Items (Guest)

| Item               | Icon                     | Route            |
|--------------------|--------------------------|------------------|
| Sites              | `bi-globe2`              | Welcome chooser  |
| Sign In            | `bi-box-arrow-in-right`  | `auth.login`     |
| Create Free Account| (outline button)         | `auth.register`  |

### 2.7 Mobile Hamburger Behavior

- Toggler button: `.navbar-toggler`, target `#navMain`
- Collapse: `.collapse .navbar-collapse`
- Mobile nav links: `padding: 10px 16px`, `font-size: 0.95rem`, bottom border `rgba(255,255,255,0.06)`
- Mobile icons: `width: 24px`, `text-align: center`, `margin-right: 8px`
- Mobile dropdown items: `padding: 10px 20px`

### 2.8 Desktop Stacked Layout

At >= 992px, nav links use `flex-direction: column` with icon (`1.1rem`) above text (`0.72rem`), centered. Dropdown caret is repositioned with `margin-left: 2px`.

---

## 3. Role Visibility Matrix

### 3.1 Role Definitions

| Role      | DB Value    | `is_master` | `is_owner` | `is_agent` | `is_admin` | `is_principal` | `is_client` |
|-----------|-------------|-------------|------------|------------|------------|----------------|-------------|
| Master    | `master`    | True        | True       | False      | True       | False           | False       |
| Owner     | `owner`     | False       | True       | False      | True       | False           | False       |
| Agent     | `agent`     | False       | False      | True       | True       | False           | False       |
| Principal | `principal` | False       | False      | False      | False      | True            | False       |
| Client    | `client`    | False       | False      | False      | False      | False           | True        |
| Guest     | (no account)| N/A         | N/A        | N/A        | N/A        | N/A             | N/A         |

### 3.2 Capability Matrix

| Capability                        | Guest | Client | Principal | Agent | Owner | Master |
|-----------------------------------|-------|--------|-----------|-------|-------|--------|
| Browse listings/map/detail        | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Toggle flags (fav/maybe/hide)     | Session| Yes   | Yes       | Yes   | Yes   | Yes    |
| Save listing notes/itinerary      | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| AI: analyze listing               | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| AI: analyze portfolio             | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| AI: analyze preferences           | No    | Yes    | No        | Yes   | Yes   | Yes    |
| Edit own preferences              | Session| Yes   | Yes*      | Yes   | Yes   | Yes    |
| Edit avoid_areas in preferences   | No    | No     | No        | No    | No    | Yes    |
| Edit target_areas in preferences  | No    | No     | No        | No    | No    | Yes    |
| Contact assigned agent             | No    | No     | Yes       | No    | No    | No     |
| Share listings                    | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Social: Shared With Me            | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| Social: My Shares                 | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| Social: Collections               | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| Social: Add a Home                | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| Social: Neighborhood Tips (view)  | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Social: Points History            | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| Social: Leaderboard               | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| Social: Referral Dashboard        | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| Social: Analytics                 | No    | No     | No        | Yes   | Yes   | Yes    |
| Social: Send Digest               | No    | No     | No        | No    | Yes   | Yes    |
| Tour/Itinerary                    | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| Street Watch                      | Yes** | Yes    | Yes       | Yes   | Yes   | Yes    |
| Agent Dashboard                   | No    | No     | No        | Yes   | Yes   | Yes    |
| Create client accounts            | No    | No     | No        | Yes   | Yes   | Yes    |
| Edit client preferences           | No    | No     | No        | Yes   | Yes   | Yes    |
| Agent branding                    | No    | No     | No        | Yes   | No    | No     |
| Agent prompt overrides            | No    | No     | No        | Yes   | Yes   | Yes    |
| Agent: Add Listing                | No    | No     | No        | Yes   | No    | No     |
| Agent: Review friend listings     | No    | No     | No        | Yes   | Yes   | Yes    |
| Trigger pipeline fetch            | No    | No     | No        | Yes   | Yes   | Yes    |
| Admin: Agents page                | No    | No     | No        | No    | Yes   | Yes    |
| Admin: Users page                 | No    | No     | No        | No    | Yes   | Yes    |
| Admin: Metrics                    | No    | No     | No        | No    | Yes   | Yes    |
| Admin: Diagnostics                | No    | No     | No        | No    | Yes   | Yes    |
| Admin: Billing                    | No    | No     | No        | No    | Yes   | Yes    |
| Admin: Owner prompts              | No    | No     | No        | No    | Yes   | Yes    |
| Admin: Landmark management        | No    | No     | No        | No    | Yes   | Yes    |
| Admin: Toggle scheduler           | No    | No     | No        | No    | Yes   | Yes    |
| Cross-site navigation             | No    | No     | No        | No    | No    | Yes    |
| Site Manager (CRUD)               | No    | No     | No        | No    | No    | Yes    |
| Masquerade as any user            | No    | No     | No        | No    | No    | Yes    |
| Masquerade as own clients         | No    | No     | No        | Yes   | No    | No     |
| Docs folder access                | No    | No     | No        | Yes   | Yes   | Yes    |

*Principal users can now edit their own scoring weights (last save wins vs agent edits).
**Guests use email-based watches stored in session.

### 3.3 Nav Visibility Summary

| Nav Item       | Guest | Client | Principal | Agent | Owner | Master |
|----------------|-------|--------|-----------|-------|-------|--------|
| Dashboard      | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Map            | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Digest         | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Favorites      | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Watch          | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Social (dd)    | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Tour           | No    | Yes    | Yes       | Yes   | Yes   | Yes    |
| Preferences    | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Contact Agent  | No    | No     | Yes*      | No    | No    | No     |
| Help (dd)      | Yes   | Yes    | Yes       | Yes   | Yes   | Yes    |
| Admin          | No    | No     | No        | No    | Yes   | Yes    |
| Users          | No    | No     | No        | No    | Yes   | Yes    |
| Metrics        | No    | No     | No        | No    | Yes   | Yes    |
| Billing        | No    | No     | No        | No    | Yes   | Yes    |
| Prompts (owner)| No    | No     | No        | No    | Yes   | Yes    |
| My Clients     | No    | No     | No        | Yes   | No    | No     |
| Prompts (agent)| No    | No     | No        | Yes   | No    | No     |
| Docs           | No    | No     | No        | Yes   | Yes   | Yes    |
| Sites          | Yes   | No     | No        | No    | No    | Yes    |
| Manage         | No    | No     | No        | No    | No    | Yes    |
| End Preview    | No    | No     | No        | Masq  | No    | Masq   |
| Sign In        | Yes   | No     | No        | No    | No    | No     |
| Create Account | Yes   | No     | No        | No    | No    | No     |
| User dropdown  | No    | Yes    | Yes       | Yes   | Yes   | Yes    |

*Only clients/principals with an assigned_agent see Contact Agent.

---

## 4. Pages

### 4.1 Welcome Page (`/welcome`)

**URL:** `/<prefix>/welcome` or `/<prefix>/site/<key>/welcome`
**Access:** Everyone. Authenticated users with site context are redirected to dashboard unless `?chooser=1` is passed.
**Template:** `dashboard/welcome.html` (standalone, does not extend `base.html`)

**Layout:**
1. **Custom nav bar** -- ink background, brand "HomeFinder Social" with gold house icon, two links ("Jump to Markets", "Choose a Market")
2. **Hero section** -- ink background with radial gold gradient overlay
   - Gold label: "AI-Powered Home Discovery"
   - H1: "Find your next home. Share the journey." (Share in gold)
   - Gold rule (40px x 3px)
   - Sub-text describing features
   - "Skip to markets" link with down-arrow icon
3. **Powers grid** -- white background with top/bottom borders
   - Label: "What You Can Do"
   - Heading: "More than a listing search. A home-finding platform."
   - 8 power cards in auto-fill grid (minmax 220px, 1fr), max-width 960px
   - Each card: colored icon box (40x40, rounded-10), h6 title, description, "Learn more" toggle revealing detail with bullet list
   - Cards: AI Deal Analysis, Share With Anyone, Add a Home, Earn Points, Build Collections, Plan Tours, Street Watch, Social Proof
4. **Roles strip** -- cream background
   - Four role pills: Buyers (blue), Agents (green), Owners (purple), Guests (slate)
   - Each pill: icon + role name + description
   - Sub-text: "No credit card. No sign-up wall..."
5. **Site picker** -- `#markets` anchor
   - Label: "Available Markets"
   - Heading: "Where are you searching?"
   - Site cards in auto-fill grid (minmax 260px, 1fr), max-width 900px
   - Each card: gold geo icon, city name, listing count, features line, "Start exploring" arrow
   - Cards have hover animation: translateY(-2px), gold border, shadow, top gold bar scaleX
   - Empty state: building icon, "No active markets" message
6. **Footer** -- ink background, links to markets and agent signup

**Data source:** `get_all_sites()` from registry, filtered to `active` sites. Each site shows `listing_count`.

### 4.2 Registration (`/auth/register`)

**URL:** `/<prefix>/site/<key>/auth/register`
**Access:** Everyone (unauthenticated users)
**Layout:** Centered card form with fields for username, email, password. Links to login. Referral code from session is auto-applied.

### 4.3 Login (`/auth/login`)

**URL:** `/<prefix>/site/<key>/auth/login`
**Access:** Everyone (unauthenticated users)
**Layout:** Centered card form with username/password fields, "Remember me" checkbox, forgot password link.

### 4.4 Dashboard (`/`)

**URL:** `/<prefix>/site/<key>/`
**Access:** Everyone
**Template:** `dashboard/index.html` (extends `base.html`)

**Layout (top to bottom):**

1. **Agent branding banner** (conditional: authenticated user with assigned_agent)
   - Gradient background using agent's brand color
   - Agent icon, name, "is here to help" text
   - "Message" button opening contact modal

2. **Since-your-last-visit banner** (conditional)
   - Green gradient background
   - Authenticated: shows new listing count (green badge), price drop count (yellow badge), total scored
   - Guest: shows total scored listings and top deal score

3. **Header row**
   - Site display name with house icon
   - Listing count and current area filter

4. **Filter bar** (card with shadow)
   - Row of filter controls, each with label + select/input:
     - **Area:** dropdown of target area names + "All Areas", auto-submit on change
     - **Sort:** Deal Score (default), Price asc, Price desc, Newest, Yard Size, Nearest to Me, auto-submit
     - **Flag:** All, Favorites, Maybe, Hidden, auto-submit
     - **Source:** All Sources, Zillow, Realtor.com, auto-submit
     - **Min Score:** number input (0-100)
     - **Max Mi:** distance filter dropdown (Any, 0.5, 1, 2, 3, 5, 10, 15, 25 mi) -- only visible when user has a POI landmark selected
     - **Filter button:** primary, funnel icon

5. **Street Watch widget** (conditional: user has active watches)
   - Card with purple left border (`#8b5cf6`)
   - Shows watch count badge, up to 8 street name pills, "+N more" if > 8
   - "Manage" link to watch page

6. **AI Portfolio Analyst** (conditional: filtering by flag AND listings exist)
   - Card with robot icon, description text
   - Authenticated: "Analyze [Favorites/Maybes/Hidden]" primary button triggers AJAX analysis
   - Guest: outline button triggers join modal
   - Results area (hidden until analysis runs): headline, ranking, patterns, strategy, dark horse, bottom line
   - Cached results pre-populated on page load from `CachedAnalysis`
   - AJAX POST to `dashboard.analyze_portfolio_route`, returns JSON
   - Loading state: spinner with "Claude is reviewing all N properties..."
   - Error state: alert-danger div

7. **Most Shared This Week** (conditional: any shares exist in past 7 days)
   - Horizontal scroll row of up to 5 listing mini-cards (200px wide)
   - Each card: photo (100px height), address, price, share count badge
   - Fire icon header with "Most Shared This Week"

8. **Neighborhood Tips** (conditional: active friend listings exist)
   - Horizontal scroll row of up to 5 friend listing mini-cards (220px wide)
   - Green left border (3px solid `#22c55e`)
   - Each card: photo, address, price, beds/baths, green "Neighborhood Tip" badge
   - "View all" link to `social.friend_listings`

9. **Listing cards** (main grid, `.row` with `.col-lg-6`)
   - Max 100 listings displayed (after all filtering and scoring)
   - Each card contains:
     - **Photo** (140px wide, left side on desktop): large variant loaded, fallback to original, then to house icon placeholder
     - **Score ring:** per-user composite score with color coding
     - **Address** as link to detail page
     - **Area/city, zip code**
     - **Place name badge** (if Census place available): blue-tinted pill
     - **Flag emoji** (if favorite or maybe)
     - **Price** (primary color, h5)
     - **Stats row:** beds, baths, sqft, lot sqft
     - **Feature tags:** Garage, Porch, Patio, Above Flood Plain, year built, POI distance
     - **Source badge + cross-reference links:** links to original source and the other source
     - **Action buttons (right side):**
       - Share button (opens per-listing share modal) with share count badge
       - Favorite, Maybe, Hide flag toggle buttons (form POST)

10. **Empty state** (when no listings match filters)
    - Search icon, "No listings match your filters"
    - Agent context: shows agent card with message suggesting browsing
    - No agent: "Clear filters" link

11. **Per-listing share modal** (one per listing card)
    - Modal-sm dialog
    - Header: "Share Listing"
    - Form fields:
      - Guest: sender name (required), sender email (required)
      - Recipient email (required)
      - Recipient name (optional)
      - Relationship dropdown: Friend, Family, Coworker, Neighbor
      - Personal message textarea
    - Footer: "Link" button (copies shareable URL via AJAX), "Share" submit button
    - Form POSTs to `social.share_listing`

**AJAX behaviors:**
- Filter selects auto-submit form (page reload)
- **Nearest to Me sort:** Selecting this option triggers `navigator.geolocation.getCurrentPosition()` (cached 5 min). A spinner replaces the filter button text while waiting for GPS. On success, hidden `user_lat`/`user_lng` fields are set and the form submits. On denial or timeout, sort falls back to Deal Score. Hidden fields are preserved across subsequent filter changes. Listings display a walking-person distance badge (green <= 2 mi, blue <= 5 mi, amber <= 10 mi, red > 10 mi).
- Share link copy: AJAX GET to `social.copy_link`, copies to clipboard, shows toast notification
- Portfolio analysis: AJAX POST, results painted into DOM without reload
- Flag toggle: form POST, full page reload

**Data flow:**
- Listings fetched with SQLAlchemy query, filtered by zip codes from site registry, area, source, flag
- Per-user composite scores computed via `DealScore.compute_user_composite(user_prefs)`
- Guest prefs loaded from session, authenticated from `user.get_prefs()`
- Hidden listings excluded by default (unless explicitly filtering for hidden)
- Sorted by user composite (default), price asc/desc, newest, or yard size
- POI distances computed via Haversine if user has proximity landmark selected

### 4.5 Listing Detail (`/listing/<id>`)

**URL:** `/<prefix>/site/<key>/listing/<id>`
**Access:** Everyone
**Template:** `dashboard/detail.html` (extends `base.html`)

**Layout:** Two-column (`.col-lg-8` main, `.col-lg-4` sidebar)

**Main column (left):**

1. **Breadcrumb:** Dashboard > [address]

2. **Address + location:** h3 address, area/city/zip, Census place badge

3. **Price:** h2 in primary color

4. **Photo gallery:**
   - Single photo: full-width rounded image (max-height 500px)
   - Multiple: Bootstrap carousel with indicators and prev/next controls
   - Photos use large variant with fallback to original
   - Photo count shown below

5. **Stats row:** Beds, Baths, Sqft, Lot Sqft, Built year -- each in `.stat-block` (centered, gray bg, rounded)

6. **Feature tags:** Garage, Porch, Patio, Above Flood Plain, FEMA Zone

7. **Mini map** (conditional: listing has lat/lng)
   - Leaflet map, 250px height, rounded-10, scroll wheel zoom disabled
   - Score-colored circle marker with score number
   - Popup with address and price
   - Landmark markers: red star icons with tooltip on hover
   - **Zoom buttons:** Street (19), Block (16), Neighborhood (14, default), Area (12)
   - Zoom buttons sync with map zoom events
   - Links: "Map with Landmarks" (Google Maps directions through all landmarks), "Google Maps" (direct link)
   - Google Maps link URL updates when zoom changes
   - Landmark tooltip: `font-size: 0.72rem`, `font-weight: 700`, red border, white bg

8. **Source + cross-reference links:**
   - Source badge (Zillow blue or Realtor red)
   - Buttons: Open on [source], Find on [other source], Google Maps

9. **Description** (conditional): pre-formatted text in card

10. **Property Details** (conditional: enriched from API detail endpoint)
    - Collapsible card with chevron toggle
    - Sections displayed in two-column grid: category label (uppercase, muted) + bulleted list

11. **Price History** (conditional: has price changes)
    - Canvas chart (120px height) drawn with vanilla JS
    - Table: Date, Price, Change (green down/red up arrows), Event badge (Listed, Reduced, Increased, Current)
    - Total change summary with percentage

12. **AI Deal Analyst**
    - Card with "Analyze This Deal" button
    - Authenticated: primary button triggers AJAX POST to `dashboard.analyze_listing`
    - Guest: outline button triggers join modal
    - Results area: verdict badge (Strong Buy green / Worth Considering yellow / Pass red), summary, strengths, concerns, negotiation strategy
    - Cached results pre-populated on page load
    - "Showing saved analysis -- refresh" link when cached
    - Disclaimer: "AI analysis is advisory only..."
    - Timestamp of analysis

**Sidebar (right):**

1. **Deal Score panel** (conditional: listing has deal_score)
   - Large colored score number (green >= 75, primary >= 50, red < 50) out of /100
   - Sub-score progress bars (6px height): Price, House Size, Yard Size, Features, Flood Risk, Year Built, Single Story, Price/Sqft, Days on Market, HOA Fee, Near Medical, Near Grocery, Community Pool, Property Tax, Lot Ratio, Price Trend, Walkability
   - POI proximity row (conditional): landmark name, distance with descriptive text and color, progress bar, score

2. **Share & Collect** (card with `#667eea` left border)
   - "Share This Listing" button opens share modal
   - "Add to Collection" dropdown (authenticated, if user has collections)
   - "Create a Collection" link (authenticated, no collections yet)
   - Share count text
   - Reaction summary: pills showing reaction type icon, label, and count

3. **Your Flag**
   - Current flag display
   - Three flag toggle buttons: Favorite, Maybe, Hidden (form POST)
   - Guest note: "Flags are saved in your browser session. Create a free account..."

4. **Watch This Street** (conditional: street name parsed from address)
   - Purple left border card (`#8b5cf6`)
   - Shows street name and zip
   - Authenticated: "Watch [street name]" button (AJAX POST to `dashboard.watch_quick_add`)
   - Not authenticated: "Sign up to watch streets" link
   - After watching: "Watching" badge with remove button (AJAX)
   - Email notice: "Alerts sent to [email]. Unsubscribe anytime."

5. **Your Notes** (authenticated only)
   - Textarea for private notes
   - Checkboxes: Visited, Tour Scheduled, Made Offer, Not Interested
   - "Save Note" button (AJAX POST to `dashboard.save_note`)
   - Save status indicator

6. **Message Agent** (conditional: authenticated user with agent_id)
   - Agent name in header
   - Textarea (auto-prefills with "Re: [address]" on first focus)
   - "Send to [agent name]" button (form POST to `dashboard.contact_agent`)

7. **Listing Info**
   - Table: Source, First Seen, Last Updated, Status

**Share detail modal:**
- Same structure as dashboard share modal but specific to this listing

**Lazy detail enrichment:**
- On first page view, if `details_fetched` is False, the route calls the source API detail endpoint
- Quota check performed before enrichment
- Fields enriched: description, year_built, hoa, features, photos, flood zone, etc.
- Transient API errors leave `details_fetched=False` for retry on next view
- All enrichment attempts logged to `ApiCallLog`

### 4.6 Map (`/map`)

**URL:** `/<prefix>/site/<key>/map`
**Access:** Everyone
**Template:** `dashboard/map.html` (extends `base.html`)

**Layout:**
- Full-width Leaflet map
- Listing markers with score-colored circle icons
- Marker clusters for dense areas
- Landmark markers (red stars from registry + user landmarks)
- Target area filter buttons
- Popup on marker click: address, price, score, link to detail
- Mobile: `height: calc(100vh - 120px)`, `min-height: 400px`

**Data:** All active listings with lat/lng coordinates, per-user composite scores, user flags, target areas from registry.

### 4.7 Digest (`/digest`)

**URL:** `/<prefix>/site/<key>/digest`
**Access:** Everyone
**Template:** `dashboard/digest.html` (extends `base.html`)

**Layout:**
- Tabular listing view with sort headers
- Filter tabs: All, Favorites, Maybe, Hidden, New (within last N days)
- Area filter buttons
- Days-back selector for "New" tab
- CSV export button (downloads `homefinder_listings.csv`)
- Columns: Address, Area, Price, Beds, Baths, Sqft, Score, Flag, Source, First Seen
- Per-user composite scores
- New listings summary strip with counts
- Price change listings highlighted

**CSV export fields:** Address, Area, Price, Beds, Baths, Sqft, Lot Sqft, Year Built, Score, Flood Zone, Above Flood Plain, HOA/mo, Tax/yr, Days on Market, Price Change %, Garage, Porch, Patio, Pool, Single Story, Source, Status, First Seen, Flag

### 4.8 Preferences (`/preferences`)

**URL:** `/<prefix>/site/<key>/preferences`
**Access:** Everyone (guests save to session, authenticated save to DB)
**Template:** `dashboard/preferences.html` (extends `base.html`)

**Three sections, each submitted independently:**

**Section 1: Scoring Weights & Search Criteria** (`_section=scoring`)
- **Search criteria:**
  - Min/max price (number inputs)
  - Min beds (number input)
  - Min baths (number input)
  - Must-have checkboxes: Garage, Porch, Patio
  - Great deal threshold (number input, default 75)

- **Importance sliders** (0-10 range each):
  - Price (default 8)
  - Size (default 5)
  - Yard (default 7)
  - Features (default 8)
  - Flood (default 6)
  - Year Built (default 5)
  - Single Story (default 7)
  - Price/Sqft (default 4)
  - Days on Market (default 3)
  - HOA (default 6)
  - Proximity Medical (default 5)
  - Proximity Grocery (default 5)
  - Community Pool (default 6)
  - Property Tax (default 4)
  - Lot Ratio (default 3)
  - Price Trend (default 4)
  - Walkability (default 3)
  - Proximity POI (default 0, off by default)

- **Proximity POI selection:**
  - Dropdown of site landmarks (from registry `landmarks_json`) + "My Landmarks" optgroup (user's personal landmarks)
  - Hidden fields for lat/lng/name
  - When landmark selected, proximity_poi importance slider becomes relevant

- **User landmarks** (authenticated only, max 3 per user):
  - Mini-map (expandable) with search and click-to-add
  - Uses Nominatim for address search
  - AJAX POST to `/my-landmarks` for add/remove
  - Displayed in POI dropdown under "My Landmarks" optgroup

- **AI Preferences Coach** (authenticated only):
  - "Analyze My Preferences" button
  - AJAX analysis returning: headline, strengths, blind_spots, tweaks, local_insight, bottom_line
  - Cached result pre-populated on page load

**Section 2: Landmarks** (owner only)
- Owner landmark picker map
- Search input using Nominatim
- Click map to add landmarks
- Table of existing landmarks with delete buttons
- AJAX POST to `/admin/landmarks` for add/remove

**Section 3: Target Areas** (`_section=areas`, master only)
- Area name + zip codes table (add/remove rows)
- Avoid areas (master only): comma-separated input
- Zip code picker map (master only)
- Form POST saves to site registry (not per-user prefs)

**AJAX behaviors:**
- Scoring preferences save via AJAX (X-Requested-With header)
- User landmarks: AJAX add/remove
- Owner landmarks: AJAX add/remove
- Preferences coach: AJAX analysis

### 4.9 Tour/Itinerary (`/itinerary`)

**URL:** `/<prefix>/site/<key>/itinerary`
**Access:** Authenticated users only
**Template:** `dashboard/itinerary.html`

**Layout:**
- Map showing all favorited listings as markers
- Driving route between favorites
- Table of favorites with notes, visit status, and listing details
- Links to detail pages

### 4.10 Street Watch (`/watch`)

**URL:** `/<prefix>/site/<key>/watch`
**Access:** Everyone (authenticated or email-based)
**Template:** `dashboard/watch.html`

**Layout:**
- List of active street watches
- Each watch: street name, zip code, created date
- Remove button per watch
- Alerts history: new listings, price drops, status changes

### 4.11 Social: Shared With Me / My Shares

**Shared With Me** (`/social/shared-with-me`):
- Authenticated only
- List of shares where `recipient_email` matches current user
- Each share: listing photo/details, sharer name, message, date, reaction buttons

**My Shares** (`/social/my-shares`):
- Authenticated only
- List of shares where `sharer_id` matches current user
- Each share: listing details, recipient name/email, status (sent/viewed/clicked/replied), reactions received

### 4.12 Social: Collections

**Collections List** (`/social/collections`):
- Authenticated only
- User's collections sorted by last updated
- Each collection: title, description, listing count, share count, view count

**Create Collection** (`/social/collections/create`):
- Form: title (required), description (optional), public toggle
- Awards 2 points

**Collection Detail** (`/social/collections/<id>`):
- Listing items ordered by position
- Remove item button per listing
- Share collection form (email, name, message)
- Public link copy

**Collection Public View** (`/social/c/<token>`):
- No authentication required
- Read-only view of collection listings
- View count incremented on visit

### 4.13 Social: Points History (`/social/points`)

**Access:** Authenticated only

**Layout:**
- Current balance display
- Lifetime earned total
- Transaction log table (last 50): date, delta, reason, reference
- Point value reference

### 4.14 Social: Leaderboard (`/social/leaderboard`)

**Access:** Authenticated only

**Layout:**
- Monthly leaderboard (current month)
- Two tables:
  - **Top 10 Sharers:** user, share count this month
  - **Top 10 Referrers:** user, referral count this month

### 4.15 Social: Referral Dashboard + Landing

**Referral Dashboard** (`/social/referral`):
- Authenticated only
- User's referral code
- Invite form: email input, send button
- Referral history table: referred email, status (invited/registered/active/converted), dates

**Referral Landing** (`/social/r/<code>`):
- Public page
- Stores `referral_code` and `referred_by` in session
- Shows referrer info, CTA to register
- Session data used at registration to close referral loop and award 10 points

### 4.16 Social: Add a Home (`/social/add-home`)

**Access:** Authenticated only

**Layout:**
- Form fields:
  - Address (required), City, Zip code (required)
  - Price, Bedrooms, Bathrooms, Sqft
  - Description textarea
  - Relationship dropdown: my_home, friend, neighbor, family
  - Photo upload (up to 5 files: .jpg, .jpeg, .png, .webp)
  - Permission confirmation checkbox (required)
- Awards 5 points on submission
- Submissions expire after 90 days if not approved

### 4.17 Social: Friend Listings / Neighborhood Tips (`/social/friend-listings`)

**Access:** Everyone

**Layout:**
- Grid of active friend listings matching site zip codes
- Each listing card: photo, address, price, beds/baths, sqft, description
- Green "Neighborhood Tip" badge
- Sorted by newest first

### 4.18 Social: Analytics + Digest Trigger (`/social/analytics`)

**Access:** Admin only (owner, agent, master)

**Layout:**
- Summary cards: total shares, total views, total reactions, total collections, total referrals
- Most shared listings table (top 10): listing, share count
- Recent shares table (last 20): sharer, recipient, listing, date, status
- "Send Social Digest" button (owner/master only, form POST to `social.send_digest`)

### 4.19 Agent Dashboard (`/agent/dashboard`)

**Access:** Agent, Owner, Master

**Layout:**
1. **Agent profile header:** name, brokerage, phone, bio, status badge

2. **Branding section:**
   - Brand color picker (hex input)
   - Brand logo URL input
   - Brand icon (emoji) input
   - Tagline text input
   - Tagline style dropdown: plain, italic, bold, caps, badge, elegant
   - Save branding button (form POST to `dashboard.agent_branding`)

3. **Create Client form:**
   - Client name, email, intro message
   - Creates account, sends welcome email with temp password
   - "Resend Welcome" button per client (AJAX POST, generates new temp password)

4. **Client table:**
   - Columns: username, email, role, favorites count, created date
   - Expandable notes section per client (AJAX save):
     - Notes textarea
     - Checkboxes: Pre-Approved, Signed Agreement, Tour Scheduled, Offer Submitted, Active Searching
   - Listing notes accordion per client: shows their notes on specific listings
   - "View Preferences" link per client
   - "Preview" (masquerade) link per client

5. **Pending Neighborhood Tips** (friend listings from clients)
   - Table of pending submissions from this agent's clients
   - Review, Approve, Reject action buttons per listing
   - Approve awards 3 points

6. **Add Listing button** -- link to agent add listing form

### 4.20 Agent: Add Listing (`/agent/add-listing`)

**Access:** Agent only

**Layout:**
- Form fields:
  - Address (required), City, Zip code (required)
  - Price, Bedrooms, Bathrooms, Sqft, Lot Sqft
  - Year Built, Latitude, Longitude
  - Description textarea
  - Photo upload (up to 5 files)
  - Feature checkboxes: Garage, Porch, Patio, Single Story, Community Pool
  - HOA monthly, Property Tax annual, Stories
- On submit: creates Listing with `source="agent"`, auto-scores, awards 5 points
- Redirects to listing detail page

### 4.21 Agent: Review/Approve/Reject Friend Listing

**Review** (`/agent/friend-listing/<id>/review`):
- Shows current friend listing details
- Editable form fields to enrich: address, city, zip, price, beds, baths, sqft, description
- Save edits button (form POST, returns to same page)
- Approve and Reject buttons

**Approve** (`/agent/friend-listing/<id>/approve`):
- Creates a real `Listing` record with `source="community"`
- Additional enrichment fields on approve form: lot sqft, year built, lat/lng, feature checkboxes, HOA, property tax, stories
- Auto-scores the new listing
- Updates FriendListing status to "approved"
- Awards 3 points to agent

**Reject** (`/agent/friend-listing/<id>/reject`):
- Optional rejection reason text field
- Updates FriendListing status to "rejected"

### 4.22 Agent: Client Preferences (`/agent/clients/<id>/prefs`)

**Access:** Agent only (client must belong to this agent)

**Layout:**
- Same preference form as Section 1 of main preferences page
- All importance sliders and search criteria
- Save button (form POST)
- Shows client name in header

### 4.23 Agent: Branding

Embedded in Agent Dashboard (section 2 above). Form POST to `dashboard.agent_branding`.

**Fields:**
- `brand_color`: hex color picker, validated against `^#[0-9A-Fa-f]{6}$`, default `#2563eb`
- `brand_logo_url`: URL string for logo image
- `brand_icon`: emoji string (max 10 chars, HTML escaped)
- `brand_tagline`: text (max 200 chars)
- `brand_tagline_style`: one of `plain`, `italic`, `bold`, `caps`, `badge`, `elegant`

**Display in navbar:**
- If `brand_icon`: emoji span before agent name
- Elif `brand_logo_url`: img tag (height 28px)
- Else: default house-heart icon
- Tagline rendered below name with style-specific formatting

### 4.24 Agent/Owner: Prompts

**Owner prompts** (`/admin/prompts`):
- Three prompt types: deal, portfolio, preferences
- Textarea per prompt type showing current override or empty
- Default prompt shown for reference
- Save button (form POST)
- Validate and Preview buttons per prompt

**Agent prompts** (`/agent/prompts`):
- Same structure as owner prompts
- Agent overrides take priority over owner overrides
- Shows effective prompt (agent -> owner -> default chain)

**Validation** (AJAX POST to `/admin/prompts/validate`):
- Returns JSON with issues array
- Checks: "JSON" keyword present, required keys mentioned, markdown fence instruction, length (50-4000), role instruction
- Required keys per type:
  - deal: summary, strengths, concerns, negotiation, verdict
  - portfolio: headline, ranking, patterns, strategy, dark_horse, bottom_line
  - preferences: headline, strengths, blind_spots, tweaks, local_insight, bottom_line

**Preview** (AJAX POST to `/admin/prompts/preview`):
- Modal with editable sample data textarea (pre-filled with type-specific sample context)
- Sends prompt + sample context to Claude API
- Returns formatted JSON result
- Shows response time in ms
- Logs the test call to ApiCallLog

### 4.25 Admin: Agent Management (`/admin/agents`)

**Access:** Owner, Master

**Layout:**
- Table of all agent profiles sorted by status then created date
- Columns: name, email, license, brokerage, phone, status, created, approved date
- Status badges: pending (warning), approved (success), suspended (danger)
- Action buttons per agent: Approve, Suspend, Reactivate
- Owner notes section per agent (AJAX save):
  - Notes textarea
  - Checkboxes: Contract Signed, Background Checked, MLS Verified
- Client count per agent

### 4.26 Admin: User Management (`/admin/users`)

**Access:** Owner, Master

**Layout:**
- Table of all users sorted by created date (newest first)
- Columns: username, email, role, verified status, suspended status, created date, last login
- Action buttons per user:
  - **Suspend:** modal with reason textarea, form POST
  - **Reactivate:** form POST
  - **Delete:** form POST (renames username/email with `deleted_` prefix, clears password hash)
- Safety rules:
  - Cannot modify your own account
  - Cannot modify master accounts unless you are master
  - Cannot delete owner or master accounts

### 4.27 Admin: Metrics + Fetch Now + Scheduler (`/admin/metrics`)

**Access:** Owner, Master

**Layout:**
1. **Summary cards:**
   - Total AI calls (all-time)
   - Total fetch calls (all-time)
   - All-time estimated cost
   - Last 30 days estimated cost

2. **Per-user usage tables:**
   - All-time and last-30-days breakdowns
   - Columns per call type: zillow, realtor, zillow_detail, realtor_detail, anthropic_deal, anthropic_portfolio, anthropic_prefs, google_places, google_geocode
   - Cost per call type shown in header
   - Total cost per user
   - Footer row with column totals

3. **Recent Activity log** (last 50 calls):
   - When, User, Trigger, Site, Zip, Call Type, Results, Response Time (ms), Detail, Success
   - Auto-refresh button (AJAX GET to `/admin/metrics/refresh`)

4. **Fetch Now button:**
   - AJAX POST to `/fetch-now`
   - Quota check before fetch
   - Returns JSON with status, summary, elapsed time, captured log lines
   - Loading state during fetch
   - Log output displayed in scrollable area

5. **Scheduler toggle:**
   - AJAX POST to `/toggle-scheduler`
   - Pauses/resumes nightly 3AM pipeline
   - Shows current state (paused/running)
   - Blocked if master has locked scheduler (`scheduler_locked` in registry)

### 4.28 Admin: Billing (`/admin/billing`)

**Access:** Owner, Master

**Layout:**
1. **Current plan display:** plan name, limits, budget

2. **Usage meters:**
   - AI calls: progress bar with percentage (used/limit)
   - Fetch calls: progress bar with percentage
   - Budget: progress bar with dollar amounts

3. **Plan selector:** free, basic, pro, unlimited
   - Each plan shows default limits

4. **Override fields:**
   - Monthly AI limit (number input)
   - Monthly fetch limit (number input)
   - Monthly budget (dollar input)
   - Billing email (for budget alerts)
   - Billing cycle start day (1-28)

5. **Plan tier defaults:**

| Plan      | AI Calls | Fetch Calls | Budget  |
|-----------|----------|-------------|---------|
| free      | 10       | 50          | $1.00   |
| basic     | 100      | 500         | $10.00  |
| pro       | 500      | 2,000       | $50.00  |
| unlimited | 0 (none) | 0 (none)    | $0 (none)|

6. **Save button:** form POST to `/admin/billing`

### 4.29 Admin: Diagnostics (`/admin/diagnostics`)

**Access:** Owner, Master

**Layout:**
1. **Summary cards (last 24h):**
   - Total API calls
   - Average response time (ms)
   - Error rate (%)
   - Zillow calls count
   - Realtor calls count
   - Min quota remaining

2. **Call log table (last 200 paid API calls):**
   - Columns: When, Call Type, User, Detail, Response Time, HTTP Status, Success, Quota Remaining

### 4.30 Docs (`/docs`)

**Access:** Admin only (agent, owner, master)

**Layout:**
- Role-based folder access
- Document listing from `docs/` directory
- Markdown rendering

### 4.31 Master: Site Manager

**Access:** Master only
**URL:** Uses `url_for('site_manager.*')` (not `site_url`)

**Sites List:**
- All sites from registry (active and inactive)
- Columns: site key, display name, DB path, active status, listing count
- Buttons: Edit, Toggle Active, Delete

**Create Site:**
- Site key input (typeahead/autocomplete)
- Display name
- DB path
- Map center lat/lng
- Map bounds JSON
- Zip codes JSON
- Active toggle

**Edit Site:**
- All fields from create
- Scheduler locked toggle (master-only, prevents owner from resuming)
- Max fetches per run (pipeline listing cap)

---

## 5. Data Flows

### 5.1 Listing Pipeline: API Fetch to Display

1. **Pipeline trigger:** APScheduler at 3AM daily, or manual "Fetch Now" button
2. **Quota check:** `billing.check_quota()` verifies site hasn't exceeded fetch limits
3. **API fetch:** `zillow.py` and `realtor.py` call RapidAPI for each zip code
4. **Dedup:** Listings matched by `source_id` (format: `zillow_<zpid>` or `realtor_<property_id>`)
5. **Upsert:** New listings created, existing listings updated (price, status, photos, etc.)
6. **Price history:** Price changes logged to `price_history_json`
7. **Geocoding:** Address geocoded to lat/lng if missing
8. **Scoring:** `scorer.py` computes all 18 sub-scores and default composite
9. **Storage:** Scores stored in `DealScore` table (original 5 columns + extended JSON)
10. **Display:** Dashboard query joins `Listing` + `DealScore`, computes per-user composite using user's importance weights

**Lazy detail enrichment (on first detail page view):**
1. Check `listing.details_fetched` flag
2. Quota check for `{source}_detail` call type
3. Call source API detail endpoint with `source_id`
4. Apply enrichable fields: description, year_built, hoa, features, photos, flood zone
5. Set `details_fetched = True` on success
6. Transient errors (5xx) leave flag False for retry

### 5.2 Share Flow

1. **Sender** fills share modal: recipient email, name, relationship, message
2. **POST** to `social.share_listing` creates `SocialShare` record with unique `share_token`
3. **Points:** +1 point awarded to sharer
4. **Email:** Share notification sent with listing photo, price, sharer's note, and share link
5. **Recipient** clicks link, arrives at `/social/s/<token>`
6. **View tracked:** `viewed_at` timestamp set, status updated to "viewed"
7. **Reaction:** Recipient selects reaction type (love, interested, great_location, too_expensive, not_for_me) and optional comment
8. **POST** to `social.react_to_share` creates `SocialReaction` record
9. **Points:** +3 points awarded to original sharer for new reaction
10. **Email:** Reaction notification sent to sharer

### 5.3 Friend Listing Flow

1. **Submission:** User fills "Add a Home" form at `/social/add-home`
2. **Record created:** `FriendListing` with `status="active"`, `expires_at` = 90 days out
3. **Points:** +5 points to submitter
4. **Display:** Appears in Neighborhood Tips section on dashboard and friend listings page
5. **Agent review:** Agent sees pending tips from their clients on agent dashboard
6. **Review page:** Agent can edit details (address, price, beds, etc.)
7. **Approve:** Agent adds enrichment data (lot, year, lat/lng, features), creates real `Listing` with `source="community"`, auto-scores
8. **Points:** +3 points to agent for approval
9. **Reject:** Agent provides optional reason, status set to "rejected"
10. **Expiry:** `expire_friend_listings()` called from pipeline, marks 90-day-old active listings as "expired"

### 5.4 Preferences and Scoring

1. **User sets preferences** via sliders (0-10 importance per factor) and search criteria
2. **Storage:** Authenticated users: `user.preferences_json` (only non-default values stored). Guests: `session["guest_prefs"]`
3. **Composite computation:** On every dashboard/detail page load:
   - Load all 18 sub-scores from `DealScore`
   - Recompute `price_score` using THIS user's min/max price range
   - Recompute `proximity_poi_score` using THIS user's selected landmark
   - Weight each sub-score by user's importance / total importance
   - Sum weighted scores for composite (0-100)
4. **Target areas:** Stored in registry (site-wide), not per-user
5. **Avoid areas:** Stored in user prefs (master only can edit)

### 5.5 Billing Quota Enforcement

1. **Site billing config** stored in registry: plan, limits, budget, cycle start
2. **On each API call:** `check_quota(site_key, call_type)` called
3. **Per-type limits:** AI calls counted against `monthly_limit_ai`, fetch calls against `monthly_limit_fetch`
4. **Budget cap:** Total estimated cost checked against `monthly_budget`
5. **Unlimited plan:** All checks bypassed
6. **Blocked calls:** Return `(False, reason)` with human-readable message
7. **Budget alerts:** Email sent at 80% and 100% thresholds (deduped per cycle)

### 5.6 Referral Loop

1. **Referrer** creates referral at `/social/referral/invite` with email
2. **Referral record** created with unique `referral_code`
3. **Email** sent to referred person with referral link
4. **Referred person** clicks `/social/r/<code>`, stores `referral_code` and `referred_by` in session
5. **Registration:** At account creation, session data checked:
   - `referral_code` looked up in `Referral` table
   - `referred_user_id` set, status updated to "registered", `registered_at` timestamped
6. **Points:** +10 points awarded to referrer for successful registration

---

## 6. Scoring System

### 6.1 All 18 Factors

| # | Factor           | Score Key                | Imp Key           | Default Imp | Description                                    |
|---|------------------|--------------------------|-------------------|-------------|------------------------------------------------|
| 1 | Price            | `price_score`            | `imp_price`       | 8           | Lower = better, sweet spot at min to 70% of max|
| 2 | House Size       | `size_score`             | `imp_size`        | 5           | Bigger = better, diminishing above 2500 sqft   |
| 3 | Yard Size        | `yard_score`             | `imp_yard`        | 7           | Target >= 10,000 sqft lot                      |
| 4 | Features         | `feature_score`          | `imp_features`    | 8           | Garage+Porch+Patio=60, beds>=4=+20, baths>=3=+20|
| 5 | Flood Risk       | `flood_score`            | `imp_flood`       | 6           | Above flood plain bonus, zone X = best         |
| 6 | Year Built       | `year_built_score`       | `imp_year_built`  | 5           | Newer = better                                 |
| 7 | Single Story     | `single_story_score`     | `imp_single_story`| 7           | 100 if single story, 50 otherwise              |
| 8 | Price/Sqft       | `price_per_sqft_score`   | `imp_price_per_sqft`| 4         | Lower $/sqft = better                          |
| 9 | Days on Market   | `days_on_market_score`   | `imp_days_on_market`| 3         | More DOM = potential opportunity                |
| 10| HOA Fee          | `hoa_score`              | `imp_hoa`         | 6           | No/low HOA = better                            |
| 11| Near Medical     | `proximity_medical_score`| `imp_proximity_medical`| 5      | Closer hospital = better                       |
| 12| Near Grocery     | `proximity_grocery_score`| `imp_proximity_grocery`| 5      | Closer grocery = better                        |
| 13| Community Pool   | `community_pool_score`   | `imp_community_pool`| 6        | Bonus for community pool                       |
| 14| Property Tax     | `property_tax_score`     | `imp_property_tax`| 4           | Lower annual tax = better                      |
| 15| Lot Ratio        | `lot_ratio_score`        | `imp_lot_ratio`   | 3           | Higher lot-to-house ratio = better             |
| 16| Price Trend      | `price_trend_score`      | `imp_price_trend` | 4           | Negative price change = opportunity            |
| 17| Walkability      | `walkability_score`      | `imp_walkability` | 3           | Higher walkability score = better              |
| 18| Proximity POI    | `proximity_poi_score`    | `imp_proximity_poi`| 0 (off)   | Distance to user's selected landmark (Haversine)|

### 6.2 Per-User Composite Recalculation

Every page load that displays scores:
1. Load all 18 sub-scores from `DealScore` record
2. Recompute `price_score` with user's `min_price`/`max_price`
3. Recompute `proximity_poi_score` with user's selected landmark lat/lng
4. For each factor: `weight = imp_value / sum(all_imp_values)`
5. `composite = sum(sub_score * weight)` for all 18 factors
6. Result: 0-100 float, rounded to 1 decimal

If all importance values are 0, returns 50.0 (neutral).

### 6.3 POI Proximity Scoring

- Uses Haversine formula (`_haversine_miles`) for distance calculation
- `score_proximity_poi(lat, lng, poi_lat, poi_lng)` returns 0-100
- Dashboard shows distance badges with color coding:
  - <= 2 mi: green (`bg-success`)
  - <= 5 mi: blue (`bg-primary`)
  - <= 10 mi: yellow (`bg-warning text-dark`)
  - > 10 mi: red (`bg-danger`)
- Detail page shows descriptive text: "walking distance", "very close", "short drive", "moderate drive", "far"
- Max distance filter on dashboard: dropdown from 0.5 to 25 miles

### 6.4 Score Ring Display Colors

- **Green:** composite >= 75 (`score-high`)
- **Blue:** composite >= 50 (`score-mid`)
- **Red:** composite < 50 (`score-low`)

Same color scheme used for sub-score progress bars in detail sidebar.

---

## 7. Points & Gamification

### 7.1 Earning Actions

| Action                | Points | Trigger                                    |
|-----------------------|--------|--------------------------------------------|
| Share a listing       | +1     | `social.share_listing` POST                |
| Create a collection   | +2     | `social.collection_create` POST            |
| Reaction received     | +3     | `social.react_to_share` (new reaction only)|
| Listing approved      | +3     | `agent_approve_friend_listing`             |
| Submit Neighborhood Tip| +5    | `social.add_home` POST                     |
| Agent creates listing | +5     | `agent_add_listing` POST                   |
| Referral signs up     | +10    | Registration with referral code in session  |

### 7.2 Daily Cap

- Maximum 50 points earnable per day (UTC midnight reset)
- If award would exceed cap, only remaining allowance is credited
- Checked via `UserPointLog` sum for current day

### 7.3 Points Badge in Nav

- Visible in Social dropdown when `points_account.balance > 0`
- Pink pill badge (`background: #f093fb`, `font-size: 0.6rem`)
- Shows gem icon (`bi-gem`) and balance number

### 7.4 Points History Page (`/social/points`)

- Current balance display
- Lifetime earned total
- Last 50 transactions table: date, delta, reason, reference ID

### 7.5 Leaderboard (`/social/leaderboard`)

- Monthly scope (current month, UTC)
- Top 10 Sharers: user + share count
- Top 10 Referrers: user + referral count
- Data queried from `SocialShare` and `Referral` tables with `created_at >= month_start`

---

## 8. Email Templates

All emails sent via Flask-Mail through SMTP.

### 8.1 Share Notification (`email/share_notification.html`)
- Subject: "[sharer] shared a listing with you on HomeFinder!"
- Content: listing photo, price, address, sharer's personal message, share link button

### 8.2 Reaction Notification (`email/reaction_notification.html`)
- Subject: "[reactor] reacted to your shared listing!"
- Content: reaction type label, link back to listing

### 8.3 Collection Share Notification (`email/collection_share_notification.html`)
- Subject: "[sharer] shared a collection with you on HomeFinder!"
- Content: collection title, listing count, personal message, collection link

### 8.4 Referral Invitation (`email/referral_invitation.html`)
- Subject: "[referrer] invited you to HomeFinder!"
- Content: referrer username, referral link with code

### 8.5 Client Welcome Email (`auth/client_welcome_email_body.html`)
- Subject: "Your HomeFinder Account -- [agent name]"
- Content: client name, username, temp password, agent info, intro message, login URL, site name

### 8.6 Social Digest (`social_digest.py`)
- Weekly summary of social activity
- Triggered manually by owner via Social Analytics page
- Uses `send_weekly_digests(site_key)` function

### 8.7 Street Watch Digest
- Alert emails for new listings, price drops, status changes on watched streets
- Includes unsubscribe link via `unsubscribe_token`

### 8.8 Budget Alert Emails
- Subject: "HomeFinder budget alert -- [pct]% of monthly limit ([site_key])"
- Sent at 80% and 100% of monthly budget
- Contains: spend amount, AI calls, fetch calls, plan details
- Deduped per threshold per billing cycle

---

## 9. Modals

### 9.1 Welcome Modal (`#welcomeModal`)

- **Trigger:** Automatically on first visit (cookie `hf_welcomed` not set)
- **Condition:** `{% if not current_user.is_authenticated %}`
- **Size:** `modal-dialog-centered`, default width
- **Content:**
  - House-heart icon (3rem, text-primary)
  - "Welcome to HomeFinder" heading
  - Description of free features
  - Grid of account benefits: AI Deal Analysis, Permanent Data Storage, Fetch Fresh Listings, Save Preferences Forever
  - Two buttons: "Start Browsing" (dismiss + set cookie), "Create Free Account"
  - Sign in link
- **Cookie:** `hf_welcomed=1`, path `/`, max-age 1 year

### 9.2 Join Modal (`#joinModal`)

- **Trigger:** `showJoinModal(feature)` JS function called from gated buttons
- **Condition:** `{% if not current_user.is_authenticated %}`
- **Size:** `modal-dialog-centered modal-sm`
- **Content:**
  - Lock icon (2rem, text-primary)
  - "Free Account Required" heading
  - Dynamic message per feature: `analyze`, `preferences`, `fetch`
  - Three buttons: "Sign Up Free", "Sign In", "Maybe Later"

### 9.3 Share Modal (Dashboard, per-listing)

- **Trigger:** Share button on listing card (`data-bs-target="#shareModal{{ listing.id }}"`)
- **Size:** `modal-sm`
- **ID:** `#shareModal{{ listing.id }}` (unique per listing)
- **Content:** See Section 4.4 item 11 above
- **Form action:** `social.share_listing`

### 9.4 Share Detail Modal (Detail page)

- **Trigger:** "Share This Listing" button in sidebar
- **ID:** `#shareDetailModal`
- **Content:** Same structure as dashboard share modal

### 9.5 Contact Agent Modal (`#contactAgentModal`)

- **Trigger:** "Contact Agent" nav link or "Message" button on dashboard
- **Condition:** `{% if current_user.is_authenticated and current_user.assigned_agent %}`
- **Size:** `modal-dialog-centered`, default width
- **Content:**
  - "Contact [agent name]" heading
  - Agent phone and brokerage (if available)
  - Message textarea (required)
  - Cancel and "Send Message" buttons
- **Form action:** `dashboard.contact_agent`

### 9.6 Prompt Preview Modal

- **Trigger:** "Preview" button on prompt editor pages
- **Content:**
  - Editable sample context textarea (pre-filled with type-specific sample data)
  - "Run Preview" button (AJAX POST to `/admin/prompts/preview`)
  - Results area: pretty-formatted JSON, response time
  - Loading spinner during API call

### 9.7 Suspend User Modal

- **Trigger:** "Suspend" button on admin users page
- **Content:**
  - "Suspend [username]?" heading
  - Reason textarea
  - Confirm and Cancel buttons
- **Form action:** `dashboard.admin_user_action`

### 9.8 Masquerade Banner

Not a modal but a persistent alert bar:
- **Condition:** `{% if session.get('masquerade_original_id') %}`
- **Style:** `alert-warning`, no rounded corners, gold bottom border
- **Content:** "Agent Preview Mode -- You are viewing the site as [username]. End Preview & Return to Your Account"
- **Chained masquerade:** Supports master -> agent -> principal chains. `masquerade_original_id` is set on the first hop only and never overwritten. "End Preview" always returns to the true original user (master) regardless of chain depth.

---

## 10. Maps

### 10.1 Listing Detail Map

- **Library:** Leaflet 1.9.4 (loaded only if listing has lat/lng)
- **Tile source:** OpenStreetMap
- **Height:** 250px, `border-radius: 10px`, `z-index: 0`
- **Interaction:** Scroll wheel zoom disabled, zoom controls enabled
- **Main marker:** Score-colored `divIcon` (36x36px circle with white border, shadow), shows score number
- **Landmark markers:** Red star icons (`bi-star-fill`, `color: #dc2626`, text-shadow for contrast), `zIndexOffset: 900`
- **Landmark tooltips:** Non-permanent, direction top, offset `[0, -6]`, class `lm-tooltip`
- **Zoom buttons:** 4 preset levels (Street 19, Block 16, Neighborhood 14 default, Area 12)
- **Google Maps links:**
  - Direct link: `https://www.google.com/maps/place/{address}/@{lat},{lng},{zoom}z`
  - Landmarks route: `https://www.google.com/maps/dir/{landmarks...}/{listing}`
- **Zoom sync:** Map zoom events update Google Maps link URL and highlight closest zoom button

### 10.2 Main Map Page (`/map`)

- **Tile source:** OpenStreetMap
- **Markers:** All active listings with lat/lng, score-colored circle icons
- **Clusters:** For dense areas (Leaflet markercluster)
- **Landmarks:** Red star markers from site registry
- **Filter buttons:** Target area filter
- **Popup:** Address, price, score, link to detail page
- **Mobile height:** `calc(100vh - 120px)`, `min-height: 400px`

### 10.3 Preferences: Target Areas Map

- **Access:** Master only (in Section 3 of preferences)
- **Purpose:** Visual zip code picker for target area configuration
- **Click interaction:** Add/remove zip codes from areas

### 10.4 Preferences: Owner Landmark Picker Map

- **Access:** Owner only (in Section 2 of preferences)
- **Search:** Nominatim geocoding for address search
- **Click interaction:** Click map to place landmark, enter name
- **AJAX:** POST to `/admin/landmarks` for add/remove
- **Existing landmarks:** Displayed as markers on the map

### 10.5 Preferences: User Landmark Mini-Map

- **Access:** Authenticated users (expandable, in Section 1 of preferences)
- **Max landmarks:** 3 per user
- **Search:** Nominatim geocoding
- **Click interaction:** Click map to place landmark, enter name
- **AJAX:** POST to `/my-landmarks` for add/remove
- **Storage:** In `user.preferences_json` under `user_landmarks` key
- **Display:** Appear in POI dropdown under "My Landmarks" optgroup

---

## 11. Mobile & PWA

### 11.1 Responsive Breakpoints

**>= 992px (Desktop):**
- Navbar expanded, stacked icon-over-text layout
- Listing cards in two-column grid (`.col-lg-6`)
- Detail page: two-column layout (8/4)

**< 992px (Tablet/Mobile):**
- Navbar collapsed behind hamburger button
- Nav links: `padding: 10px 16px`, `font-size: 0.95rem`, bottom border separator
- Nav icons: fixed 24px width, 8px right margin
- Dropdown items: `padding: 10px 20px`
- Listing cards: full width, photo stacks on top
- Photo: `width: 100%`, `height: 160px`, `border-radius: 10px 10px 0 0`
- Score ring: 42x42px, `font-size: 0.8rem`
- Filter bar: wraps with `gap: 4px`
- Modals: `margin: 8px`, near full-width
- Map: `height: calc(100vh - 120px)`, `min-height: 400px`
- Detail stat blocks: reduced padding (8px 4px), smaller value text (1.2rem)
- Preferences: full-width columns, `padding: 12px`
- Main container: `padding-left: 8px`, `padding-right: 8px`

**< 576px (Small Phone):**
- Price display: `font-size: 1.1rem`
- Feature tags: `font-size: 0.62rem`, `padding: 1px 4px`
- Source badges and flag buttons: wrap with 6px gap
- Welcome power grid: single column
- Role pills: vertical stack, full-width

### 11.2 Touch Target Sizes

- Mobile nav links: 10px vertical padding (min ~44px touch target)
- Mobile dropdown items: 10px vertical padding
- Flag buttons on listing cards: `btn-sm` with `py-0 px-1` (compact but tappable)

### 11.3 PWA Configuration

**Manifest:** `/static/manifest.json`
- App name: "HomeFinder"
- Icons: `icon-192.png`, `icon-512.png`
- Display mode: standalone
- Theme color: `#1a1a2e`

**Service Worker:** `/home_finder_agents_social/sw.js`
- Scope: `/home_finder_agents_social/`
- Registered on every page load (both `base.html` and `welcome.html`)
- Graceful failure: `.catch(() => {})` on registration

**Meta tags:**
- `<meta name="mobile-web-app-capable" content="yes">`
- `<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">`
- `<meta name="apple-mobile-web-app-title" content="HomeFinder">`
- `<meta name="theme-color" content="#1a1a2e">`
- `<link rel="apple-touch-icon" href="icon-192.png">`
- `<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">`

**Standalone mode CSS:**
```css
@media (display-mode: standalone) {
    body { padding-top: env(safe-area-inset-top); }
    .navbar { padding-top: env(safe-area-inset-top); }
}
```

**Safe area insets:**
```css
@supports (padding: env(safe-area-inset-bottom)) {
    main.container { padding-bottom: env(safe-area-inset-bottom); }
}
```

### 11.4 PWA Install Banner

A custom fixed banner appears at the bottom of the dashboard on mobile devices after a 2-second delay.

**Detection:** Mobile is detected via user-agent string (Android, iPhone, iPad, iPod, Opera Mini, IEMobile, etc.) combined with screen width <= 768px.

**Banner design:**
- Fixed bottom, dark gradient background matching site theme (`--ink`), gold accent border-top
- Contains app icon, "Install HomeFinder" heading, brief description, and action button(s)

**Platform-specific behavior:**
- **Android with native prompt:** Intercepts the `beforeinstallprompt` event. "Install" button triggers the browser's native install dialog. On successful install, sets a 1-year cookie.
- **iOS (Safari):** Shows manual instructions: "Tap the Share button, then 'Add to Home Screen'."
- **Other browsers (Opera, Firefox, etc.):** Shows instructions: "Tap browser menu, then 'Add to Home Screen'."

**Dismiss logic:**
- "Dismiss" sets a 30-day cookie (`pwa_dismissed`)
- "Install" (successful) sets a 1-year cookie (`pwa_installed`)
- Not shown if `display-mode: standalone` (already installed), if dismissed cookie exists, or on desktop

**Cookie names:** `pwa_dismissed` (30 days), `pwa_installed` (365 days)

---

## Appendix A: URL Route Reference

All routes use `site_url()` (which preserves multi-tenant site context) unless noted.

| Route                                    | Method | URL Pattern                            | Auth Required |
|------------------------------------------|--------|----------------------------------------|---------------|
| `dashboard.welcome`                      | GET    | `/welcome`                             | No            |
| `dashboard.index`                        | GET    | `/`                                    | No            |
| `dashboard.listing_detail`               | GET    | `/listing/<id>`                        | No            |
| `dashboard.toggle_flag`                  | POST   | `/listing/<id>/flag`                   | No            |
| `dashboard.map_view`                     | GET    | `/map`                                 | No            |
| `dashboard.digest`                       | GET    | `/digest`                              | No            |
| `dashboard.preferences`                  | GET/POST| `/preferences`                        | No            |
| `dashboard.itinerary`                    | GET    | `/itinerary`                           | Yes           |
| `dashboard.watch_manage`                 | GET    | `/watch`                               | No            |
| `dashboard.help_page`                    | GET    | `/help`                                | No            |
| `dashboard.agent_dashboard`              | GET    | `/agent/dashboard`                     | Yes (agent)   |
| `dashboard.agent_add_listing`            | GET/POST| `/agent/add-listing`                  | Yes (agent)   |
| `dashboard.agent_branding`               | POST   | `/agent/branding`                      | Yes (agent)   |
| `dashboard.agent_client_prefs`           | GET/POST| `/agent/clients/<id>/prefs`           | Yes (agent)   |
| `dashboard.agent_client_notes`           | POST   | `/agent/clients/<id>/notes`            | Yes (admin)   |
| `dashboard.agent_create_client`          | POST   | `/agent/clients/create`                | Yes (agent)   |
| `dashboard.agent_prompts`                | GET/POST| `/agent/prompts`                      | Yes (admin)   |
| `dashboard.agent_review_friend_listing`  | GET/POST| `/agent/friend-listing/<id>/review`   | Yes (agent)   |
| `dashboard.agent_approve_friend_listing` | POST   | `/agent/friend-listing/<id>/approve`   | Yes (agent)   |
| `dashboard.agent_reject_friend_listing`  | POST   | `/agent/friend-listing/<id>/reject`    | Yes (agent)   |
| `dashboard.admin_agents`                 | GET    | `/admin/agents`                        | Yes (owner)   |
| `dashboard.admin_agent_action`           | POST   | `/admin/agents/<id>/action`            | Yes (owner)   |
| `dashboard.admin_users`                  | GET    | `/admin/users`                         | Yes (owner)   |
| `dashboard.admin_user_action`            | POST   | `/admin/users/<id>/action`             | Yes (owner)   |
| `dashboard.admin_metrics`                | GET    | `/admin/metrics`                       | Yes (owner)   |
| `dashboard.admin_diagnostics`            | GET    | `/admin/diagnostics`                   | Yes (owner)   |
| `dashboard.admin_billing`                | GET/POST| `/admin/billing`                      | Yes (owner)   |
| `dashboard.admin_prompts`                | GET/POST| `/admin/prompts`                      | Yes (owner)   |
| `dashboard.admin_landmarks`              | POST   | `/admin/landmarks`                     | Yes (owner)   |
| `dashboard.user_landmarks`               | POST   | `/my-landmarks`                        | Yes           |
| `dashboard.fetch_now`                    | POST   | `/fetch-now`                           | Yes (owner/agent)|
| `dashboard.toggle_scheduler`             | POST   | `/toggle-scheduler`                    | Yes (owner)   |
| `dashboard.prompt_validate`              | POST   | `/admin/prompts/validate`              | Yes (admin)   |
| `dashboard.prompt_preview`               | POST   | `/admin/prompts/preview`               | Yes (admin)   |
| `social.share_listing`                   | POST   | `/social/share`                        | No            |
| `social.view_share`                      | GET    | `/social/s/<token>`                    | No            |
| `social.react_to_share`                  | POST   | `/social/react/<id>`                   | No            |
| `social.shared_with_me`                  | GET    | `/social/shared-with-me`               | Yes           |
| `social.my_shares`                       | GET    | `/social/my-shares`                    | Yes           |
| `social.copy_link`                       | GET    | `/social/copy-link/<id>`               | No            |
| `social.collections_list`                | GET    | `/social/collections`                  | Yes           |
| `social.collection_create`               | GET/POST| `/social/collections/create`          | Yes           |
| `social.collection_detail`               | GET    | `/social/collections/<id>`             | Yes           |
| `social.collection_public`               | GET    | `/social/c/<token>`                    | No            |
| `social.collection_add_listing`          | POST   | `/social/collections/<id>/add`         | Yes           |
| `social.collection_remove_listing`       | POST   | `/social/collections/<id>/remove/<item_id>` | Yes     |
| `social.collection_share`                | POST   | `/social/collections/<id>/share`       | Yes           |
| `social.referral_dashboard`              | GET    | `/social/referral`                     | Yes           |
| `social.referral_invite`                 | POST   | `/social/referral/invite`              | Yes           |
| `social.referral_landing`                | GET    | `/social/r/<code>`                     | No            |
| `social.social_analytics`                | GET    | `/social/analytics`                    | Yes (admin)   |
| `social.send_digest`                     | POST   | `/social/send-digest`                  | Yes (admin)   |
| `social.points_history`                  | GET    | `/social/points`                       | Yes           |
| `social.leaderboard`                     | GET    | `/social/leaderboard`                  | Yes           |
| `social.add_home`                        | GET/POST| `/social/add-home`                    | Yes           |
| `social.friend_listings`                 | GET    | `/social/friend-listings`              | No            |
| `site_manager.sites_list`               | GET    | `/admin/sites/` (uses `url_for`)       | Yes (master)  |
| `auth.login`                             | GET/POST| `/auth/login`                         | No            |
| `auth.register`                          | GET/POST| `/auth/register`                      | No            |
| `auth.logout`                            | GET    | `/auth/logout`                         | Yes           |
| `auth.close_account`                     | GET/POST| `/auth/close-account`                 | Yes           |
| `auth.end_masquerade`                    | GET    | `/auth/end-masquerade`                 | Yes           |
| `docs.index`                             | GET    | `/docs/`                               | Yes (admin)   |

## Appendix B: External Dependencies

| Library              | Version | CDN Source                                  | Usage                    |
|----------------------|---------|---------------------------------------------|--------------------------|
| Bootstrap CSS        | 5.3.2   | cdnjs.cloudflare.com                        | Layout, components       |
| Bootstrap Icons      | 1.11.2  | cdnjs.cloudflare.com                        | All icons                |
| Bootstrap JS         | 5.3.2   | cdnjs.cloudflare.com                        | Modals, dropdowns, etc.  |
| Leaflet              | 1.9.4   | unpkg.com (loaded conditionally)            | Maps                     |
| Twemoji              | 14.0.2  | cdn.jsdelivr.net                            | Emoji rendering in navbar|

## Appendix C: API Cost Map

| Call Type           | Estimated Cost |
|---------------------|----------------|
| zillow              | $0.005         |
| realtor             | $0.005         |
| zillow_detail       | $0.005         |
| realtor_detail      | $0.005         |
| anthropic_deal      | $0.015         |
| anthropic_portfolio | $0.025         |
| anthropic_prefs     | $0.012         |
| google_places       | $0.017         |
| google_geocode      | $0.005         |
