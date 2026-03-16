<!--
  File: docs/MANUAL_TESTING.md
  App Version: 2026.03.14 | File Version: 1.0.0
  Last Modified: 2026-03-15
-->

# Manual Testing Guide — HomeFinder Social

Last updated: 2026-03-15

---

## How to Use This Guide

### Test Accounts

Four test accounts exist per site, all using `philipalarson@gmail.com`:

| Role   | Capabilities |
|--------|-------------|
| master | Full platform control, site registry, masquerade as anyone |
| owner  | Site admin, metrics, billing, agents, prompts, user management |
| agent  | Client roster, branding, friend listing review, direct listing creation |
| user   | Browse, flag, score, share, tour planning |

Guest access (no login) is also available for most browsing features.

### Role Hierarchy

`master` > `owner` > `agent` > `client`/`principal` > guest

### Browser Setup

- Test in Chrome (desktop) and a mobile viewport (Chrome DevTools device mode or real phone).
- Clear cookies between role switches or use incognito windows.
- For PWA tests, use HTTPS or localhost.

### URL Pattern

All site-specific URLs follow: `/home_finder_agents_social/site/<site_key>/...`

The welcome page is at: `/home_finder_agents_social/welcome`

---

## Page: Welcome

**URL:** `/welcome`
**Roles:** All (guest, authenticated)
**Prerequisites:** At least one active site in the registry with listings

### Test: Market Picker Loads

- [ ] Navigate to `/welcome`
- [ ] Verify site cards appear for all active markets
- [ ] Each card shows the site display name and listing count
- [ ] Cards are clickable and link to the correct `/site/<key>/` URL

**Expected:** All active sites render as cards with listing counts. Inactive sites are not shown.

### Test: Navigation Links

- [ ] Click the "Choose a Market" nav link (if present)
- [ ] Verify the page scrolls smoothly to the `#markets` section
- [ ] Click the "Skip to markets" accessibility link (if visible on focus)
- [ ] Verify it jumps to the markets section

**Expected:** Smooth scroll or jump to the market picker section.

### Test: Power Cards

- [ ] Locate the power/feature cards on the welcome page
- [ ] Click "Learn more" on each card
- [ ] Verify expanded details appear with additional information

**Expected:** Each card expands to show more detail; clicking again collapses it.

### Test: Role Pills

- [ ] Verify role-specific badges or pills display correctly on the welcome page
- [ ] Check that they describe the user/agent/owner roles accurately

**Expected:** Role pills render with correct text and styling.

### Test: Authenticated User Redirect

- [ ] Log in as any user who has a site context
- [ ] Navigate to `/welcome` (without `?chooser=1`)
- [ ] Verify automatic redirect to the dashboard

**Expected:** Authenticated users with site context are redirected to their dashboard.

### Test: Force Chooser

- [ ] As an authenticated user, navigate to `/welcome?chooser=1`
- [ ] Verify the market picker is shown (no redirect)

**Expected:** The `?chooser=1` parameter forces the chooser even for logged-in users.

### Test: PWA Install Prompt (Mobile)

- [ ] Open the welcome page on a mobile device or mobile viewport
- [ ] Check for an "Add to Home Screen" or install prompt
- [ ] Verify the service worker registers (`/static/sw.js`)

**Expected:** On supported browsers, a PWA install prompt appears or can be triggered from the browser menu.

---

## Page: Registration

**URL:** `/auth/register`
**Roles:** Unauthenticated only
**Prerequisites:** Mail server configured for verification emails

### Test: Standard Registration

- [ ] Navigate to `/auth/register`
- [ ] Fill in username, email, and password
- [ ] Submit the form
- [ ] Check email for the verification link

**Expected:** Account is created. A flash message says to check email. User cannot log in until verified.

### Test: Duplicate Email Rejected

- [ ] Attempt to register with an email already in use
- [ ] Submit the form

**Expected:** Flash error indicating the email is already registered.

### Test: Duplicate Username Rejected

- [ ] Attempt to register with a username already in use

**Expected:** Flash error indicating the username is taken.

### Test: Referral Code Carried Through Registration

- [ ] Visit a referral link `/social/r/<code>` first
- [ ] Then navigate to `/auth/register` and complete registration
- [ ] Verify the referral is attributed (check Referral dashboard of the referrer)

**Expected:** The referral code stored in the session is closed on registration, awarding points to the referrer.

### Test: Agent Signup

- [ ] Navigate to `/auth/agent-signup`
- [ ] Fill in agent details (full name, phone, brokerage, license number)
- [ ] Submit the form
- [ ] Verify the agent profile is created with status "pending"
- [ ] Verify the user role is set to "agent" (or remains user until approved, depending on implementation)

**Expected:** Agent profile created. Agent cannot access agent features until owner approves.

---

## Page: Email Verification

**URL:** `/auth/verify/<token>`
**Roles:** Unauthenticated
**Prerequisites:** Registration completed, verification email received

### Test: Valid Verification Token

- [ ] Click the verification link from the registration email
- [ ] Verify the account is marked as verified
- [ ] Verify redirect to login page with success message

**Expected:** Account verified, user can now log in.

### Test: Expired or Invalid Token

- [ ] Modify the token in the URL to make it invalid
- [ ] Navigate to the modified URL

**Expected:** Error flash message indicating invalid or expired token.

### Test: Resend Verification

- [ ] Navigate to `/auth/resend-verification`
- [ ] Enter the registered email address
- [ ] Submit the form
- [ ] Check for a new verification email

**Expected:** A new verification email is sent with a fresh token.

---

## Page: Login

**URL:** `/auth/login`
**Roles:** Unauthenticated
**Prerequisites:** A verified user account

### Test: Successful Login

- [ ] Navigate to `/auth/login`
- [ ] Enter correct username/email and password
- [ ] Submit the form

**Expected:** Redirect to the dashboard. Username appears in the nav bar.

### Test: Wrong Password

- [ ] Enter a valid username but incorrect password
- [ ] Submit the form

**Expected:** Flash error "Invalid credentials" or similar. No login.

### Test: Unverified User Blocked

- [ ] Register a new account but do not verify the email
- [ ] Attempt to log in with correct credentials

**Expected:** Flash error indicating the account is not yet verified, with a link to resend verification.

### Test: Suspended User Blocked

- [ ] As an owner, suspend a user account from `/admin/users`
- [ ] Attempt to log in as that user

**Expected:** Flash error showing the account is suspended with the suspension reason.

### Test: Password Reset Flow

- [ ] Navigate to `/auth/forgot-password`
- [ ] Enter a registered email address
- [ ] Submit the form
- [ ] Check email for the reset link
- [ ] Click the link (`/auth/reset-password/<token>`)
- [ ] Enter a new password and submit
- [ ] Log in with the new password

**Expected:** Password is changed. Old password no longer works. New password logs in successfully.

---

## Page: Dashboard

**URL:** `/` (within site context: `/site/<key>/`)
**Roles:** All (guest, user, agent, owner, master)
**Prerequisites:** Listings exist in the site database with deal scores

### Test: Listings Load with Scores

- [ ] Navigate to the dashboard
- [ ] Verify listing cards appear with photos, address, price, and deal score
- [ ] Verify feature tags (garage, porch, patio, etc.) appear on cards
- [ ] Verify scores use user-specific composite weights

**Expected:** Up to 100 listings displayed, sorted by score descending by default.

### Test: Filter Bar — Area

- [ ] Select a specific area from the Area dropdown
- [ ] Verify only listings in that area's zip codes appear
- [ ] Select "All" to reset

**Expected:** Listings filtered to the selected area.

### Test: Filter Bar — Sort

- [ ] Change sort to "Price (Low)" — verify ascending price order
- [ ] Change sort to "Price (High)" — verify descending price order
- [ ] Change sort to "Newest" — verify newest first
- [ ] Change sort to "Yard Size" — verify largest lots first
- [ ] Change sort to "Score" — verify highest score first

**Expected:** Listing order changes according to selected sort.

### Test: Filter Bar — Flag Filter

- [ ] Select "Favorites" — verify only favorited listings appear
- [ ] Select "Maybe" — verify only maybe-flagged listings appear
- [ ] Select "Hidden" — verify only hidden listings appear
- [ ] Select "All" — verify hidden listings are excluded but favorites and maybes are included

**Expected:** Flag filter works for both authenticated users and guests.

### Test: Filter Bar — Source

- [ ] Select "Zillow" — verify only Zillow-sourced listings appear
- [ ] Select "Realtor" — verify only Realtor-sourced listings appear
- [ ] Select "All" — verify all sources shown

**Expected:** Listings filtered by data source.

### Test: Filter Bar — Min Score

- [ ] Set minimum score to 60
- [ ] Verify all displayed listings have a score >= 60

**Expected:** Only listings meeting the score threshold appear.

### Test: Filter Bar — Max Distance (POI selected)

- [ ] Go to Preferences and select a proximity POI landmark
- [ ] Return to the dashboard
- [ ] Set a max distance value (e.g., 5 miles)
- [ ] Verify only listings within that distance of the POI appear
- [ ] Verify distance badges appear on listing cards (color-coded by distance)

**Expected:** Distance filter only appears when a POI is selected. Listings beyond the distance are hidden.

### Test: Distance Badges

- [ ] With a POI selected, verify distance badges appear on listing cards
- [ ] Check color coding: green for close, yellow for medium, red for far (or similar)

**Expected:** Badges show distance in miles with appropriate color coding.

### Test: "Most Shared This Week" Section

- [ ] Verify the horizontal scroll section appears at the top of the dashboard
- [ ] Check that up to 5 most-shared listings from the last 7 days are shown
- [ ] Verify each card shows the share count

**Expected:** Most shared listings appear in a scrollable horizontal strip.

### Test: "Neighborhood Tips" Section

- [ ] Verify active friend listings appear in a section on the dashboard
- [ ] Check that they are filtered to the current site's zip codes

**Expected:** Up to 5 active friend-listed homes displayed with Neighborhood Tip badges.

### Test: Share Button

- [ ] Click the share button on a listing card
- [ ] Verify the share modal opens with fields for recipient email, name, relationship, and message
- [ ] Fill in a recipient email and submit
- [ ] Verify a success flash message appears
- [ ] Verify the "Copy Link" button generates a shareable URL

**Expected:** Share creates a SocialShare record, sends an email notification, and awards points.

### Test: Flag Buttons

- [ ] Click the star (favorite) button on a listing
- [ ] Verify the listing is flagged and the button state updates
- [ ] Click the "maybe" button — verify flag changes
- [ ] Click the "hide" button — verify listing disappears from default view
- [ ] Click a flag button again on an already-flagged listing — verify flag is removed

**Expected:** Flags toggle correctly. Hidden listings disappear. Re-clicking removes the flag.

### Test: Flag Milestones (Authenticated)

- [ ] Favorite your first listing — verify "Great first pick!" message
- [ ] Favorite your 3rd listing — verify AI Portfolio Analysis nudge
- [ ] Favorite your 5th listing — verify tour planning nudge

**Expected:** Progressive nudge messages appear at milestone counts.

### Test: Guest Flag Milestones

- [ ] As a guest, favorite 1 listing — verify "Nice pick!" message
- [ ] Favorite a 3rd listing — verify nudge to create an account

**Expected:** Guest-specific milestone messages appear.

### Test: "Since Your Last Visit" Banner

- [ ] Log in as an authenticated user who has a previous login timestamp
- [ ] Verify the banner shows new listing count, price drops, total scored, and top score

**Expected:** Stats banner appears with accurate counts since last login.

### Test: Street Watch Widget

- [ ] If user has active street watches, verify they appear in the dashboard sidebar/widget
- [ ] Verify watch entries show street name and zip code

**Expected:** Active watches displayed in the widget.

### Test: Portfolio AI Analysis

- [ ] Filter by "Favorites" flag
- [ ] Click the "AI Portfolio Analysis" button
- [ ] Verify a loading indicator appears
- [ ] Verify the analysis result renders with ranking, patterns, and strategy

**Expected:** AI analysis runs and displays cached or fresh results.

### Test: Welcome Modal (Guest First Visit)

- [ ] Clear the `hf_welcomed` cookie
- [ ] Navigate to the dashboard as a guest
- [ ] Verify the welcome modal appears explaining guest features
- [ ] Click "Start Browsing" — verify modal dismisses and cookie is set
- [ ] Refresh the page — verify modal does not reappear

**Expected:** Modal shows on first visit only.

---

## Page: Listing Detail

**URL:** `/listing/<id>`
**Roles:** All
**Prerequisites:** At least one listing exists with a deal score

### Test: Photo Gallery

- [ ] Navigate to a listing detail page
- [ ] Verify photos display (gallery or carousel)
- [ ] If multiple photos exist, verify navigation between them

**Expected:** Photos render correctly. If no photos, a placeholder or empty state shows.

### Test: Stats and Feature Tags

- [ ] Verify price, beds, baths, sqft, lot size, year built display
- [ ] Verify feature tags (garage, porch, patio, pool, single story) are present where applicable

**Expected:** All available data fields render. Missing fields show gracefully (no errors).

### Test: Deal Score Panel

- [ ] Verify the overall deal score displays prominently
- [ ] Verify all 18 sub-score bars render with labels and values
- [ ] Verify scores reflect the current user's preference weights

**Expected:** 18-factor score breakdown with colored bars.

### Test: POI Proximity Bar

- [ ] With a landmark selected in preferences, navigate to a listing detail
- [ ] Verify a distance bar/badge shows the distance in miles to the selected POI

**Expected:** POI proximity displays when a landmark is selected. Hidden when no landmark set.

### Test: Reaction Summary

- [ ] Share a listing, then react to it from the share landing page
- [ ] Navigate to the listing detail
- [ ] Verify the reaction summary shows reaction types and counts

**Expected:** Reaction counts appear when shares with reactions exist.

### Test: Share and Collect Card

- [ ] Verify the "Share" button opens the share modal
- [ ] Verify the "Add to Collection" dropdown lists user's collections
- [ ] Add the listing to a collection — verify success message

**Expected:** Share and collect functionality works from the detail page.

### Test: AI Deal Analysis

- [ ] Click the "AI Deal Analysis" button
- [ ] Verify a loading indicator appears
- [ ] Verify the analysis displays verdict, summary, strengths, concerns, and negotiation tips
- [ ] Refresh the page — verify the cached analysis loads without re-calling the API

**Expected:** Analysis renders with all expected JSON keys. Cached results load instantly on revisit.

### Test: AI Deal Analysis (Guest)

- [ ] As a guest, click the AI analysis button
- [ ] Verify the "Join" modal appears prompting account creation

**Expected:** Guests are prompted to create an account for AI features.

### Test: Detail Map

- [ ] Verify the map renders with the listing marker
- [ ] If landmarks exist, verify landmark stars appear with hover tooltips
- [ ] Click "Map with Landmarks" link — verify it opens Google Maps with landmarks
- [ ] Click "Directions from [landmark]" — verify it opens Google Maps directions

**Expected:** Map with listing pin and landmark stars. External links open correctly.

### Test: Street Watch Card

- [ ] Verify the Street Watch card shows the street name
- [ ] If not already watching, click "Watch this Street"
- [ ] If already watching, verify "Watching" state displays

**Expected:** Street Watch card reflects current watch state.

### Test: Listing Notes (Authenticated)

- [ ] Add a text note to the listing
- [ ] Check the "Visited" box
- [ ] Refresh the page — verify note and checkbox persist

**Expected:** Notes and checkboxes persist across page loads.

### Test: Flag Buttons on Detail

- [ ] Toggle favorite, maybe, hidden flags from the detail page
- [ ] Verify flag state updates and flash messages appear

**Expected:** Flags work identically to the dashboard.

### Test: Lazy Detail Enrichment

- [ ] Navigate to a listing that has `details_fetched=False`
- [ ] Verify the page triggers an API call to fetch details (check server logs)
- [ ] Refresh — verify the enrichment does not fire again

**Expected:** First visit fetches details from the source API. Subsequent visits use cached data.

---

## Page: Map

**URL:** `/map`
**Roles:** All
**Prerequisites:** Listings with latitude/longitude coordinates

### Test: Listings Plotted

- [ ] Navigate to `/map`
- [ ] Verify markers appear for active listings with coordinates
- [ ] Verify marker colors correspond to deal scores (green = high, red = low, or similar)

**Expected:** All geo-coded listings appear on the map with score-based colors.

### Test: Marker Clusters

- [ ] Zoom out on the map
- [ ] Verify nearby markers cluster into numbered group icons
- [ ] Click a cluster to zoom in and reveal individual markers

**Expected:** Clusters form at low zoom levels and expand on click.

### Test: Landmark Stars

- [ ] Verify site landmarks appear as star markers
- [ ] Hover over a landmark star — verify tooltip with name
- [ ] If user landmarks exist, verify they also appear

**Expected:** Landmark stars render with hover tooltips.

### Test: Marker Popup

- [ ] Click a listing marker
- [ ] Verify the popup shows: photo, price, score, and a link to the detail page
- [ ] Click the detail link in the popup

**Expected:** Popup displays listing summary with a working link to detail.

### Test: Filter Controls

- [ ] Use the area filter — verify markers update to show only that area
- [ ] Use the source filter — verify markers update
- [ ] Use the score filter — verify markers update

**Expected:** Map markers respond to filter selections.

---

## Page: Digest

**URL:** `/digest`
**Roles:** All
**Prerequisites:** Listings exist in the database

### Test: Tabular View

- [ ] Navigate to `/digest`
- [ ] Verify listings display in a table with columns: address, price, beds, baths, sqft, score, etc.

**Expected:** Sortable table of all active listings.

### Test: Tab Filters

- [ ] Click "New" tab — verify only listings from the last N days appear
- [ ] Click "Favorites" tab — verify only favorited listings appear
- [ ] Click "Maybe" tab — verify only maybe-flagged listings appear
- [ ] Click "Hidden" tab — verify only hidden listings appear
- [ ] Click "All" tab — verify all non-hidden listings appear

**Expected:** Each tab filters the table appropriately.

### Test: Area Filter

- [ ] Select a specific area — verify table filters to that area
- [ ] Select all areas — verify full list returns

**Expected:** Area filter works in combination with tab filter.

### Test: CSV Export

- [ ] Click the "Export CSV" button/link
- [ ] Verify a file `homefinder_listings.csv` downloads
- [ ] Open the CSV — verify it contains the correct columns and data

**Expected:** CSV download with all displayed listings and their attributes.

---

## Page: Preferences

**URL:** `/preferences`
**Roles:** All (guest prefs stored in session, authenticated prefs stored in DB)
**Prerequisites:** Site has target areas and landmarks configured

### Test: Section 1 — Scoring Preferences

- [ ] Adjust the price range dual slider (min/max price)
- [ ] Change min beds and min baths values
- [ ] Toggle feature checkboxes (must have garage, porch, patio)
- [ ] Adjust each of the 18 importance sliders
- [ ] Select a POI from the dropdown (site landmarks + user landmarks)
- [ ] Click "Save Scoring Preferences"
- [ ] Verify AJAX save (no page reload) with success message
- [ ] Navigate to the dashboard — verify scores reflect new weights

**Expected:** Preferences save via AJAX. Scores on the dashboard update to reflect new weights.

### Test: Section 2 — Target Areas (Master Only Editable)

- [ ] As master, add a new area name with comma-separated zip codes
- [ ] Click "Save Target Areas"
- [ ] Verify AJAX save with success message
- [ ] Check that the new area appears in dashboard area filter
- [ ] As a non-master user, verify the target areas section is read-only

**Expected:** Master can add/edit/remove target areas. Non-master users see but cannot edit.

### Test: Section 2 — Avoid Areas

- [ ] As master, enter area names to avoid (comma-separated)
- [ ] Save and verify they persist on page reload

**Expected:** Avoided areas are stored and affect listing display.

### Test: Section 3 — Site Landmarks (Owner/Master Only)

- [ ] As owner/master, search for a location via the Nominatim search box
- [ ] Select a result — verify coordinates populate
- [ ] Use the common landmarks dropdown to pick a preset
- [ ] Click the map to place a pin — verify coordinates update
- [ ] Click "Add Landmark" — verify it appears in the existing landmarks list via AJAX
- [ ] Delete a landmark — verify it is removed via AJAX
- [ ] Verify the map is bounded to the site's configured area

**Expected:** Landmarks are managed via AJAX without page reload. Map stays within site bounds.

### Test: My Landmarks (All Authenticated Users)

- [ ] Expand the "My Landmarks" section
- [ ] Search for a location or use the mini map picker
- [ ] Click the expand button on the mini map to enlarge it
- [ ] Add a personal landmark — verify AJAX success and it appears in the list
- [ ] Attempt to add a 4th landmark — verify error message about 3 max limit
- [ ] Delete a personal landmark — verify removal
- [ ] Verify the POI dropdown in Section 1 updates in real time to include user landmarks

**Expected:** Personal landmarks limited to 3. AJAX add/delete. POI dropdown reflects changes immediately.

### Test: AI Preferences Coach

- [ ] Click the "AI Preferences Coach" button
- [ ] Verify loading indicator
- [ ] Verify analysis renders with headline, strengths, blind spots, tweaks, local insight, and bottom line

**Expected:** AI coaching analysis of the user's preference settings.

### Test: Guest Preferences

- [ ] As a guest (not logged in), adjust scoring preferences
- [ ] Save — verify stored in session
- [ ] Navigate to dashboard — verify scores use the guest preferences
- [ ] Close the browser — verify preferences are lost (session-based)

**Expected:** Guest prefs work for the session but are not persisted permanently.

---

## Page: Shared With Me

**URL:** `/social/shared-with-me`
**Roles:** Authenticated users
**Prerequisites:** Someone has shared a listing with the current user's email

### Test: View Received Shares

- [ ] Share a listing to a test user's email
- [ ] Log in as that user and navigate to `/social/shared-with-me`
- [ ] Verify the share appears with sharer name, listing info, and timestamp
- [ ] Verify status indicators (viewed, replied)

**Expected:** All shares sent to the user's email are listed in reverse chronological order.

---

## Page: My Shares

**URL:** `/social/my-shares`
**Roles:** Authenticated users
**Prerequisites:** The current user has shared at least one listing

### Test: View Sent Shares

- [ ] Navigate to `/social/my-shares`
- [ ] Verify all shares sent by the user are listed
- [ ] Check status tracking: sent, viewed, replied
- [ ] Verify recipient information displays

**Expected:** Complete list of outgoing shares with status tracking.

---

## Page: Collections

**URL:** `/social/collections`
**Roles:** Authenticated users
**Prerequisites:** None

### Test: Create a Collection

- [ ] Navigate to `/social/collections`
- [ ] Click "Create Collection"
- [ ] Enter a title and description
- [ ] Toggle the "Public" checkbox
- [ ] Submit — verify redirect to the new collection detail page
- [ ] Verify points awarded (check Points page)

**Expected:** Collection created with title, description, and public/private setting. 2 points awarded.

### Test: Add Listings to Collection

- [ ] From a listing detail or dashboard, use "Add to Collection"
- [ ] Select the collection and add
- [ ] Navigate to the collection detail — verify the listing appears

**Expected:** Listing added to collection with optional note.

### Test: Remove Listing from Collection

- [ ] On the collection detail page, click remove on a listing
- [ ] Verify it is removed from the collection

**Expected:** Listing removed. Flash confirmation message.

### Test: Share a Collection

- [ ] On the collection detail page, enter a recipient email and optional message
- [ ] Click "Share Collection"
- [ ] Verify success message and email sent

**Expected:** Collection share creates a SocialShare record with type "collection" and sends email.

### Test: Public Collection View

- [ ] Copy the public collection URL (`/social/c/<token>`)
- [ ] Open it in an incognito window (not logged in)
- [ ] Verify the collection and its listings are visible
- [ ] Verify the view count increments

**Expected:** Public collections are viewable by anyone with the link.

---

## Page: Points

**URL:** `/social/points`
**Roles:** Authenticated users
**Prerequisites:** Some point-earning actions completed

### Test: View Points Balance

- [ ] Navigate to `/social/points`
- [ ] Verify current balance and lifetime total display
- [ ] Verify the points history table shows recent earning events with icons
- [ ] Check that each log entry shows: action type, points earned, timestamp

**Expected:** Accurate points balance and chronological history (last 50 entries).

---

## Page: Leaderboard

**URL:** `/social/leaderboard`
**Roles:** Authenticated users
**Prerequisites:** Multiple users have shares/referrals in the current month

### Test: View Leaderboards

- [ ] Navigate to `/social/leaderboard`
- [ ] Verify "Top Sharers This Month" table with user names and share counts
- [ ] Verify "Top Referrers This Month" table with user names and referral counts
- [ ] Verify the month start date displays correctly

**Expected:** Top 10 sharers and referrers for the current calendar month.

---

## Page: Referral

**URL:** `/social/referral`
**Roles:** Authenticated users
**Prerequisites:** None

### Test: View Referral Dashboard

- [ ] Navigate to `/social/referral`
- [ ] Verify your referral code displays
- [ ] Verify any previous referral invitations are listed with status

**Expected:** Referral code shown with copy ability. History of sent invitations.

### Test: Send Referral Invitation

- [ ] Enter an email address and click "Invite"
- [ ] Verify success flash and the invitation appears in the list
- [ ] Check that an email was sent to the recipient

**Expected:** Referral record created and email sent.

### Test: Duplicate Referral Rejected

- [ ] Attempt to invite the same email again

**Expected:** Flash message "You've already invited this person."

### Test: Referral Landing Page

- [ ] Open the referral link (`/social/r/<code>`) in an incognito window
- [ ] Verify the landing page shows the referrer's info
- [ ] Verify the referral code is stored in the session
- [ ] Complete registration — verify the referral is attributed

**Expected:** Referral code persists in session through registration. Referral closed on signup.

---

## Page: Add a Home (Neighborhood Tip)

**URL:** `/social/add-home`
**Roles:** Authenticated users
**Prerequisites:** None

### Test: Submit a Friend Listing

- [ ] Navigate to `/social/add-home`
- [ ] Fill in address, city, zip code, price, beds, baths, sqft
- [ ] Add a description
- [ ] Select relationship (friend, neighbor, family)
- [ ] Check the "I have permission" checkbox
- [ ] Upload 1-5 photos (jpg, png, webp)
- [ ] Submit the form
- [ ] Verify redirect to Neighborhood Tips page
- [ ] Verify 5 points awarded

**Expected:** Friend listing created with status "active" and 90-day expiry. Photos saved to `/static/uploads/`.

### Test: Permission Checkbox Required

- [ ] Fill in all fields but leave the permission checkbox unchecked
- [ ] Submit the form

**Expected:** Flash warning requiring permission confirmation. Form not submitted.

### Test: Missing Required Fields

- [ ] Submit with address or zip code empty

**Expected:** Flash warning about required fields.

---

## Page: Friend Listings (Neighborhood Tips)

**URL:** `/social/friend-listings`
**Roles:** All (guests and authenticated)
**Prerequisites:** At least one active friend listing in the site's zip codes

### Test: Browse Friend Listings

- [ ] Navigate to `/social/friend-listings`
- [ ] Verify active friend listings display with address, price, description
- [ ] Verify Neighborhood Tip badges appear
- [ ] Verify only listings matching the current site's zip codes are shown

**Expected:** Active community-submitted listings displayed in reverse chronological order.

---

## Page: Share Landing

**URL:** `/social/s/<token>`
**Roles:** Anyone (no login required)
**Prerequisites:** A share has been created

### Test: View Shared Listing

- [ ] Open a share link in an incognito window
- [ ] Verify the shared listing displays with photo, price, address
- [ ] Verify the sharer's name and message appear
- [ ] Verify the share is marked as viewed (check My Shares page)

**Expected:** Landing page shows the shared listing with the sharer's context.

### Test: React to a Share

- [ ] On the share landing page, select a reaction type (love, interested, not_for_me, etc.)
- [ ] Optionally add a comment
- [ ] Submit the reaction
- [ ] Verify "Thanks for your feedback!" message
- [ ] Verify the sharer receives a reaction notification email
- [ ] Verify the share status changes to "replied"

**Expected:** Reaction recorded. Points awarded to sharer (3 points). Email sent.

### Test: Update Existing Reaction

- [ ] React a second time from the same email
- [ ] Verify the reaction is updated (not duplicated)

**Expected:** Existing reaction updated rather than creating a new one.

---

## Page: Social Analytics

**URL:** `/social/analytics`
**Roles:** Owner, Master
**Prerequisites:** Social activity exists (shares, reactions, collections, referrals)

### Test: View Analytics KPIs

- [ ] Log in as owner and navigate to `/social/analytics`
- [ ] Verify KPI cards: total shares, total views, total reactions, total collections, total referrals

**Expected:** Accurate aggregate counts displayed.

### Test: Most Shared Listings

- [ ] Verify the "Most Shared" table shows up to 10 listings with share counts

**Expected:** Listings ranked by share count, descending.

### Test: Recent Shares

- [ ] Verify the "Recent Shares" section shows the last 20 shares with details

**Expected:** Chronological list of recent shares.

### Test: Send Digest

- [ ] Click the "Send Social Digest" button
- [ ] Verify success message with count of recipients
- [ ] Check email inboxes for digest messages

**Expected:** Digest emails sent to eligible users.

### Test: Access Denied for Non-Admin

- [ ] As a regular user, attempt to navigate to `/social/analytics`

**Expected:** 403 Forbidden response.

---

## Page: Tour / Itinerary

**URL:** `/itinerary`
**Roles:** Authenticated users
**Prerequisites:** At least one listing flagged as favorite

### Test: View Tour Page

- [ ] Flag several listings as favorites
- [ ] Navigate to `/itinerary`
- [ ] Verify favorited listings appear on a map with markers
- [ ] Verify the listing summary cards show beside the map

**Expected:** All favorited listings plotted on the tour map.

### Test: Listing Notes and Visit Status

- [ ] Add a note to a listing from the tour page or detail page
- [ ] Check the "Visited" checkbox
- [ ] Check the "Scheduled Visit" checkbox
- [ ] Check the "Made Offer" checkbox
- [ ] Refresh — verify checkboxes and notes persist

**Expected:** Notes and visit status checkboxes persist and display correctly.

### Test: Contact Agent Modal

- [ ] As a client with an assigned agent, click "Contact Agent" in the nav
- [ ] Verify the modal shows the agent's name, phone, brokerage
- [ ] Enter a message and submit
- [ ] Verify success message and email sent to the agent

**Expected:** Message sent to the assigned agent via email.

---

## Page: Street Watch

**URL:** `/watch`
**Roles:** All (guest needs email, authenticated auto-linked)
**Prerequisites:** None

### Test: Create a Street Watch

- [ ] From a listing detail page, click "Watch this Street"
- [ ] If guest, enter an email address
- [ ] Verify the watch is created and confirmation appears

**Expected:** StreetWatch record created. User will receive email alerts for new listings on that street.

### Test: View Active Watches

- [ ] Navigate to `/watch`
- [ ] Verify all active watches display with street name, zip code, and creation date

**Expected:** List of active street watches.

### Test: Remove a Watch

- [ ] Click "Remove" on an active watch
- [ ] Verify it is deactivated

**Expected:** Watch marked as inactive.

### Test: Quick Watch from Dashboard

- [ ] Use the quick watch form on the dashboard widget

**Expected:** Watch created without leaving the dashboard.

### Test: Unsubscribe

- [ ] Click the unsubscribe link from a street watch alert email (`/watch/unsubscribe/<token>`)
- [ ] Verify the watch is deactivated

**Expected:** Watch deactivated. Confirmation message displayed.

---

## Page: Agent Dashboard

**URL:** `/agent/dashboard`
**Roles:** Agent
**Prerequisites:** Agent profile approved by owner

### Test: View Client List

- [ ] Log in as an approved agent
- [ ] Navigate to `/agent/dashboard`
- [ ] Verify client list displays with usernames, emails, favorite counts
- [ ] Verify agent notes and checkboxes per client (pre-approved, signed agreement, etc.)

**Expected:** All clients assigned to the agent appear with summary info.

### Test: Create a Client Account

- [ ] Click "Add Client" or equivalent button
- [ ] Enter client name and email
- [ ] Optionally add an intro message
- [ ] Submit
- [ ] Verify the client account is created, pre-verified, and linked to the agent
- [ ] Verify a welcome email is sent with temporary credentials

**Expected:** Client account created with auto-generated username and password. Welcome email sent.

### Test: Resend Welcome Email

- [ ] Click "Resend Welcome" for an existing client
- [ ] Verify a new temporary password is generated
- [ ] Verify the email is sent

**Expected:** Password reset and new welcome email sent.

### Test: Agent Client Notes

- [ ] Click into a client's notes
- [ ] Add freeform notes
- [ ] Toggle checkboxes: pre-approved, signed agreement, tour scheduled, offer submitted, active searching
- [ ] Verify AJAX save

**Expected:** Notes and checkboxes save via AJAX without page reload.

### Test: View Client Listing Notes

- [ ] Verify the dashboard shows listing notes made by each client
- [ ] Check that visited/scheduled/offer checkboxes display correctly

**Expected:** Agent can see all client listing notes and visit statuses.

### Test: Pending Friend Listings

- [ ] Have a client submit a Neighborhood Tip via `/social/add-home`
- [ ] On the agent dashboard, verify it appears in the "Pending Friend Listings" section

**Expected:** Pending friend listings from the agent's clients are displayed.

---

## Page: Agent Add Listing

**URL:** `/agent/add-listing`
**Roles:** Agent
**Prerequisites:** Approved agent profile

### Test: Create a Direct Listing

- [ ] Navigate to `/agent/add-listing`
- [ ] Fill in address, zip code, city, price, beds, baths, sqft
- [ ] Add lot size, year built, lat/lng coordinates
- [ ] Toggle feature checkboxes
- [ ] Upload up to 5 photos
- [ ] Enter HOA and tax amounts
- [ ] Submit
- [ ] Verify redirect to the new listing detail page
- [ ] Verify the listing has source="agent" and a deal score

**Expected:** Listing created with source "agent", auto-scored, and immediately visible.

### Test: Missing Required Fields

- [ ] Submit without address or zip code

**Expected:** Flash warning about required fields.

---

## Page: Agent Review Friend Listing

**URL:** `/agent/friend-listing/<id>/review`
**Roles:** Agent (for own clients), Owner
**Prerequisites:** A pending friend listing from the agent's client

### Test: Review and Edit

- [ ] Navigate to the review page for a pending friend listing
- [ ] Verify submitter info and original listing data display
- [ ] Edit the address, price, or other fields
- [ ] Submit edits — verify changes are saved
- [ ] Verify "Listing details updated" flash

**Expected:** Agent can review and edit friend listing details before approval.

### Test: Approve a Friend Listing

- [ ] On the review page, click "Approve"
- [ ] Optionally fill in enrichment fields (lot size, year built, coordinates, features)
- [ ] Submit approval
- [ ] Verify a real Listing record is created with source="community"
- [ ] Verify the listing has a deal score
- [ ] Verify the FriendListing status is set to "approved"
- [ ] Verify points awarded to the agent

**Expected:** Friend listing converted to a real listing, scored, and visible in the main feed.

### Test: Reject a Friend Listing

- [ ] Click "Reject" and optionally enter a reason
- [ ] Submit
- [ ] Verify the FriendListing status is set to "rejected"

**Expected:** Listing rejected with optional reason. Does not appear in the main feed.

### Test: Access Control

- [ ] As an agent, try to review a friend listing from a different agent's client

**Expected:** Flash error "You can only review listings from your own clients."

---

## Page: Agent Client Preferences

**URL:** `/agent/clients/<id>/prefs`
**Roles:** Agent
**Prerequisites:** An assigned client

### Test: View and Set Client Preferences

- [ ] Navigate to client preferences page
- [ ] Adjust scoring weights, price range, beds, baths, features
- [ ] Save
- [ ] Verify success message
- [ ] Log in as the client — verify preferences reflect the agent's changes

**Expected:** Agent can set scoring preferences on behalf of their client.

---

## Page: Agent Branding

**URL:** (form on Agent Dashboard, POST to `/agent/branding`)
**Roles:** Agent
**Prerequisites:** Approved agent profile

### Test: Update Branding

- [ ] Set a brand color (hex code, e.g., `#2563eb`)
- [ ] Enter a brand icon (emoji)
- [ ] Enter a tagline
- [ ] Select a tagline style (plain, italic, bold, caps, badge, elegant)
- [ ] Save
- [ ] Verify the navbar updates with the agent's branding when viewing as the agent or their clients
- [ ] Verify the brand icon renders as an emoji in the navbar

**Expected:** Branding persists and displays in the navbar for the agent and all their clients.

### Test: Invalid Color Rejected

- [ ] Enter a non-hex color value
- [ ] Save

**Expected:** Falls back to default color `#2563eb`.

---

## Page: Agent Prompts

**URL:** `/agent/prompts`
**Roles:** Agent (with admin flag)
**Prerequisites:** Approved agent profile

### Test: Override Prompts

- [ ] Navigate to `/agent/prompts`
- [ ] Verify default prompts display for deal, portfolio, and preferences types
- [ ] Enter a custom prompt override for one type
- [ ] Save — verify success message
- [ ] Clear the override — save — verify it reverts to the global/default prompt

**Expected:** Agent-level overrides take precedence over global defaults. Empty override reverts to default.

---

## Page: Admin Agents

**URL:** `/admin/agents`
**Roles:** Owner, Master
**Prerequisites:** At least one agent signup exists

### Test: View Agent List

- [ ] Navigate to `/admin/agents`
- [ ] Verify agents are listed with name, status (pending/approved/suspended), email, brokerage, license

**Expected:** All agent profiles displayed sorted by status then date.

### Test: Approve an Agent

- [ ] Click "Approve" on a pending agent
- [ ] Verify status changes to "approved"
- [ ] Verify the agent can now log in and access agent features

**Expected:** Agent status updated to approved.

### Test: Suspend an Agent

- [ ] Click "Suspend" on an approved agent
- [ ] Verify status changes to "suspended"

**Expected:** Agent suspended. They can no longer access agent features.

### Test: Reactivate an Agent

- [ ] Click "Reactivate" on a suspended agent

**Expected:** Agent status returns to "approved."

### Test: Owner Notes for Agent

- [ ] Add freeform notes and toggle checkboxes (contract signed, background checked, MLS verified)
- [ ] Verify AJAX save

**Expected:** Notes persist via AJAX.

---

## Page: Admin Users

**URL:** `/admin/users`
**Roles:** Owner, Master
**Prerequisites:** Multiple user accounts exist

### Test: View User List

- [ ] Navigate to `/admin/users`
- [ ] Verify all users are listed with username, email, role, verified status, suspended status

**Expected:** Complete user list in reverse chronological order.

### Test: Suspend a User

- [ ] Click "Suspend" on a user
- [ ] Enter a suspension reason
- [ ] Verify the user is marked suspended
- [ ] Attempt to log in as that user — verify blocked with reason

**Expected:** User suspended with reason. Login blocked.

### Test: Reactivate a User

- [ ] Click "Reactivate" on a suspended user
- [ ] Verify they can log in again

**Expected:** Suspension lifted. Login restored.

### Test: Delete a User

- [ ] Click "Delete" on a non-owner, non-master user
- [ ] Verify the account is soft-deleted (username/email prefixed, password cleared)

**Expected:** Account permanently disabled but record preserved.

### Test: Protected Roles

- [ ] Attempt to delete an owner or master account

**Expected:** Flash error "Cannot delete owner or master accounts."

### Test: Cannot Modify Self

- [ ] As an owner, try to suspend your own account

**Expected:** Flash warning "You cannot modify your own account here."

### Test: Owner Cannot Modify Master

- [ ] As an owner (not master), try to modify a master account

**Expected:** Flash error "Cannot modify master accounts."

---

## Page: Admin Metrics

**URL:** `/admin/metrics`
**Roles:** Owner, Master
**Prerequisites:** API calls have been logged

### Test: View Metrics

- [ ] Navigate to `/admin/metrics`
- [ ] Verify summary cards: AI calls, fetch calls, all-time cost, 30-day cost
- [ ] Verify per-user breakdown table with call type columns
- [ ] Verify recent activity log (last 50 calls) with timestamps, users, types, results

**Expected:** Comprehensive API usage and cost metrics.

### Test: Fetch Now

- [ ] Click "Fetch Now" button
- [ ] Verify loading indicator and log output streams in
- [ ] Verify final status (success/warning/error) and listing count

**Expected:** Pipeline runs inline with log capture. Results display in real-time.

### Test: Fetch Now — No Zip Codes

- [ ] Remove all zip codes from a site's target areas
- [ ] Click "Fetch Now"

**Expected:** Error message about no zip codes configured.

### Test: Toggle Scheduler

- [ ] Click the pause/resume scheduler button
- [ ] Verify the scheduler state toggles
- [ ] Verify the button label updates

**Expected:** Scheduler paused or resumed for the current site.

### Test: AJAX Refresh

- [ ] Verify the metrics page auto-refreshes or has a manual refresh button
- [ ] Click refresh — verify updated data loads without page reload

**Expected:** Fresh data loads via AJAX.

---

## Page: Admin Billing

**URL:** `/admin/billing`
**Roles:** Owner, Master
**Prerequisites:** Site exists in registry

### Test: View Billing Info

- [ ] Navigate to `/admin/billing`
- [ ] Verify current plan displays (free/basic/pro/unlimited)
- [ ] Verify usage bars show current month's AI and fetch call usage vs. limits

**Expected:** Billing dashboard with plan info and usage visualization.

### Test: Change Billing Plan

- [ ] Select a different plan (e.g., free to basic)
- [ ] Verify limits update to the plan defaults
- [ ] Save — verify success message

**Expected:** Plan updated. Usage limits change to match the selected tier.

### Test: Custom Limits

- [ ] Override the monthly AI limit and fetch limit with custom values
- [ ] Set a monthly budget
- [ ] Enter a billing email
- [ ] Set cycle start day
- [ ] Save

**Expected:** Custom limits override plan defaults. Budget alerts will trigger at 80%/100%.

### Test: Quota Enforcement

- [ ] Set very low limits (e.g., 1 AI call)
- [ ] Use up the quota
- [ ] Attempt another AI analysis

**Expected:** Quota exceeded message. Feature blocked until next cycle.

---

## Page: Admin Prompts

**URL:** `/admin/prompts`
**Roles:** Owner, Master
**Prerequisites:** None

### Test: View and Edit Global Prompts

- [ ] Navigate to `/admin/prompts`
- [ ] Verify default prompts display for deal, portfolio, and preferences types
- [ ] Edit a prompt — save — verify success message
- [ ] Clear a prompt — save — verify it reverts to the hardcoded default

**Expected:** Global prompt overrides saved. Empty overrides revert to defaults.

### Test: Validate Prompt

- [ ] Click "Validate" on a prompt
- [ ] Verify validation checks: mentions JSON, includes required keys, has role instruction, appropriate length
- [ ] Test with a prompt missing required keys — verify warnings

**Expected:** Validation returns specific, actionable issues.

### Test: Test Prompt with Sample Data

- [ ] Click "Test" on a prompt
- [ ] Verify a modal opens with editable sample data fields
- [ ] Edit the sample data if desired
- [ ] Click "Run Test" — verify loading indicator
- [ ] Verify the AI response renders with pretty-formatted JSON
- [ ] Check response time displayed

**Expected:** Real AI call made with sample data. Response displayed with formatting.

---

## Page: Admin Diagnostics

**URL:** `/admin/diagnostics`
**Roles:** Owner, Master
**Prerequisites:** API calls have been logged

### Test: View Diagnostics

- [ ] Navigate to `/admin/diagnostics`
- [ ] Verify summary: total calls (24h), average response time, error rate
- [ ] Verify per-call log: timestamp, call type, success/failure, response time, HTTP status, details
- [ ] Check Zillow and Realtor call counts

**Expected:** Last 200 paid API calls displayed with performance metrics.

---

## Page: Site Manager

**URL:** `/admin/sites`
**Roles:** Master only
**Prerequisites:** At least one site exists in the registry

### Test: View Site List

- [ ] Log in as master
- [ ] Navigate to `/admin/sites` (Manage in nav)
- [ ] Verify all sites listed with display name, site key, active status, database path

**Expected:** All registered sites displayed.

### Test: Create a New Site

- [ ] Click "Create Site"
- [ ] Enter a display name, site key, and location
- [ ] Use the location picker typeahead to set map center coordinates
- [ ] Submit
- [ ] Verify the site database is created
- [ ] Verify the site appears in the list

**Expected:** New site created with its own SQLite database and registry entry.

### Test: Edit Site Configuration

- [ ] Click "Edit" on an existing site
- [ ] Change display name, map center, default zoom, or map bounds
- [ ] Save — verify changes persist

**Expected:** Site configuration updated in registry.

### Test: Toggle Site Active

- [ ] Click "Toggle Active" on a site
- [ ] Verify status changes between active and inactive
- [ ] When inactive, verify the site does not appear on the welcome page

**Expected:** Site active toggle works. Inactive sites hidden from market picker.

### Test: Delete a Site

- [ ] Click "Delete" on a site
- [ ] Confirm deletion
- [ ] Verify the site is removed from the registry

**Expected:** Site record removed. Database file may or may not be deleted (check implementation).

### Test: Scheduler Lock

- [ ] Toggle the scheduler lock on a site card
- [ ] As an owner, try to resume the scheduler

**Expected:** When locked by master, owner cannot resume the scheduler. Gets error message.

### Test: Max Fetches

- [ ] Set a max fetches limit on a site
- [ ] Run the pipeline — verify it stops at the configured limit

**Expected:** Pipeline respects the max fetches setting.

### Test: Nav Links

- [ ] Click "Sites" in the nav — verify it goes to the welcome/chooser page with `?chooser=1`
- [ ] Click "Manage" in the nav — verify it goes to the site manager CRUD page

**Expected:** Both nav links work and go to the correct destinations.

---

## Page: Docs

**URL:** `/docs`
**Roles:** Owner, Master (for upload/delete); others may have read access
**Prerequisites:** Documentation files exist in the docs directory

### Test: Browse Documentation

- [ ] Navigate to `/docs`
- [ ] Verify a file browser displays available documentation files
- [ ] Click on a file — verify markdown renders in a viewer

**Expected:** Documentation files listed and rendered as formatted markdown.

### Test: Upload a Document (Owner/Master)

- [ ] Click "Upload"
- [ ] Select a markdown file
- [ ] Verify it appears in the file list

**Expected:** File uploaded and available in the docs browser.

### Test: Delete a Document (Owner/Master)

- [ ] Click "Delete" on a document
- [ ] Verify it is removed from the list

**Expected:** File deleted. No longer appears in the browser.

---

## Page: Help

**URL:** `/help`
**Roles:** All
**Prerequisites:** None

### Test: View Help Page

- [ ] Click "Help & Guide" in the Help dropdown
- [ ] Verify the page loads with feature descriptions and instructions

**Expected:** Help content renders.

### Test: Why HomeFinder Pages

- [ ] Click "Why HomeFinder? (Buyers)" — verify buyer-focused content
- [ ] Click "Why HomeFinder? (Agents)" — verify agent-focused content
- [ ] As owner, click "Owner Operations Guide" — verify owner-focused content

**Expected:** Role-specific informational pages render correctly.

---

## Mobile and PWA

**Roles:** All
**Prerequisites:** Access via mobile device or DevTools mobile viewport

### Test: Responsive Layout

- [ ] Open the dashboard on a phone-sized viewport (375px wide)
- [ ] Verify listing cards stack photo on top, details below
- [ ] Verify the nav collapses into a hamburger menu
- [ ] Verify nav icons stack vertically when menu is open
- [ ] Verify touch targets are at least 44x44 pixels

**Expected:** Fully responsive layout with no horizontal overflow.

### Test: Map Full Height

- [ ] Open the map page on mobile
- [ ] Verify the map takes full viewport height

**Expected:** Map fills available screen space on mobile.

### Test: PWA Install

- [ ] On a supported mobile browser (Chrome Android), navigate to the app
- [ ] Verify the "Add to Home Screen" prompt appears or is available in the browser menu
- [ ] Add to home screen — verify the app opens in standalone mode

**Expected:** App installs as a PWA with correct icon and name.

---

## Cross-Cutting Features

### Test: Masquerade — Agent as Client

**Roles:** Agent
**Prerequisites:** Agent has assigned clients

- [ ] Log in as an agent
- [ ] On the agent dashboard, click the masquerade/preview button for a client
- [ ] Verify the masquerade banner appears at the top: "Agent Preview Mode — You are viewing as [client]"
- [ ] Verify the nav shows the client's username
- [ ] Browse the dashboard — verify preferences and flags reflect the client's data
- [ ] Click "End Preview" — verify return to the agent account
- [ ] Verify the masquerade banner disappears

**Expected:** Agent sees the app as the client would. End preview restores agent context.

### Test: Masquerade — Master as Anyone

**Roles:** Master
**Prerequisites:** Multiple user accounts exist

- [ ] Log in as master
- [ ] Navigate to user management
- [ ] Masquerade as an owner — verify owner nav items appear
- [ ] End masquerade — masquerade as a regular user — verify limited nav
- [ ] End masquerade — verify master context restored

**Expected:** Master can impersonate any role and see the app from their perspective.

### Test: Guest Mode

**Roles:** Unauthenticated
**Prerequisites:** Listings exist

- [ ] Without logging in, navigate to a site dashboard
- [ ] Verify listings load with scores
- [ ] Flag a listing — verify it persists in the session
- [ ] Adjust preferences — verify scores update
- [ ] Share a listing — verify guest share (name/email fields appear)
- [ ] Click AI analysis — verify "Join" modal prompts for account creation
- [ ] Close browser and reopen — verify flags and preferences are lost

**Expected:** Full browsing experience without login. Session-based persistence only.

### Test: Email Notifications

**Prerequisites:** Mail server configured

- [ ] Share a listing — verify recipient gets notification email
- [ ] React to a share — verify sharer gets reaction email
- [ ] Send a referral — verify invitee gets referral email
- [ ] Register a new account — verify welcome/verification email sent
- [ ] Create a client as agent — verify client welcome email sent
- [ ] Trigger a social digest — verify digest emails sent

**Expected:** All email types send correctly with proper content and links.

### Test: Close Account

**Roles:** Authenticated users
**Prerequisites:** Logged in

- [ ] Click username dropdown > "Close Account"
- [ ] Verify a confirmation page appears with warnings
- [ ] Confirm account closure
- [ ] Verify logout and account data is anonymized
- [ ] Attempt to log in with the old credentials

**Expected:** Account closed. Login fails. Email/username freed for reuse.

---

## Appendix: Points Earning Actions

| Action | Points | Notes |
|--------|--------|-------|
| Share a listing | 1 | Per share |
| Reaction received | 3 | Per unique reaction on your shares |
| Create a collection | 2 | Per collection |
| Submit a friend listing | 5 | Neighborhood Tip |
| Approve a listing (agent) | 3 | Per approval |
| Create a listing (agent) | 5 | Direct listing creation |
| Referral signup | Varies | When referred user registers |

Daily cap: 50 points per day.

---

## Appendix: 18 Deal Score Factors

For reference when testing score panels:

1. Price (within range)
2. Size (sqft)
3. Bedrooms
4. Bathrooms
5. Yard / Lot size
6. Year built
7. Garage
8. Porch
9. Patio
10. Single story
11. Community pool
12. Price per sqft
13. HOA monthly
14. Property tax annual
15. Flood zone risk
16. Above flood plain
17. Days on market
18. POI proximity (distance to selected landmark)
