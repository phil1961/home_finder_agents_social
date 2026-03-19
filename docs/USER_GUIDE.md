# HomeFinder — User Guide

**Version:** 2026.03.19a
**Last Updated:** 2026-03-19

---

## Getting Started

### Creating an Account

1. Visit your market's welcome page (e.g., `https://www.toughguycomputing.com/home_finder_agents/welcome`)
2. Select your market from the available options
3. Click **Register** in the top navigation
4. Enter your email, username, and password
5. Check your email for a verification link — click it to activate your account
6. Log in and start exploring listings

No account? No problem — you can browse listings, view deal scores, and flag favorites as a guest. Your flags are saved in your browser session. Create an account to make them permanent and unlock AI analysis.

---

## Browsing Listings

### Dashboard

The main dashboard shows all active listings in your market, sorted by deal score (highest first by default).

**"Since Your Last Visit" Summary:**
At the top of the dashboard, a summary card shows what's changed since you last logged in:
- **New listings** added to the market
- **Price drops** on active listings
- Guests see the total number of scored listings and the top deal score

This card appears automatically — no setup required.

**Filter bar:**
- **Area** — Filter by neighborhood or submarket
- **Sort** — Deal Score (default), Price asc/desc, Newest, Yard Size
- **Min Score** — Only show listings above a certain deal score
- **Flags** — Show only your Favorites, Maybes, or Hidden listings
- **Source** — Filter by Zillow or Realtor data source
- **Max Mi** — Maximum distance from your selected landmark (0.5 / 1 / 2 / 3 / 5 / 10 / 15 / 25 mi; only appears when a landmark is selected in Preferences)

**Each listing card shows:**
- Photo, address, price
- Beds / Baths / Sqft
- Your personalized deal score (colored green/yellow/red)
- Your flag status (heart/star icon)

### Map View

Click **Map** in the navigation to see all listings plotted on an interactive map. Click any marker to see a summary popup with a link to the full detail page.

### Listing Detail

Click any listing to see the full detail page:

- **Photo gallery** with full-size images
- **Property details** — beds, baths, sqft, lot size, year built, HOA, tax. If the listing has not yet been enriched with full details, a **"Fetch Property Details"** button appears. Click it to fetch data from Zillow/Realtor via AJAX -- a spinner shows progress, and the description and additional fields appear without a full page reload. If many fields are updated, the page auto-reloads to show all changes. If the API quota is exceeded (429) or the service is unavailable (503), an appropriate message is displayed with a "Try Again" option. Already-enriched listings show their description immediately.
- **18-factor deal score breakdown** — see exactly how each factor contributes (including proximity to your selected landmark)
- **Google Maps directions** — a "Directions from [landmark name]" link opens Google Maps with driving directions from your selected POI landmark to the listing
- **AI Deal Brief** — click "Analyze" for a Claude AI assessment
- **Your Notes** — add personal notes and track visit status
- **Watch This Street** — one-click to monitor the street for new listings

---

## Flagging Listings

Flag any listing to organize your search:

| Flag | Icon | Purpose |
|------|------|---------|
| **Favorite** | Heart | Your top picks |
| **Maybe** | Star | Worth a second look |
| **Hidden** | Eye-slash | Not interested — hides from default view |

Click the flag icon on any listing card or detail page. Click again to remove.

**Progressive Milestones:**
As you flag listings, HomeFinder offers timely suggestions:
- **1st favorite** — encouragement to keep exploring
- **3rd favorite** — suggestion to try AI Portfolio Analysis
- **5th favorite** — prompt to plan a tour of your picks
- Guests are nudged to create a free account at the 3rd favorite

**As a guest:** Flags are saved in your browser session (cleared when you close the browser).
**With an account:** Flags are saved permanently and accessible from any device.

---

## Deal Scores

Every listing receives a personalized deal score from 0 to 100 based on **18 factors** weighted to your preferences.

### The 18 Factors

| Factor | What It Measures |
|--------|------------------|
| **Price** | How the price fits your budget (sweet spot = ~70% of max) |
| **Size** | Square footage (larger = higher score) |
| **Yard** | Lot size (bigger lot = higher score) |
| **Features** | Garage, porch, patio, bedroom/bathroom count |
| **Flood Risk** | FEMA flood zone and elevation |
| **Year Built** | Age of construction (newer = higher) |
| **Single Story** | Single-story preference |
| **Price/Sqft** | Value relative to local benchmarks |
| **Days on Market** | Freshness (newer listings score higher) |
| **HOA** | Monthly HOA fees (lower = higher score) |
| **Medical Proximity** | Distance to nearest hospital |
| **Grocery Proximity** | Distance to nearest grocery store |
| **Community Pool** | Community pool availability |
| **Property Tax** | Annual tax rate relative to price |
| **Lot Ratio** | Lot size vs. house size |
| **Price Trend** | Recent price changes (drops = higher score) |
| **Walkability** | Walkability score |
| **Proximity POI** | Distance to your selected landmark (per-user) |

### Customizing Your Preferences

Navigate to **Preferences** to adjust:

- **Importance weights** (0–10) for each of the 18 factors
- **Price range** — min and max budget
- **Must-have features** — garage, porch, patio requirements
- **Distance from landmark** — select a point of interest from the dropdown to enable proximity scoring
- **Avoid areas** — neighborhoods to exclude from scoring
- **Target areas** (owner and master only) — name groups of zip codes as areas; owners can label and assign zips from the master's zip list but cannot add new zips

Your deal scores update instantly based on your preferences.

### Proximity to a Landmark (POI Scoring)

Select a landmark from the "Distance from..." dropdown on the Preferences page to enable distance-based scoring. When a landmark is selected:

- The **imp_proximity_poi** slider (0--10) sets how much distance matters to your deal scores
- Listing detail pages show a **POI score bar** with the distance in miles and a color-coded label: walking distance, very close, short drive, moderate drive, or far
- Dashboard listing cards display a **distance badge** (green / blue / amber / red) next to feature tags
- A **"Max Mi" filter** appears in the dashboard filter bar (0.5 / 1 / 2 / 3 / 5 / 10 / 15 / 25 mi) to show only listings within a chosen radius
- The **Map page** shows all site landmarks as red star icons with name tooltips on hover

Each user picks their own landmark and importance weight, so proximity scoring is fully personal.

### My Landmarks (Personal POI)

In addition to site-wide landmarks managed by owners, you can add up to **3 personal landmarks** that are meaningful to you -- a relative's house, a favorite park, your workplace, etc.

**Adding a personal landmark:**

1. Navigate to **Preferences**
2. Expand the **"My Landmarks"** section in the scoring panel
3. Add a landmark using either method:
   - **Search** -- Type a place name or address to search via Nominatim (results are bounded to your market area)
   - **Map click** -- Click the mini Leaflet map to place a pin at any location. The map has an expand button to toggle between 150px and 400px height for easier browsing.
   - You can combine both: search to get close, then click the map to fine-tune the location
4. Enter any name you want (e.g., "Grandma's House", "Folly Beach Trail", "My Office")
5. Click **Add** -- the landmark is saved immediately via AJAX (no page reload)

**Managing landmarks:**
- A counter shows your current usage (e.g., "2/3")
- When you reach 3 landmarks, the add form is replaced with a "Maximum 3 reached" message
- Click the delete button next to any landmark to remove it

**Using personal landmarks for scoring:**
- Your personal landmarks appear in the "Distance from..." dropdown under a **"My Landmarks"** group, separate from site-wide landmarks
- Select any personal landmark to activate proximity scoring based on distance to that location

---

## AI-Powered Analysis

HomeFinder uses Claude AI to provide three types of analysis:

### Deal Brief

Available on any listing detail page. Click **"Analyze This Deal"** to get:

- **Summary** — One-paragraph assessment
- **Strengths** — What makes this property attractive
- **Concerns** — Red flags and risk factors
- **Negotiation Tips** — Leverage points for making an offer
- **Verdict** — Buy, negotiate, or pass recommendation

### Portfolio Analysis

From the dashboard, click **"Analyze Portfolio"** on any flag group (Favorites, Maybes, or Hidden). Claude will:

- **Rank** your flagged listings from best to worst value
- **Identify patterns** in what you're drawn to
- **Suggest strategy** for your search
- **Highlight a dark horse** — an overlooked gem in your list

### Preference Coaching

From the Preferences page, click **"Coach My Preferences"** to get AI feedback on:

- **Strengths** in your current weighting
- **Blind spots** you might be overlooking
- **Suggested tweaks** to find better deals
- **Local market insight** specific to your area

All AI results are cached so you can revisit them without waiting.

---

## Street Watch

Monitor specific streets for new listings, price drops, and status changes.

### Setting Up a Watch

**From a listing detail page:**
1. Find the **"Watch This Street"** card in the sidebar
2. The street name is auto-extracted from the listing address
3. Click **"Watch"** — done!

**From the Watch management page:**
1. Click **Watch** in the navigation
2. Select a zip code from the dropdown
3. Start typing a street name — pick from the autocomplete suggestions
4. Click the **+** button

### How It Works

- The nightly pipeline checks every watched street for changes
- You'll receive an **email digest** when events are detected:
  - **New listing** on your watched street
  - **Price drop** on a listing you're watching
  - **Back on market** — a previously delisted listing returns
- Each alert includes a photo, price, and direct link to the listing

### Managing Watches

- Visit `/watch` to see all active watches and alert counts
- Click **X** on any watch card to stop monitoring
- Each alert email includes a **one-click unsubscribe** link

**Note:** Street Watch requires a free account. Guests are prompted to register.

---

## Tour Planning

Organize property visits from your flagged listings:

1. Click **Tour** in the navigation
2. Your Favorites and Maybes are listed with notes and visit status
3. Mark listings as **Visited**, **Scheduled**, or **Made Offer**
4. Add notes for each property

---

## Digest View

Click **Digest** for an email-style summary of your top listings — great for sharing with a partner or agent.

---

## Settings

Click the **gear icon** in the navigation bar to open the Settings page. It contains three cards:

### Help Level

Control how much contextual guidance the app shows:
- **Level 1** — Minimal: tooltips and hints are hidden
- **Level 2** — Standard (default): helpful tips appear where relevant
- **Level 3** — Verbose: detailed explanations and onboarding prompts throughout

### Power Mode

Toggle advanced features on or off:
- **Off** — Simplified interface, best for casual browsing
- **Low** (default for guests) — Core features visible
- **High** — All advanced features enabled (bulk actions, export, extended filters)

### AI Analysis Mode

Control how AI deal analysis works:
- **Off** (default for guests) — AI analysis buttons are hidden
- **On** — Standard AI deal briefs, portfolio analysis, and preference coaching
- **Tune** — Enables **AI Tune** with a Buyer Profile form (see below)

---

## AI Tune and Buyer Profile

When AI Mode is set to **Tune**, a Buyer Profile form appears on the Settings page. Fill in your structured preferences so that Claude AI can personalize its analysis to your specific situation:

- **Timeline** — When you plan to buy
- **Priorities** — What matters most to you (e.g., school district, commute, yard)
- **Dealbreakers** — Hard requirements that would rule out a property
- **Other details** — Lifestyle notes, household info, etc.

Your buyer profile is saved in your account and used automatically whenever you request a Deal Brief, Portfolio Analysis, or Preference Coaching. AI responses become significantly more relevant and actionable with a completed profile.

---

## Great Deal Score

Set a **Great Deal Threshold** on the Preferences page (default: 80) to highlight exceptional listings:

- Listings scoring at or above your threshold receive a **"Great Deal!"** badge on their card
- Cards for great deals display a **golden glow** effect to stand out visually
- The listing detail page plays a brief **confetti animation** when you view a great deal
- The threshold is personal -- adjust it up or down to match your standards

---

## Help Page

Click **Help** in the navigation bar to open the full Help page. It provides a comprehensive overview of features, keyboard shortcuts, and tips organized by topic. (Previously a dropdown menu, Help is now a dedicated page.)

---

## Account Management

### Updating Preferences
Navigate to **Preferences** to change scoring weights, price range, and feature requirements at any time.

### Password Reset
Click **Forgot Password** on the login page to receive a reset email.

### Closing Your Account
Navigate to **Settings -> Close Account**. This permanently deletes your account, flags, notes, and watch data.

---

## Working with an Agent

If your account was created by a real estate agent (as a **principal**):

- You can edit your scoring weights and preferences
- You can view listings, flag, and add notes
- Your agent's branding (color, logo, tagline) appears in the navigation bar
- Click **Contact Agent** to send your agent a message
- Your agent can see your flags and notes to guide showings
- Empty states (no favorites yet, no tour planned) include personalized encouragement from your agent

---

## Points System

Earn points by participating in the HomeFinder community. Your points balance is displayed as a badge in the navigation bar.

### How to Earn Points

| Action | Points |
|--------|--------|
| Share a listing | +1 |
| Reaction received on your share | +3 |
| Create a collection | +2 |
| Submit a friend listing ("Add a Home") | +5 |
| Referral registers an account | +10 |

**Daily cap:** You can earn up to 50 points per day.

### Viewing Your Points History

Navigate to **Social > Points** (or visit `/social/points`) to see a detailed log of every point you have earned, when, and why.

---

## Add a Home (Friend Listings)

Know about a home that is not listed on HomeFinder? Submit it as a **Neighborhood Tip** so other users can see it.

### Submitting a Home

1. Click **Add a Home** in the navigation (requires a free account)
2. Fill in the property details:
   - Address (required)
   - Price
   - Beds, baths, square footage
   - Photos
   - Your relationship to the property (neighbor, friend of owner, etc.)
   - Permission checkbox confirming you have consent to share
3. Submit -- your tip enters **pending** review

### What Happens After Submission

- Your tip appears with a green **"Neighborhood Tip"** badge
- A local agent reviews your submission and may enrich it with additional details (lot size, year built, coordinates, features)
- **Approved** tips become full listings with source "community" and are scored like any other listing
- **Rejected** tips are removed (the agent may provide a reason)
- Tips expire automatically after **90 days** if not approved

You earn **+5 points** when you submit a friend listing.

---

## Sharing and Social Proof

### Sharing Listings

Share any listing or collection with friends and family via email or a shareable link. Add a personal message to give context. You earn **+1 point** per share, and **+3 points** each time someone reacts to your share.

### Share Counts and Badges

Listing cards display a share count badge showing how many users have shared that property. High share counts indicate popular listings.

### Reactions

Recipients of a shared listing can react with:
- **Love** -- they are excited about this property
- **Interested** -- worth a closer look
- **Not for me** -- does not fit their needs

The listing detail page shows a grouped reaction summary with icons and counts.

### Most Shared This Week

The dashboard features a **"Most Shared This Week"** section showing the top 5 most-shared listings in a horizontal scroll. These are the properties generating the most community buzz.

---

## Referrals

### How Referral Codes Work

Every registered user has a unique referral code. Share your code (or use the referral link) with friends who are looking for a home.

### Registration Attribution

When someone registers using your referral link:
1. The referral code is stored in their session during browsing
2. At registration, HomeFinder detects the code and links the new user to you
3. You earn **+10 points** when the referral completes registration
4. The referral relationship is tracked permanently for attribution

---

## Leaderboard

Visit the monthly leaderboard to see how the community is engaging:

- **Top 10 Sharers** -- users who shared the most listings this month
- **Top 10 Referrers** -- users who brought the most new members

The leaderboard resets monthly.

---

## Installing HomeFinder as an App

On mobile devices, a banner appears at the bottom of the dashboard inviting you to install HomeFinder as a standalone app on your home screen.

- **Android (Chrome, Edge, Samsung Internet):** Tap the "Install" button in the banner. Your browser's native install prompt appears -- confirm to add HomeFinder to your home screen.
- **iOS (Safari):** The banner shows manual instructions: tap the Share button in Safari, then select "Add to Home Screen."
- **Other browsers (Opera, Firefox, etc.):** The banner shows instructions to use the browser menu to add HomeFinder to your home screen.

Once installed, HomeFinder opens full-screen without browser chrome, just like a native app.

The banner appears after a 2-second delay and can be dismissed for 30 days. It does not appear if you have already installed the app or if you are browsing on a desktop.

---

## Tips for Best Results

1. **Set your price range first** — this has the biggest impact on deal scores
2. **Adjust importance weights** over time as you learn what matters most
3. **Use AI analysis** on your top 5 picks before making decisions
4. **Watch streets** in neighborhoods you love — you'll be first to know about new listings
5. **Check the dashboard daily** — new listings are scored as soon as the pipeline runs
6. **Use "Maybe" generously** — portfolio analysis works best with 5–20 listings
