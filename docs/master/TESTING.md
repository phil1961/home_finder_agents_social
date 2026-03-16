# HomeFinder — Testing Guide

**Version:** 2026.03.14
**Last Updated:** 2026-03-14

---

## Quick Start

```bash
cd D:\Projects\home_finder_agents_social
python -m pytest tests/ -v
```

All tests use temporary SQLite databases — no production data is touched.

---

## Prerequisites

```bash
pip install pytest
```

No other test-specific dependencies are needed. The test suite uses the same packages as the app itself.

---

## Test Suite Overview

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_models.py` | 12 | User, AgentProfile, Listing, UserFlag ORM models |
| `test_auth.py` | 11 | Registration, login, verification, agent guards, masquerade, close account |
| `test_scoring.py` | 6 | DealScore composite computation, user weights, 18-factor validation |
| `test_street_watch.py` | 20 | Street name extraction, watch CRUD, dedup, token unsubscribe, user linking |
| `test_engagement.py` | 18 | Since-last-visit stats, progressive nudges, smart empty states |
| `test_social_phase2.py` | 17 | Points system, referral loops, social models, agent listing workflow, user suspension, social proof, collections |

**Total: 84 tests**

---

## Test Architecture

### Fixtures (`tests/conftest.py`)

Every test gets a fresh, isolated environment:

1. **`app`** — Creates a temporary registry DB and site DB in `tmp_path`, configures a Flask app with `TESTING=True` and `MAIL_SUPPRESS_SEND=True`
2. **`client`** — Flask test client for HTTP-level tests
3. **`req_ctx`** — Full request context with `g.site` and `g.site_engine` bound to the temp site DB, tables created, migrations applied

### Helpers

| Helper | Purpose |
|--------|---------|
| `make_user()` | Creates a User with hashed password (not yet committed) |
| `make_listing()` | Creates a Listing with unique source_id (not yet committed) |
| `make_agent_profile()` | Creates an AgentProfile for a user (not yet committed) |

All helpers return uncommitted objects — call `db.session.add()` and `db.session.commit()` in your test.

---

## Test Details

### `test_models.py` — ORM Models

**TestUserModel**
- Password hashing and verification (bcrypt via werkzeug)
- Default role is `client`, role hierarchy properties (`is_master`, `is_owner`, `is_agent`, `is_admin`)
- `get_prefs()` returns merged defaults + user overrides
- `set_prefs()` stores only values that differ from defaults (keeps DB lean)
- Principal ↔ AgentProfile relationship via `assigned_agent`

**TestAgentProfile**
- Profile creation with branding fields
- `is_approved` property (pending vs approved)
- `client_count` dynamic count via relationship

**TestListingModel**
- Listing creation and `first_seen` auto-timestamp

**TestUserFlag**
- Flag creation, querying by type
- Favorite count at milestones (verifies the query used by progressive nudges)

### `test_auth.py` — Authentication

**TestRegistration**
- User creation with unique username constraint
- Duplicate username raises `IntegrityError`
- Registration links existing guest street watches to the new account

**TestLogin**
- Correct/incorrect password verification
- Unverified user flag detection

**TestAgentProfileGuards**
- Agent user without AgentProfile row does not crash (regression for 500 errors)
- Agent with profile has branding accessible

**TestMasquerade**
- Principal sees agent branding via `assigned_agent` relationship
- Regular user without `agent_id` has no `assigned_agent`

**TestCloseAccount**
- Credential scrambling: username/email prefixed with `closed_`, password hash set to `ACCOUNT_CLOSED`

### `test_scoring.py` — Deal Scoring

**TestDealScoreModel**
- Basic DealScore creation and 1:1 listing relationship
- `compute_user_composite()` with price-only weights returns high composite
- Balanced weights produce mid-range composite
- All-zero weights return neutral 50.0 (no division by zero)

**TestDefaultImportanceWeights**
- All 18 factors present in `config.DEFAULT_IMPORTANCE`
- All weights within valid range (0–10)

### `test_street_watch.py` — Street Watch

**TestExtractStreetName**
- Basic address: `"123 Oak Dr, Charleston, SC"` → `"OAK DR"`
- Full suffix normalisation: `Drive`→`DR`, `Street`→`ST`, `Lane`→`LN`, etc.
- Directional prefixes preserved: `"N Main Blvd"` stays `"N MAIN BLVD"`
- Edge cases: empty string, `None`, unit suffix (`"100A"`)
- All 11 suffix types tested

**TestCreateWatch**
- New watch creation with unsubscribe token
- Duplicate watch returns existing (idempotent)
- Deactivated watch reactivates on re-creation
- Guest watch (no `user_id`) gets linked when user_id provided later

**TestDeactivateWatch**
- Deactivation by `user_id` and by `email`
- Wrong owner cannot deactivate another user's watch
- Nonexistent watch ID returns `False`

**TestDeactivateByToken**
- Valid unsubscribe token deactivates watch
- Invalid token returns `False`

**TestLinkWatchesToUser**
- Guest watches (email-only) get `user_id` set on registration

**TestGetUserWatches**
- Fetch by `user_id` and by `email`
- Inactive watches excluded from results

### `test_engagement.py` — Engagement Features

**TestSinceLastVisitStats** (Feature 1)
- Authenticated user with `last_login` gets new listing and price drop counts
- Old listings (before `last_login`) are excluded
- Guests get `total_scored` but not `new_count`

**TestProgressiveNudges** (Feature 2)
- Favorite count reaches 1, 3, and 5 milestones
- Principal with agent gets agent-name-aware nudge text
- Guest at 3 favorites triggers account creation nudge

**TestSmartEmptyStates** (Feature 3)
- 8 template files verified to contain value-first messaging:
  - `digest.html` — "broadening your price range"
  - `watch.html` — "first to know"
  - `admin_agents.html` — "all caught up" + signup link
  - `agent_dashboard.html` — "welcome email" + "branding"
  - `admin_metrics.html` — "pipeline runs"
  - `landing.html` — "free account"
  - `welcome.html` — "adding new markets"
  - `index.html` — `since_stats` template variable present

### `test_social_phase2.py` -- Social Phase 2

**TestPointsSystem**
- Points awarded for actions using `award_points()`
- Daily cap (50 points) enforced -- excess awards silently capped
- Balance and lifetime totals tracked correctly

**TestReferralLoop**
- Referral chain creation and attribution
- Points awarded on successful referral conversion

**TestSocialModels**
- SocialShare, SocialReaction, SocialCollection, SocialCollectionItem creation
- Relationship integrity between social models

**TestAgentListingWorkflow**
- Agent creates listing directly via `/agent/add-listing`
- Friend listing submission, review, approval (creates Listing row), and rejection (with reason)
- Status transitions: active -> approved/rejected

**TestUserSuspension**
- `is_suspended` flag and `suspended_reason` on User model
- Admin suspend/reactivate/delete actions via `/admin/users/<id>/action`

**TestShareCountsAndSocialProof**
- Share count aggregation per listing
- Social proof badge data ("X people shared this")

**TestCollections**
- Collection creation, item add/remove
- Collection sharing

---

## Running Specific Tests

```bash
# Run a single test file
python -m pytest tests/test_street_watch.py -v

# Run a single test class
python -m pytest tests/test_engagement.py::TestSmartEmptyStates -v

# Run a single test
python -m pytest tests/test_models.py::TestUserModel::test_password_hashing -v

# Run with print output visible
python -m pytest tests/ -v -s

# Run only tests matching a keyword
python -m pytest tests/ -v -k "milestone"
```

---

## Adding New Tests

1. Use the `req_ctx` fixture for any test that needs ORM access
2. Use the `app` fixture for template content checks
3. Use helpers (`make_user`, `make_listing`, `make_agent_profile`) to create test data
4. Always `db.session.add()` + `db.session.commit()` before querying
5. Each test runs in an isolated temp DB — no cleanup needed

### Example

```python
def test_new_feature(self, req_ctx):
    from app.models import db
    from tests.conftest import make_user, make_listing

    user = make_user(username="example", email="ex@test.com")
    db.session.add(user)
    listing = make_listing(price=500000)
    db.session.add(listing)
    db.session.commit()

    # Your assertions here
    assert listing.price == 500000
```

---

## Phase 2 Testing Patterns

**Points cap testing:** Award points in a loop exceeding `DAILY_CAP` (50), then assert `balance <= DAILY_CAP` and that `UserPointLog` entries reflect the capped amounts.

**Referral lifecycle:** Create a referrer user, simulate a referred signup, verify the `Referral` record links both users, then confirm points are awarded to the referrer.

**Friend listing approval:** Create a `FriendListing`, call the agent review endpoint, assert status transitions (`active` -> `approved` or `rejected`), and verify that approval creates a corresponding `Listing` row with `listing_id` back-linked.

---

## CI Integration

The test suite is designed for CI pipelines:

- No external services required (no API keys, no SMTP, no network)
- All databases are temporary (auto-cleaned by pytest `tmp_path`)
- Deterministic — no random data, no timing dependencies
- Exit code 0 on success, non-zero on failure

```bash
# CI one-liner
python -m pytest tests/ --tb=short -q
```
