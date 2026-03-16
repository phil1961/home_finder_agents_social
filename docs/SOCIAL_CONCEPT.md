# HomeFinder Social — Product Concept

**Version:** 2026.03.14
**Last Updated:** 2026-03-14

---

## Vision

Turn HomeFinder from a solo home-search tool into a **social discovery platform** — where friends, family, neighbors, and agents collaborate to surface great homes, list properties from their own networks, and earn rewards for referrals that lead to real outcomes.

Think **Airbnb meets Reddit karma, but for real estate.** Nobody "sells" anything through HomeFinder — we're a discovery and scoring platform. The social layer makes it viral.

---

## The Problem

Home buyers browse alone. They find a listing, maybe text a screenshot to a friend, and the conversation dies. Agents cold-call leads. Owners pay for ads. Nobody benefits from word-of-mouth — the most powerful force in real estate.

---

## The Solution: Neighborhood Network

### Core Idea

Any user can **share a listing** with someone they know — friend, family, coworker, neighbor. That share is tracked. If the recipient engages (reacts, signs up, eventually buys), the sharer earns points. Points unlock perks. The viral loop drives growth without ad spend.

Beyond sharing scraped listings, users can **list a friend's or neighbor's home** directly — a "Neighborhood Tip" that appears alongside Zillow and Realtor results. This crowdsourced layer is something no other platform offers.

### What Makes It Different

| Traditional Platform | HomeFinder Social |
|---------------------|-------------------|
| You search alone | Friends share listings with you |
| Agent cold-calls you | Your neighbor recommends their agent |
| Listings feel anonymous | "Sarah shared this — she lives nearby" |
| No reward for word-of-mouth | Points for every referral in the chain |
| One listing source | Zillow + Realtor + **friend-listed** homes |

---

## User Roles in the Social Layer

| Role | Social Capabilities |
|------|-------------------|
| **Guest** | Browse shared listings via link, react to shares, share via link (no email) |
| **User/Client** | Full sharing, collections, reactions, referrals, "Add a Home," points |
| **Principal** | Same as client; agent can see their social activity |
| **Agent** | Share on behalf of clients, branded share pages, curated collections, social analytics, client social activity feed, referral network tracking |
| **Owner** | Site-wide social analytics (most shared, viral chains, conversion metrics), moderation of friend-listed homes |
| **Master** | Cross-site social analytics, reward tier configuration, fraud review |

---

## User Journeys

### Journey 1: The Helpful Friend

1. **Maria** is browsing HomeFinder Charleston and spots a house perfect for her coworker Dave
2. She clicks **Share** on the listing card → enters Dave's email and a note: *"This backyard is exactly what you described!"*
3. Dave gets a polished email with a listing card and Maria's note
4. He clicks through to the **share landing page** — sees the full listing detail, photos, deal score
5. Dave reacts with "Love It" — Maria gets notified instantly
6. Dave creates a free account → Maria earns **10 referral points**
7. Dave eventually tours and buys → Maria earns **100 bonus points** → unlocks VIP badge

### Journey 2: The Neighborhood Tip

1. **Tom** knows his neighbor is about to sell their home (FSBO, not on MLS yet)
2. Tom clicks **"Add a Home"** → enters the address, uploads phone photos, checks the permission box
3. The listing appears with a **"Neighborhood Tip"** badge alongside scraped listings
4. **Agent Rachel** spots it → contacts the seller → closes the deal
5. Rachel reports the sale → Tom earns **50 points** → Rachel's referral chain is credited

### Journey 3: The Agent's Curated Collection

1. **Agent Rachel** creates a **collection**: *"Best Homes Under $400K in Mt. Pleasant"*
2. She adds 8 curated listings with personal notes on each one
3. She shares the collection with her 5 active principal clients
4. Clients browse, react, share individual listings with their own friends
5. Rachel tracks everything in her **Social Analytics** dashboard
6. Two new users sign up through the chain → attributed to Rachel

### Journey 4: The Viral Share Chain

1. **User A** shares listing → **User B** (friend)
2. **B** loves it, re-shares to **User C** (their sister)
3. **C** signs up, shares to **User D** (her husband)
4. **D** contacts the listing agent
5. Every link in the chain earns points: A gets 10, B gets 10, C gets 5

---

## Reward System: Points Economy

### Why Points, Not Cash

Cash rewards create legal and tax complexity. Points are simpler, flexible, and encourage engagement without making HomeFinder look like a referral fee scheme (which would require brokerage licensing in most states).

### Earning Points

| Action | Points |
|--------|--------|
| Share a listing | 1 |
| Someone views your share | 1 |
| Someone reacts to your share | 3 |
| Your share leads to a new signup | 10 |
| Create a collection | 2 |
| Your collection gets shared by others | 5 |
| List a friend's home ("Add a Home") | 5 |
| Friend-listed home gets agent inquiry | 15 |
| Referral chain leads to verified sale | 100 |

### Spending Points — Reward Tiers

| Points | Perk |
|--------|------|
| 10 | Featured listing placement (your shares appear first) |
| 25 | Custom map pin colors for your flagged listings |
| 50 | **"Top Contributor"** badge on your profile |
| 100 | Early access to new markets before public launch |
| 250 | Eligible for **Site Owner** status (pending master approval) |
| 500 | Lifetime VIP — priority support, beta features |

### Anti-Fraud Guardrails

- Cap earnings at 50 points/day per user
- Flag patterns: same IP creating multiple accounts, rapid-fire shares to disposable emails
- Sale verification requires MLS number or screenshot — manual review by owner or master
- Monthly leaderboard resets prevent runaway accumulation
- Points have no cash value — explicitly stated in Terms of Service

---

## Friend-Listed Homes: "Add a Home"

### The Feature

Users can list a home they know about — FSBO, pre-market, neighbor's place. This crowdsourced layer is the key differentiator from Zillow/Realtor.

**Upload Form:**
- Address (geocoded for map placement and area matching)
- At least 1 photo (phone camera upload)
- Permission checkbox: *"I confirm the property owner is aware of and consents to this listing"*
- Relationship: "My home," "Friend's home," "Neighbor's home," "Family member's home"
- Optional: asking price, beds, baths, sqft, year built, description

**How It Appears:**
- Badge: **"Neighborhood Tip"** or **"Friend-Listed"** (visually distinct from Zillow/Realtor badges)
- Attributed: *"Listed by Tom"* (first name only)
- No deal score (insufficient data for 18-factor scoring) — but still appears in searches, map, and collections
- Can be shared, reacted to, and added to collections like any listing

**Moderation:**
- Owner can remove any friend-listed home from their site
- Report button for other users ("Inaccurate," "No permission," "Spam")
- Auto-expire after 90 days unless the lister renews
- Master can review and remove across all sites

---

## Monetization Strategy

### Revenue Streams

HomeFinder is **not a broker**. We never touch transactions. Revenue comes from platform hosting and usage fees.

| Stream | Model | Price Point |
|--------|-------|-------------|
| **Owner hosting fee** | Flat monthly per market | $5–15/mo per zip code |
| **Scraping usage** | Pay-as-you-go after free tier | 500 free API calls/day, then $0.002/call |
| **Agent Pro tier** | Optional monthly subscription | $10/mo — unlimited client invites, branded shares, priority support |
| **Featured placement** | Points-based or paid boost | $1/listing/week OR redeem 10 points |

### What We Don't Do

- **No commissions** on sales — ever
- **No lead-selling** to agents
- **No advertising** or sponsored listings (initially)
- **No transaction facilitation** — we don't handle offers, contracts, or escrow

### Unit Economics

| Cost | Estimate |
|------|----------|
| RapidAPI scraping (Zillow + Realtor) | ~$15/mo per active market |
| Claude AI analysis calls | ~$0.015 per deal brief |
| Email delivery (SMTP) | ~$0/mo (existing provider) |
| IIS hosting | Already covered (toughguycomputing.com) |
| **Total cost per market** | **~$15–20/mo** |

**Break-even per market:** One owner paying $5/mo across 4 zip codes = $20/mo. Covered.

---

## Legal Position

### We Are

- A **search and discovery platform** for publicly available real estate data
- A **social sharing tool** that lets users recommend listings to friends
- An **AI-powered scoring engine** that helps users evaluate properties

### We Are Not

- A licensed real estate broker, agent, or referral service
- A transaction facilitator (no offers, contracts, closings)
- A source of legal, financial, or investment advice

### Required Disclaimers

**Footer (every page):**
> HomeFinder is not a licensed real estate broker or agent. Listings are sourced from public data and user submissions. All information should be independently verified. HomeFinder does not facilitate transactions or provide legal, financial, or investment advice.

**"Add a Home" upload form:**
> By submitting this listing, you confirm that the property owner is aware of and consents to this information being shared on HomeFinder. You are responsible for the accuracy of the information provided.

**Terms of Service highlights:**
- Users own their content; we can remove anything that violates terms
- No guarantee of accuracy for scraped or user-submitted data
- Points have no cash value and may be modified or revoked at our discretion

---

## Social Proof & Engagement Mechanics

### On Listing Cards

- **Share count badge:** "3 people shared this listing"
- **"Most Shared This Week"** section on dashboard
- **"Neighborhood Tip"** badge for friend-listed homes

### On Listing Detail Page

- **Reaction summary:** "2 Love It, 1 Great Location"
- **Share chain:** "Shared by Sarah → viewed by 4 people → 2 reactions"
- **Social proof:** "This listing has been added to 3 collections"

### In Navbar / Profile

- **Points balance** visible in navbar
- **"Top Contributor" badge** on user profile
- **Leaderboard** — top referrers per market (monthly reset)

### For Agents

- **Social Activity dashboard** — which clients are sharing, what's getting traction
- **Referral attribution** — "5 users joined through your client network"
- **Collection engagement** — views, shares, reactions on curated collections
- **Branded share pages** — agent's colors, logo, and tagline on shares

---

## Phased Rollout

### Phase 1: Foundation (Current — shipped)
- [x] Share listings via email/link with personal message
- [x] Share landing pages with full listing detail
- [x] Reactions (love, interested, great location, too pricey, not for me)
- [x] Collections (create, curate, share)
- [x] Referral codes and tracking
- [x] Social analytics dashboard for owners/agents
- [x] Share button on every listing card and detail page
- [x] "Social" nav dropdown with all social pages
- [x] Email notifications for shares, reactions, collection shares, referral invitations

### Phase 2: Engagement (next)
- [ ] Points system with earning/spending and balance display
- [ ] "Add a Home" friend-listing feature with photo upload
- [ ] Leaderboards per market (monthly)
- [ ] Weekly digest emails: "Your shares this week"
- [ ] Social proof badges on listing cards (share count, reactions)
- [ ] Re-share from share landing page (viral loop)

### Phase 3: Monetization
- [ ] Stripe integration for owner hosting fees
- [ ] Agent Pro subscription tier
- [ ] Usage-based scraping charges with top-up
- [ ] Featured placement (points or paid)

### Phase 4: Network Effects
- [ ] Multi-level share chain attribution
- [ ] Public collections discoverable via search
- [ ] Agent referral marketplace
- [ ] Mobile-optimized share experience
- [ ] Push notifications for reactions and new shares

---

## Success Metrics

| Metric | 3-Month Target | 6-Month Target |
|--------|---------------|----------------|
| Shares per week | 20 | 50+ |
| Share → signup conversion | 10% | 15% |
| Collections created | 30 | 100+ |
| Referral chain depth (avg) | 1.5 links | 2.5 links |
| Monthly active sharers | 20% of users | 30% of users |
| Friend-listed homes | 10 per market | 50 per market |
| Revenue (owner fees) | $50/mo | $200/mo |

---

## Competitive Position

| Capability | Zillow | Realtor | Redfin | Nextdoor | **HomeFinder Social** |
|-----------|--------|---------|--------|----------|----------------------|
| Listing discovery | Excellent | Excellent | Excellent | None | Good + growing |
| Social sharing | None | None | Minimal | Strong (informal) | **Strong (structured)** |
| AI deal scoring | Zestimate | None | Hot Homes | None | **18-factor + Claude AI** |
| Friend-listed homes | None | None | None | Informal posts | **Yes (with moderation)** |
| Referral rewards | None | None | Redfin Refund | None | **Points system** |
| Agent tools | Premier Agent ($$$) | Connections ($$$) | Partner Agents | None | **Included (free/Pro)** |
| Multi-tenant / white-label | No | No | No | No | **Yes** |

**Our moat:** Nobody combines AI deal scoring + social sharing + friend-listed homes + referral rewards + multi-tenant agent tools. Zillow has the listings. Nextdoor has the community. We bridge both.
