# HomeFinder Social — Technical Specification

**Version:** 2026.03.14
**Last Updated:** 2026-03-14

---

## Overview

This document describes the technical architecture, data models, routes, templates, and integration points for HomeFinder Social — the social sharing, collections, reactions, referral, and friend-listing features layered onto the existing HomeFinder multi-tenant platform.

---

## Architecture

### New Components

```
Flask App
  ├── Existing Blueprints
  │   ├── dashboard (/)        ← Share button added to listing cards + detail page
  │   ├── auth (/auth)         ← Referral code check on registration
  │   ├── site_manager         ← Unchanged
  │   └── docs (/docs)         ← New doc routes for social docs
  │
  ├── NEW: social (/social)    ← All social feature routes
  │   ├── /share               ← POST: create a share
  │   ├── /s/<token>           ← GET: share landing page
  │   ├── /react/<id>          ← POST: add reaction
  │   ├── /shared-with-me      ← GET: inbox
  │   ├── /my-shares           ← GET: outbox
  │   ├── /copy-link/<id>      ← GET: generate link (AJAX)
  │   ├── /collections/*       ← CRUD for collections
  │   ├── /c/<token>           ← GET: public collection view
  │   ├── /referral            ← GET: referral dashboard
  │   ├── /referral/invite     ← POST: send invitation
  │   ├── /r/<code>            ← GET: referral landing
  │   └── /analytics           ← GET: social analytics (admin)
  │
  ├── models.py                ← Existing models (unchanged)
  └── models_social.py         ← NEW: 5 social models
```

### Multi-Tenant Compatibility

Social models live in the **per-site SQLite databases** (not registry.db), so social activity is scoped per market. This means:

- Shares created in Charleston stay in Charleston's DB
- Collections are per-site (an agent in Savannah can't see Charleston collections)
- Referrals track across the site they were created in
- The `db.create_all()` call in `app/__init__.py` automatically creates social tables in every site DB on first access

Cross-site social features (Phase 4) would require a shared table or registry-level tracking.

---

## Data Models

### File: `app/models_social.py`

All models use the existing `db` instance from `app/models.py` and inherit multi-tenant routing automatically via `MultiTenantSQLAlchemy`.

### SocialShare

The core social action — one person shares a listing or collection with another.

```
social_shares
├── id                  INTEGER PK
├── listing_id          INTEGER FK(listings.id) NULLABLE  ← what was shared
├── collection_id       INTEGER FK(social_collections.id) NULLABLE
├── share_type          VARCHAR(20) NOT NULL DEFAULT 'listing'  ← listing | collection
├── sharer_id           INTEGER FK(users.id) NULLABLE     ← NULL for guests
├── sharer_name         VARCHAR(120)
├── sharer_email        VARCHAR(254)
├── recipient_email     VARCHAR(254) NOT NULL INDEX
├── recipient_name      VARCHAR(120)
├── recipient_user_id   INTEGER FK(users.id) NULLABLE     ← linked when they sign in
├── relationship        VARCHAR(30)                        ← friend, family, coworker, neighbor, client, agent
├── message             TEXT                               ← personal note
├── share_token         VARCHAR(64) UNIQUE NOT NULL INDEX  ← URL token
├── status              VARCHAR(20) NOT NULL DEFAULT 'sent' ← sent → viewed → clicked → replied
├── created_at          DATETIME
├── viewed_at           DATETIME                           ← set on first landing page view
└── clicked_at          DATETIME
```

**Indexes:** share_token (unique), listing_id, sharer_id, recipient_email, recipient_user_id

**Key methods:**
- `generate_token()` — `secrets.token_urlsafe(32)`
- `mark_viewed()` — sets `viewed_at` and status on first view
- `mark_clicked()` — sets `clicked_at` and status

### SocialReaction

A recipient's feedback on a shared listing.

```
social_reactions
├── id                  INTEGER PK
├── share_id            INTEGER FK(social_shares.id) NOT NULL INDEX
├── reactor_user_id     INTEGER FK(users.id) NULLABLE
├── reactor_email       VARCHAR(254) NOT NULL
├── reaction_type       VARCHAR(30) NOT NULL   ← love, interested, great_location, too_expensive, not_for_me
├── comment             TEXT
└── created_at          DATETIME

UNIQUE(share_id, reactor_email)
```

**Reaction types** (defined as `REACTION_TYPES` constant):

| Key | Label | Icon | Color |
|-----|-------|------|-------|
| `love` | Love It | `bi-heart-fill` | `text-danger` |
| `interested` | Interested | `bi-eye-fill` | `text-primary` |
| `great_location` | Great Location | `bi-geo-alt-fill` | `text-success` |
| `too_expensive` | Too Pricey | `bi-currency-dollar` | `text-warning` |
| `not_for_me` | Not For Me | `bi-x-circle` | `text-secondary` |

### SocialCollection

A curated group of listings that can be shared as a unit.

```
social_collections
├── id                  INTEGER PK
├── creator_id          INTEGER FK(users.id) NOT NULL INDEX
├── title               VARCHAR(200) NOT NULL
├── description         TEXT
├── share_token         VARCHAR(64) UNIQUE NOT NULL INDEX
├── is_public           BOOLEAN DEFAULT FALSE
├── share_count         INTEGER DEFAULT 0
├── view_count          INTEGER DEFAULT 0
├── created_at          DATETIME
└── updated_at          DATETIME
```

**Property:** `listing_count` — dynamic count via `items.count()`

### SocialCollectionItem

A listing within a collection. Ordered by `position`.

```
social_collection_items
├── id                  INTEGER PK
├── collection_id       INTEGER FK(social_collections.id) NOT NULL INDEX
├── listing_id          INTEGER FK(listings.id) NOT NULL INDEX
├── note                TEXT              ← why this listing is in the collection
├── position            INTEGER DEFAULT 0
└── added_at            DATETIME

UNIQUE(collection_id, listing_id)
```

### Referral

Tracks user-to-user referral invitations and conversion status.

```
referrals
├── id                  INTEGER PK
├── referrer_id         INTEGER FK(users.id) NOT NULL INDEX
├── referred_email      VARCHAR(254) NOT NULL INDEX
├── referred_user_id    INTEGER FK(users.id) NULLABLE  ← linked on registration
├── referral_code       VARCHAR(20) UNIQUE NOT NULL INDEX
├── status              VARCHAR(20) NOT NULL DEFAULT 'invited' ← invited → registered → active → converted
├── created_at          DATETIME
├── registered_at       DATETIME
└── converted_at        DATETIME

UNIQUE(referrer_id, referred_email)
```

**Key method:** `generate_code()` — `secrets.token_urlsafe(8).upper()[:10]`

---

## Routes

### Blueprint: `social_bp` (prefix: `/social`)

All routes respect multi-tenant context via `g.site`. URLs in production look like:
```
/home_finder_agents_social/site/charleston/social/share
/home_finder_agents_social/site/charleston/social/s/abc123token
```

#### Sharing

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| `POST` | `/share` | None | Create a share (form submit from modal) |
| `GET` | `/s/<token>` | None | Share landing page (public, tracks views) |
| `POST` | `/react/<share_id>` | None | Add/update reaction (form or AJAX) |
| `GET` | `/shared-with-me` | Login | Inbox: listings shared with current user |
| `GET` | `/my-shares` | Login | Outbox: what I've shared + status |
| `GET` | `/copy-link/<listing_id>` | None | Generate shareable link (AJAX, returns JSON) |

#### Collections

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| `GET` | `/collections` | Login | List my collections |
| `GET/POST` | `/collections/create` | Login | Create new collection |
| `GET` | `/collections/<id>` | Login | View collection detail |
| `GET` | `/c/<token>` | None | Public collection view |
| `POST` | `/collections/<id>/add` | Login | Add listing to collection |
| `POST` | `/collections/<id>/remove/<item_id>` | Login | Remove listing from collection |
| `POST` | `/collections/<id>/share` | Login | Share collection via email |

#### Referrals

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| `GET` | `/referral` | Login | Referral dashboard + code |
| `POST` | `/referral/invite` | Login | Send referral invitation email |
| `GET` | `/r/<code>` | None | Referral landing (stores code in session) |

#### Analytics

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| `GET` | `/analytics` | Admin | Social analytics dashboard |

---

## Templates

### Directory: `app/templates/social/`

| Template | Route | Description |
|----------|-------|-------------|
| `share_landing.html` | `/s/<token>` | Beautiful standalone page: listing detail, sharer's note, reaction buttons, re-share modal, signup CTA |
| `shared_with_me.html` | `/shared-with-me` | Card grid of received shares with "New" badges |
| `my_shares.html` | `/my-shares` | Table: listing thumbnail, recipient, status badge, reaction count, date |
| `collections.html` | `/collections` | Card grid of user's collections with stats |
| `collection_create.html` | `/collections/create` | Simple form: title, description, public toggle |
| `collection_detail.html` | `/collections/<id>` | Listing cards with remove buttons, share modal, copy-link button |
| `collection_public.html` | `/c/<token>` | Public view with gradient hero, listing cards, signup CTA |
| `referral.html` | `/referral` | Referral code display, invite form, history table |
| `referral_landing.html` | `/r/<code>` | Gradient hero, feature pitch, signup CTA |
| `analytics.html` | `/analytics` | KPI cards, most-shared table, recent shares table |

### UI Integration in Existing Templates

#### `base.html` — Navbar

Added **Social** dropdown (pink accent `#f093fb`) between Watch and Tour:
- Shared With Me
- My Shares
- My Collections
- Refer a Friend
- Social Analytics (admin only)

#### `dashboard/index.html` — Listing Cards

- **Share button** (paper plane icon) added to each listing card's action row
- **Share modal** rendered per-listing with: recipient email, name, relationship selector, message textarea, "Copy Link" button
- **`copyShareLink()`** JavaScript function for AJAX link generation

#### `dashboard/detail.html` — Listing Detail

- **"Share & Collect" card** added to sidebar (purple accent border)
  - "Share This Listing" button → opens share modal
  - "Add to Collection" dropdown listing user's collections
  - Social proof: "X people shared this listing"
- **Share modal** at page bottom with full form

---

## Email Templates

### Directory: `app/templates/email/`

All emails use inline CSS for maximum email client compatibility. Consistent design language with gradient headers and card-style content.

| Template | Trigger | Subject Line |
|----------|---------|-------------|
| `share_notification.html` | Share created | "{Sharer} shared a listing with you on HomeFinder!" |
| `reaction_notification.html` | Reaction added | "{Reactor} reacted to your shared listing!" |
| `collection_share_notification.html` | Collection shared | "{Sharer} shared a collection with you on HomeFinder!" |
| `referral_invitation.html` | Referral invite sent | "{Username} invited you to HomeFinder!" |

**Email structure:**
```
┌─────────────────────────────────┐
│  Gradient Header                │  ← Emoji + headline + subtitle
├─────────────────────────────────┤
│  Content Card                   │  ← Listing photo, price, address, message
│  ┌─────────────────────────┐    │
│  │  Listing Preview Card   │    │  ← (share_notification only)
│  └─────────────────────────┘    │
│                                 │
│      [ CTA Button ]            │  ← "View Listing & React"
├─────────────────────────────────┤
│  Footer                        │  ← "HomeFinder Social"
└─────────────────────────────────┘
```

---

## Security Considerations

### Share Tokens

- Generated via `secrets.token_urlsafe(32)` — 256-bit entropy
- Unique index prevents collisions
- No expiration currently (consider adding TTL in Phase 2)
- Token-based access means no login required to view shares — by design

### Authorization

- Collections: only creator can modify; public flag controls read access
- Reactions: anyone with the share token can react (by design — recipients may not have accounts)
- Analytics: restricted to `is_admin` (owner, agent, master)
- Referral invites: login required (prevents spam)
- Share creation: no login required (guests can share)

### Input Validation

- Email fields validated by HTML5 `type="email"` + server-side format check
- Message/note fields: no length limit currently (consider adding `maxlength` in Phase 2)
- Listing/collection IDs validated against database (404 on invalid)
- CSRF: handled by Flask's session-based form handling (all POST routes use form submission)

### Data Privacy

- Share landing pages do not expose recipient's email to the sharer
- Reaction notifications reveal only the reactor's name, not their email
- Guest sharers provide their name/email voluntarily
- No PII stored beyond what the user explicitly provides

---

## Database Migration Strategy

Social tables are created automatically by `db.create_all()` during app startup. No manual migration needed.

**How it works:**
1. `app/__init__.py` imports `app.models_social` (via `importlib.import_module`)
2. This registers all social model classes with SQLAlchemy's metadata
3. `db.create_all()` creates any missing tables in both the default DB and per-site DBs
4. Per-site DBs get tables created on first request via `_get_site_engine()` → `db.metadata.create_all()`

**Adding columns later:** Use the existing `app/migrations.py` pattern — add migration functions that run `ALTER TABLE` via raw SQL, tracked by a migrations metadata table.

---

## Future Technical Work

### Phase 2: Points System

New model: `UserPoints`
```
user_points
├── id              INTEGER PK
├── user_id         INTEGER FK(users.id) UNIQUE
├── balance         INTEGER DEFAULT 0
├── lifetime_earned INTEGER DEFAULT 0
└── updated_at      DATETIME

user_point_log
├── id              INTEGER PK
├── user_id         INTEGER FK(users.id)
├── delta           INTEGER          ← positive = earn, negative = spend
├── reason          VARCHAR(50)      ← share_created, reaction_received, signup_referral, etc.
├── reference_id    INTEGER          ← FK to share/referral/etc.
└── created_at      DATETIME
```

Earning logic integrated into existing routes:
- `social.share_listing` → +1 point
- `social.react_to_share` → +3 points to sharer
- `auth.register` → check session for referral_code → +10 points to referrer

### Phase 2: "Add a Home" (Friend-Listed)

New model: `FriendListing`
```
friend_listings
├── id                  INTEGER PK
├── lister_id           INTEGER FK(users.id) NOT NULL
├── address             TEXT NOT NULL
├── city                VARCHAR(80)
├── zip_code            VARCHAR(10)
├── latitude            FLOAT
├── longitude           FLOAT
├── asking_price        INTEGER
├── beds                INTEGER
├── baths               FLOAT
├── sqft                INTEGER
├── year_built          INTEGER
├── description         TEXT
├── photo_urls_json     TEXT        ← JSON array of uploaded photo URLs
├── relationship        VARCHAR(30) ← my_home, friend, neighbor, family
├── permission_confirmed BOOLEAN NOT NULL DEFAULT TRUE
├── status              VARCHAR(20) DEFAULT 'active' ← active, expired, removed, reported
├── created_at          DATETIME
├── expires_at          DATETIME   ← created_at + 90 days
└── removed_at          DATETIME
```

Integration with existing listing display:
- Render friend-listed homes alongside scraped listings in `dashboard/index.html`
- Different badge style: "Neighborhood Tip" with a distinct color
- No deal score (omit score circle)
- Photo upload to `static/uploads/friend_listings/<id>/` directory

### Phase 3: Stripe Integration

- `pip install stripe`
- Owner subscription: Stripe Checkout session → webhook → update registry.db `subscription_status`
- Usage billing: monthly invoice with metered scraping calls
- Agent Pro: simple monthly subscription via Stripe Customer Portal

---

## Configuration

### New Environment Variables (`.env`)

None required for Phase 1. Future phases:

```bash
# Phase 2
POINTS_DAILY_CAP=50
FRIEND_LISTING_EXPIRY_DAYS=90

# Phase 3
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_OWNER_PRICE_ID=price_...
STRIPE_AGENT_PRO_PRICE_ID=price_...
```

### URL Prefix

All social routes are served under the app's URL prefix:
```
https://www.toughguycomputing.com/home_finder_agents_social/site/<key>/social/...
```

Waitress `url_prefix="/home_finder_agents_social"` handles prefix stripping. `SitePathMiddleware` handles `/site/<key>/` extraction. Social routes work transparently within both layers.

---

## Testing Checklist

### Share Flow
- [ ] Guest shares a listing → email sent → landing page loads → reaction works
- [ ] Logged-in user shares → sharer_id populated → "My Shares" shows it
- [ ] Recipient views share → status updates to "viewed" → viewed_at set
- [ ] Recipient reacts → reaction saved → sharer notified via email
- [ ] Copy-link AJAX → returns valid URL → URL loads share landing page
- [ ] Re-share from landing page → new share created → email sent

### Collections
- [ ] Create collection → appears in "My Collections"
- [ ] Add listing to collection → item appears → position set correctly
- [ ] Remove listing → item deleted → collection count updates
- [ ] Share collection → email sent → public view loads
- [ ] Public collection link → view_count increments → listings display
- [ ] Only creator can modify (403 for others on private collections)

### Referrals
- [ ] Generate referral code → displays in dashboard
- [ ] Send invitation → email sent → referral record created
- [ ] Click referral link → code stored in session → landing page loads
- [ ] Register with active referral session → referral status updates (future: Phase 2)

### Multi-Tenant
- [ ] Shares created in site A don't appear in site B
- [ ] Social tables exist in all per-site databases
- [ ] Social nav links preserve site context (include `/site/<key>/`)

### Email
- [ ] Share notification renders correctly in Gmail, Outlook
- [ ] Reaction notification includes listing address
- [ ] Collection share includes collection title and listing count
- [ ] Referral invitation includes referrer's username
- [ ] All emails fail gracefully (logged, not raised) if SMTP is down
