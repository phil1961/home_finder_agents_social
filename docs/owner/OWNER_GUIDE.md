# HomeFinder — Market Owner Guide

**Version:** 2026.03.15
**Last Updated:** 2026-03-15

---

## Overview

As a market owner, you manage a HomeFinder site instance for a specific geographic market. You control agent approval, site-wide AI prompts, pipeline scheduling, and have access to usage metrics and diagnostics.

---

## Your Responsibilities

| Area | What You Do |
|------|-------------|
| **Agent Management** | Approve, suspend, and reinstate agent accounts |
| **Pipeline** | Monitor nightly data fetches; trigger manual runs |
| **Metrics** | Track user engagement, API costs, listing inventory |
| **Prompts** | Set site-wide AI prompt overrides |
| **Quality** | Monitor deal scores, data freshness, API health |

---

## Agent Management

### Approval Workflow

1. An agent registers via the **Agent Sign Up** page
2. Their account enters **pending** status — they can log in but can't manage clients
3. Navigate to **Admin → Agents** to review pending applications
4. Review their license number, brokerage, and service areas
5. Click **Approve** to activate or **Suspend** to deny

### Agent Notes

For each agent, track:
- **Contract signed** — Business agreement in place
- **Background checked** — Verification completed
- **MLS verified** — License confirmed with MLS

Add free-form notes for any additional context.

### Suspending an Agent

Suspended agents:
- Cannot log in
- Their clients retain access (but see no agent branding)
- Can be reinstated at any time

---

## Data Pipeline

### Nightly Runs

The pipeline runs automatically every night at 3 AM via Windows Task Scheduler:

1. Fetches new listings from Zillow and Realtor for all site zip codes
2. Deduplicates fetched data (normalizes addresses, merges richer data per field)
3. Updates prices and statuses on existing listings
4. Scores all listings using the 18-factor system
5. Runs post-upsert deduplication on existing DB listings (marks duplicates as status="duplicate")
6. Detects Street Watch events (new listings, price drops, back on market)
7. Sends email alerts to watchers

### Manual Trigger

From your dashboard, click **Fetch Now** to run the pipeline on-demand. Results display inline showing:
- Listings fetched
- New vs. updated counts
- Scoring results
- Any errors

**Note:** If no zip codes are configured for the site, both Fetch Now and the nightly pipeline will return a clear error: *"No zip codes configured. Go to Preferences -> Target Areas and add zip codes before fetching."*

### Rescore Only

To recalculate deal scores without fetching new data (e.g., after adjusting area mappings):
```bash
python pipeline.py --site <your_site_key> --rescore
```

### Scheduler Control

Click **Pause Scheduler** to temporarily stop nightly runs (e.g., during maintenance). Click again to resume.

**Note:** A master user can also **lock the scheduler** for a site from the Site Manager page (see below). When the scheduler is locked by a master, the owner cannot override it -- the nightly pipeline is blocked until the master unlocks it.

### Master Site Controls (Site Manager Page)

The following controls are available to master users on the **Manage** page for each site and are enforced in both the scheduled pipeline (`bin/scheduled_pipeline.py`) and the manual Fetch Now route:

- **Scheduler Lock** -- A toggle that force-disables the nightly scheduler for a site. When locked, the owner's Pause/Resume button has no effect. Stored in `registry.db` as `scheduler_locked` (BOOLEAN).
- **Max Fetches Per Run** -- Limits how many listings the pipeline processes per run. Set to 0 for unlimited. Stored in `registry.db` as `max_fetches_per_run` (INTEGER).

---

## Metrics Dashboard

Navigate to **Admin → Metrics** to view:

### User Metrics
- Active users by role (agents, clients, principals, guests)
- Registration trends
- Login frequency

### Listing Metrics
- Total active listings
- Listings by source (Zillow vs. Realtor)
- Score distribution (how many are "great deals" above threshold)
- New listings per pipeline run

### API Metrics
- Call volume by type (Zillow, Realtor, Claude AI)
- Success/failure rates
- Response times
- Estimated costs
- Quota utilization

### Diagnostics

Navigate to **Admin → Diagnostics** for detailed API call logs:
- Individual call records with timestamps
- Error details for failed calls
- Response time trends
- Per-zip-code fetch results

---

## Site-Wide AI Prompts

Override the default AI system prompts for your entire market:

1. Navigate to **Admin → Prompts**
2. Select the prompt type (Deal, Portfolio, or Preferences)
3. Edit the system prompt
4. Save

**Prompt resolution:** Agent-specific → **your site-wide** → system default

### Prompt Editor Tools

Each prompt type (Deal, Portfolio, Preferences) includes three tools to help you write and test prompts:

**Copy Default to Editor** — Loads the built-in default prompt into the textarea so you can start editing from a known-good baseline rather than writing from scratch.

**Validate Syntax** — Checks your prompt for common issues before saving:
- Confirms the prompt mentions "JSON" (required for structured output)
- Verifies all required response keys are present (e.g., summary, strengths, concerns, negotiation, verdict for the Deal type)
- Checks for a "No markdown fences" instruction
- Warns if the prompt is too short or too long
- Confirms a role instruction is present (e.g., "You are a...")
- Returns a green pass with found keys, or yellow warnings listing specific issues

**Test with Sample Data** — Opens a full-width modal with two panels:
- **Left panel: Editable Sample Data** — Fill in realistic test values. Controls vary by prompt type:
  - *Deal:* 15+ validated fields including address, price (with min/max), beds (1-20), baths (0.5 step), sqft, lot sqft, year built (1800-2030), days on market, HOA, tax, price change %, deal score (0-100), flood zone dropdown, feature checkboxes, stories, and market
  - *Portfolio:* Editable monospace textarea pre-loaded with 3 sample properties
  - *Preferences:* 12 range sliders (0-10) for scoring weights plus min beds/baths and price range inputs
- **Right panel: Pretty-formatted preview** — Shows results exactly as users see them:
  - *Deal:* Verdict badge (Strong Buy / Worth Considering / Pass), summary, Strengths, Concerns, Negotiation Strategy
  - *Portfolio:* Big Picture headline, 2x2 grid (Ranking, Patterns, Strategy, Dark Horse), Bottom Line
  - *Preferences:* Assessment headline, 2x2 grid (Well Configured, Blind Spots, Tweaks, Local Insight), Bottom Line
- Response time is displayed, and a raw JSON toggle is available
- "Reset Defaults" restores all sample fields to their original values

The preview calls the actual Anthropic API, so each test incurs a small API cost (logged to ApiCallLog).

### Recommended Customizations

- Add local market context: *"This is the [City] market, known for..."*
- Mention region-specific concerns: flood zones, HOA regulations, school districts
- Set the analysis tone: conservative, balanced, or optimistic
- Include local price benchmarks for the AI to reference

---

## Target Areas & Zip Codes

As an owner, you can label target areas and assign zip codes to them directly from the **Preferences** page:

- **Area name input + clickable zip map** — type an area name and click zips on the map to assign or unassign them to that area
- **Zip list is controlled by the master** — you can only assign zips that the master has added to the site. If you try to add a zip not in the master's list, a warning is displayed. You can choose not to use a zip by leaving it unassigned to any area.
- **Save Target Areas** button saves your area-to-zip mappings
- **Avoid areas** can be set per-user to exclude neighborhoods from scoring

---

## Masquerade

As an owner, you can masquerade as any user in your site:
- View the site through any user's perspective
- See their personalized scores, flags, and notes
- Useful for troubleshooting user-reported issues
- A masquerade banner is always visible
- Click **End Masquerade** to return

---

## Cost Management

### API Call Costs (Estimates)

| API | Cost per Call | Typical Daily Volume |
|-----|---------------|---------------------|
| Zillow Search | $0.005 | 5–15 per zip per run |
| Zillow Detail | $0.005 | On-demand (lazy load) |
| Realtor Search | $0.005 | 5–15 per zip per run |
| Claude Deal Brief | $0.015 | Per user request |
| Claude Portfolio | $0.025 | Per user request |
| Claude Preferences | $0.015 | Per user request |

### Reducing Costs

- **Limit zip codes** to areas with genuine buyer interest
- **Pause the scheduler** during low-activity periods
- **Monitor the diagnostics page** for unusual API consumption
- AI analyses are cached — repeat views don't incur API calls

---

## User Management

Manage user accounts across your site from the admin panel.

### Accessing User Management

Navigate to **Admin > Users** (or visit `/admin/users`) to see all registered users with their roles, status, and activity.

### Suspending a User

1. Find the user in the list
2. Click **Suspend**
3. Optionally enter a reason (this is displayed to the user when they attempt to log in)
4. Confirm -- the user is immediately locked out

Suspended users see the suspension reason on the login page and cannot access any site features.

### Reactivating a User

Click **Reactivate** next to any suspended user to restore their access. All their data (flags, notes, preferences) remains intact.

### Deleting a User

Click **Delete** to permanently disable an account. This renames the user's credentials and locks the account. Use this for spam accounts or users who have requested removal.

### Protection Rules

- **Master accounts** are protected -- only another master can take action on a master account
- **You cannot modify your own account** via the admin panel (prevents accidental self-lockout)
- Owners can manage any non-master user in their site
- Masters can manage any non-master user across all sites

---

## Billing and Quotas

Control API costs with tiered billing plans and usage quotas.

### Billing Tiers

| Tier | AI Analyses | Fetch Calls | Monthly Cost |
|------|-------------|-------------|-------------|
| **Free** | 10 | 50 | $1 |
| **Basic** | 100 | 500 | $10 |
| **Pro** | 500 | 2,000 | $50 |
| **Unlimited** | Unlimited | Unlimited | Custom |

### Detail Enrichment

Listing detail pages now load instantly. If a listing has not been enriched with full property details, users see a **"Fetch Property Details"** button that triggers an AJAX call to fetch data from Zillow/Realtor. This avoids blocking page loads and gives users control over when enrichment happens.

### Quota Enforcement

When a site exceeds its quota:
- **AI analysis requests** return a 429 (rate limited) error with a message explaining the limit
- **Fetch calls** are blocked during pipeline runs
- **Detail enrichment** returns a 429 error with a clear message when quota is exceeded

### Budget Alerts

The system sends email alerts to the site owner at two thresholds:
- **80% of quota** -- warning to review usage or upgrade
- **100% of quota** -- notification that limits are in effect

### Managing Billing

Navigate to **Admin > Billing** (or visit `/admin/billing`) to:
- View current tier and usage with visual progress bars
- See AI analysis count vs. limit
- See fetch call count vs. limit
- Change the billing tier
- Configure the monthly billing cycle reset day

---

## Friend Listing Moderation

Users can submit homes they know about as **Neighborhood Tips**. These submissions require agent review before becoming visible listings.

As an owner, you have visibility into the moderation pipeline:
- View all pending, approved, and rejected friend listings across the site
- Monitor agent review activity and turnaround times
- Tips that go unreviewed expire automatically after 90 days

The day-to-day review workflow is handled by agents. See the [Agent Guide](AGENT_GUIDE.md) for details on the approve/reject process.

---

## Social Digest

Send a weekly summary email to all active users covering their social activity.

### Digest Contents

Each user receives a personalized email including:
- Shares they sent and received during the week
- Reactions on their shared listings
- Community highlights

### Triggering the Digest

The digest can be triggered manually:
1. Navigate to the **Analytics** page
2. Click the **Send Social Digest** button
3. The system generates and sends personalized emails to all active users

---

## Points System Overview

The points system encourages community participation. Users earn points for sharing listings, creating collections, submitting friend listings, and referring new users.

Key details:
- **7 earning actions** with values ranging from +1 to +10 points
- **50-point daily cap** per user prevents abuse
- Users see their balance in the navigation bar and full history at `/social/points`
- The monthly **leaderboard** shows top sharers and top referrers

See [Roles & Permissions](ROLES_AND_PERMISSIONS.md) for the complete points earning table.

---

## Landmark Management

Landmarks are site-wide points of interest that users can select on the Preferences page to enable proximity-based deal scoring (the 18th scoring factor).

### Managing Landmarks

The **"Manage Landmarks"** card appears on the Preferences page (below Target Areas) for owners and masters. Three methods are available to add landmarks:

1. **Search** -- Type a place name to search via Nominatim (OpenStreetMap geocoder). Results are bounded to approximately 30 miles from the site center, US addresses only.
2. **Common landmarks dropdown** -- Select a category (Hospital, University, Airport, Shopping Mall, etc.) to trigger a local search for that type of place.
3. **Map picker** -- Click on the Leaflet map to place a pin. Latitude and longitude are auto-filled from the click location. Enter a name and save.

### How Landmarks Work

- Landmarks are stored in `registry.db` in the `landmarks_json` column (per site)
- Existing landmarks appear in a numbered bordered list with delete buttons
- Add and delete operations use AJAX (no page reload)
- Landmarks appear on the main **Map page** as red star markers with hover tooltips showing the landmark name
- Users select a landmark from the "Distance from..." dropdown on Preferences to activate proximity scoring for their account

### Preferences Page Layout

The Preferences page is organized into three visually distinct sections with bordered containers:

1. **Scoring & Search Preferences** (blue border) -- Importance sliders, price range, beds/baths, features, POI landmark dropdown. Has its own "Save Scoring Preferences" button.
2. **Target Areas** (green border) -- Zip code map, area names, avoid areas. Has its own "Save Target Areas" button.
3. **Landmarks** (red border, owner/master only) -- Map picker, search, common landmarks dropdown, AJAX add/delete. Auto-saves on each action.

Each section saves independently -- changes in one section do not affect the others.

---

## Best Practices

1. **Approve agents promptly** — pending status frustrates new signups
2. **Review metrics weekly** — spot trends in user engagement and API costs
3. **Customize AI prompts** with local expertise — it differentiates your market
4. **Run manual fetches** before sending marketing emails — ensure fresh data
5. **Monitor diagnostics** after pipeline runs — catch API issues early
6. **Keep zip codes focused** — fewer zips = lower costs and faster pipelines
7. **Set billing tiers early** — establish quota limits before inviting users to avoid surprise costs
8. **Monitor friend listing queue** — ensure agents review tips promptly so submitters stay engaged
9. **Send social digests regularly** — weekly digests keep users coming back to the platform
10. **Add key landmarks** — hospitals, universities, airports, and major employers make proximity scoring useful for buyers with commute or lifestyle priorities
