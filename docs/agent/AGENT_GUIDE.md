# HomeFinder — Real Estate Agent Guide

**Version:** 2026.03.14
**Last Updated:** 2026-03-14

---

## Overview

HomeFinder gives real estate agents a powerful digital platform to serve buyers more effectively. As an agent, you get a dedicated dashboard, client management tools, custom branding, and AI-powered analysis — all designed to help you close more deals faster.

---

## Getting Started as an Agent

### Registration

1. Navigate to your market's site
2. Click **Agent Sign Up** (separate from regular registration)
3. Fill in your professional details:
   - Full name, license number, brokerage
   - Phone, bio, service areas
4. Submit — your account enters **pending** status
5. The site owner reviews and approves your application
6. Once approved, you have full agent access

### Agent Dashboard

After approval, click **My Clients** in the navigation to access your agent dashboard:

- **Client roster** with activity indicators
- **Quick stats** — active clients, flagged listings, scheduled visits
- **Client notes** with status checklists

---

## Managing Clients

### Inviting a Client (Principal)

1. From your Agent Dashboard, click **Invite Client**
2. Enter the client's email address
3. The system creates a **principal** account and sends a welcome email
4. The client can log in immediately after verifying their email

**Principal vs. Client accounts:**
- **Principal** — You control their scoring preferences. They can browse, flag, and add notes but can't change weights.
- **Client** — Self-registered user. They control their own preferences. You can view but not edit.

### Client Notes & Checklists

For each client, track:
- **Pre-approved** — Mortgage pre-approval status
- **Signed agreement** — Buyer-agent agreement
- **Tour scheduled** — Upcoming showings
- **Offer submitted** — Active offers
- **Active searching** — Currently looking

Add free-form notes to record conversations, preferences, and next steps.

### Proximity Scoring for Clients

Clients (and principals) can select a landmark on their Preferences page to enable proximity-based scoring -- the 18th deal scoring factor. This is useful for buyers who need to be near a workplace, hospital, school, or other location. Each client picks their own landmark and importance weight, so scores are personalized. Landmarks available in the dropdown are managed by the site owner (see the Owner Guide for details).

### Viewing Client Activity

From your dashboard, you can see each client's:
- Number of flagged listings (favorites/maybes)
- Recent login activity
- Notes and visit statuses on specific listings

### Masquerade Mode

Need to see the site through your client's eyes?

1. Click **View As** next to any of your clients
2. The site renders exactly as they see it — their scores, flags, and preferences
3. A banner at the top reminds you that you're in masquerade mode
4. Click **End Masquerade** to return to your agent view

**Scope:** You can only masquerade as your own clients (principals assigned to you).

---

## Branding

Customize how HomeFinder looks for your clients:

- **Brand color** — Applied to headers and accents when your clients are logged in
- **Logo URL** — Displayed in the navigation bar
- **Icon** — Small icon for mobile/compact views
- **Tagline** — Shown beneath the logo

Navigate to **Agent Dashboard → Branding** to update.

---

## AI Prompt Customization

Override the default AI prompts to match your communication style and market expertise:

### Available Prompt Types

| Prompt | Used For | Default Behavior |
|--------|----------|------------------|
| **Deal** | Individual listing analysis | Adversarial buyer advisor — highlights risks |
| **Portfolio** | Multi-listing comparison | Ranks and compares flagged properties |
| **Preferences** | Scoring weight coaching | Critiques client's importance weights |

### Customizing

1. Navigate to **Prompts** in the agent navigation
2. Select the prompt type to customize
3. Edit the system prompt text
4. Save — your custom prompt applies to all your clients' AI analyses

**Resolution order:** Your agent prompt → site-wide owner prompt → system default

### Prompt Editor Tools

Each prompt type includes tools to help you write, validate, and test your overrides:

**Copy Default to Editor** — Loads the built-in default prompt into the textarea so you can start from a known-good baseline.

**Copy Effective to Editor** — Loads whatever prompt your clients actually see (your override if set, otherwise the site-wide owner prompt or system default). Useful for making incremental tweaks to the currently active prompt.

**Validate Syntax** — Server-side check that flags common issues:
- Missing "JSON" mention (required for structured output)
- Missing required response keys (e.g., summary, strengths, concerns for the Deal type)
- Missing "No markdown fences" instruction
- Length problems (too short or too long)
- Missing role instruction (e.g., "You are a...")
- Results appear as green pass (with found keys) or yellow warnings (with specific issues)

**Test with Sample Data** — Opens a full-width modal with two panels:
- **Left panel: Editable Sample Data** — Controls vary by prompt type:
  - *Deal:* 15+ validated fields (address, price, beds, baths, sqft, lot sqft, year built, days on market, HOA, tax, price change %, deal score, flood zone, features, stories, market)
  - *Portfolio:* Editable monospace textarea with 3 sample properties
  - *Preferences:* 12 range sliders (0-10) for scoring weights plus min beds/baths and price range
- **Right panel: Pretty-formatted preview** — Shows results exactly as your clients see them:
  - *Deal:* Verdict badge (Strong Buy / Worth Considering / Pass), summary, Strengths, Concerns, Negotiation Strategy
  - *Portfolio:* Big Picture headline, 2x2 grid (Ranking, Patterns, Strategy, Dark Horse), Bottom Line
  - *Preferences:* Assessment headline, 2x2 grid (Well Configured, Blind Spots, Tweaks, Local Insight), Bottom Line
- Response time displayed, raw JSON toggle available
- "Reset Defaults" restores all sample fields

The preview calls the actual Anthropic API, so each test incurs a small API cost.

### Tips for Effective Prompts

- Include your market expertise: *"You are an expert on the Charleston, SC Lowcountry market..."*
- Set the tone: professional, casual, data-driven
- Add local context: school districts, flood zones, development plans
- Be specific about what to emphasize: *"Always mention flood insurance costs for Zone AE properties"*

---

## Monitoring Your Clients' Listings

### On Listing Detail Pages

When viewing any listing, you'll see:
- All of your clients' flags on this property
- Their notes and visit statuses
- AI analyses they've generated

### On the Dashboard

The main dashboard shows aggregate activity across all your clients. Use filters to view specific clients' flagged listings.

---

## Street Watch for Clients

Encourage clients to set up Street Watch for streets they're interested in. When a new listing appears or a price drops on a watched street, they'll get an email alert automatically — keeping them engaged without manual effort from you.

---

## Add Listing (Direct Creation)

Agents can create listings directly from the agent dashboard without waiting for the nightly pipeline.

### Creating a Listing

1. Navigate to **Agent Dashboard > Add Listing** (or visit `/agent/add-listing`)
2. Fill in the full listing form:
   - Address, price, beds, baths, square footage
   - Lot size, year built, HOA, tax rate
   - Latitude/longitude for map placement
   - Features (garage, porch, patio, pool, etc.)
   - Photos and description
3. Submit -- the listing is created immediately with source "agent"
4. The listing is scored right away using the 18-factor system

You earn **+5 points** for each listing you create.

---

## Friend Listing Review

Users can submit homes they know about as **Neighborhood Tips**. As an agent, you review and manage these submissions.

### Viewing Pending Tips

Pending friend listings appear in your agent dashboard under a **"Pending Tips"** section. Each entry shows the submitter, address, price, and relationship to the property.

### Review Workflow

For each pending tip, you can:

1. **Review** -- Click to view the full submission details
2. **Edit and Enrich** -- Add missing information before approving:
   - Lot square footage
   - Year built
   - Latitude and longitude (for map placement)
   - Additional features
3. **Approve** -- Creates a real Listing record with source "community". The listing is immediately scored and appears on the dashboard. You earn **+3 points** for each approval.
4. **Reject** -- Removes the tip. You can optionally provide a reason, which is shared with the submitter.

**Expiry:** Unapproved tips expire automatically after 90 days. The `expire_friend_listings()` process handles this.

---

## Points

Agents earn points for community contributions just like other users, plus additional actions specific to the agent role.

### Agent Earning Actions

| Action | Points |
|--------|--------|
| Share a listing | +1 |
| Reaction received on your share | +3 |
| Create a collection | +2 |
| Submit a friend listing | +5 |
| Create a listing directly | +5 |
| Approve a friend listing | +3 |
| Referral registers an account | +10 |

**Daily cap:** 50 points per day.

Your points badge appears in the navigation bar. Visit `/social/points` for a full history.

---

## Leaderboard

The monthly leaderboard shows the **top 10 sharers** and **top 10 referrers** across the site. Active agents who share listings on behalf of clients and bring in new users through referrals can earn high visibility on the leaderboard.

---

## Best Practices

1. **Set up principal accounts** for serious buyers — you control their scoring weights to match what they actually need (not just what they think they want)
2. **Customize AI prompts** to reflect your expertise — clients will see you as the source of market insight
3. **Use masquerade mode** before client meetings to see exactly what they're seeing
4. **Track checklists diligently** — pre-approval, agreements, and offer status keep your pipeline organized
5. **Review client flags weekly** — spot patterns in what they're gravitating toward
6. **Encourage Street Watch** — clients who get alerts stay engaged with your service
7. **Review friend listings promptly** — pending tips expire after 90 days; fast approvals reward engaged users
8. **Create listings directly** for pocket listings or off-market deals — they are scored immediately and earn you points
9. **Share listings on behalf of clients** — you earn points and build visibility on the leaderboard
