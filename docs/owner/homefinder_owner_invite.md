# HomeFinder Social

**Owner Access Package — Dover, DE Market**
Prepared for: [NAME] — coastalgraphics.com

---

## Welcome

You've been set up as an Owner on HomeFinder Social, an AI-powered real estate discovery platform. Your access covers the Dover, DE market. As an owner, you have full visibility into the site — listings, users, agents, community tips, and the scoring engine.

## What HomeFinder Social Does

HomeFinder Social is a multi-tenant real estate platform that layers social features and AI deal analysis on top of MLS/Zillow listing data. Each market runs as an independent site with its own listings, users, and agents.

### Core Features

- **AI Deal Scoring (18 factors)** — Every listing is scored 0-100 on price, size, yard, HOA, flood risk, taxes, proximity to landmarks, and more. Users adjust weighting sliders to reflect their own priorities. Claude AI generates plain-English negotiation briefs for individual listings and side-by-side portfolio comparisons.

- **Social Sharing** — Users share listings with friends and family via email or shareable link. Recipients can react (Love It, Interested, Too Pricey, etc.) and the sender sees all reactions on their My Shares page.

- **Collections** — Users group favorites into named, shareable collections — useful for comparing options with a partner or presenting shortlists.

- **Neighborhood Tips** — Community members submit unlisted homes for sale. Agents review, enrich, and approve them to appear alongside standard listings.

- **Street Watch** — Email alerts when new listings, price drops, or status changes appear on a watched street.

- **Tour Planner** — Users star listings, plot them on a map, and build a driving itinerary. Agents see flagged properties in real time.

- **Points & Leaderboard** — Gamification layer rewarding shares, referrals, tips, and reactions. Monthly leaderboard tracks top contributors.

## What the Owner Role Can Do

As an owner, you have access to everything on the site:

- Full listing database with deal scores and raw data
- User management — view, promote, or deactivate accounts
- Agent dashboard — see what agents are working on and listings they've added
- Neighborhood Tips queue — approve or reject community submissions
- Social activity — shares, reactions, collections, leaderboard
- Site configuration and billing controls
- Target area labeling — organize zip codes into named areas for the dashboard filter
- Landmark management — set up points of interest for proximity-based scoring
- AI prompt customization — edit, validate, and preview AI analysis prompts
- Documentation access — owner and general docs

## Areas of Special Interest for UI Review

Given your background in visual design, a few areas worth particular attention:

- **Listing Cards** — The primary browse surface. Score badges, share counts, and action buttons all live here. Consistency and visual hierarchy matter most.

- **Deal Score Display** — The 0-100 score and weighting sliders are central to the product's value prop. Are they intuitive and trustworthy-looking?

- **AI Negotiation Brief** — Long-form AI text output on listing detail pages. Readability and formatting of this content is a known area for improvement.

- **Mobile Experience** — The platform is used on phones during home tours. Responsive behavior on listing cards and the map view are priority areas.

- **Social Flows** — Share modal, reaction display, and My Shares page. These are newer features and less refined than core search.

- **Guest vs. Logged-In State** — A key design principle is that guests can do almost everything without an account. Is that boundary clear and inviting rather than frustrating?

## Technical Notes

The platform is built on Python Flask with SQLAlchemy and per-market SQLite databases. Listings are sourced nightly via pipeline from Zillow and Realtor.com data feeds. AI scoring and briefs call the Anthropic Claude API. The stack runs on IIS at toughguycomputing.com.

HomeFinder Social is under active development. Features and UI are subject to change. Feedback of any kind is welcome.

---

*Phil Larson*
