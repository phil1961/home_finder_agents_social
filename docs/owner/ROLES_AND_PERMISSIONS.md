# HomeFinder — Roles & Permissions Matrix

**Version:** 2026.03.15
**Last Updated:** 2026-03-15

---

## Role Hierarchy

```
master
  └─ owner
       └─ agent
            └─ principal (agent-managed)
            └─ client (self-registered)
                 └─ guest (no account)
```

Each role inherits all capabilities of the roles below it.

---

## Role Descriptions

### Guest (No Account)
A visitor browsing without logging in. Can explore listings, view deal scores, and flag properties — but all data is stored in the browser session and lost when the session expires.

### Client
A self-registered user with full control over their experience. Can customize scoring preferences, use AI analysis, add notes, plan tours, and set up Street Watch alerts.

### Principal
An agent-managed buyer account. Created by an agent via invitation. Principals can edit their own scoring preferences (agents may also update them — last save wins). All buyer features are available.

### Agent
A real estate professional serving buyers. Can manage a roster of principal clients, customize AI prompts, apply branding, and masquerade as their own clients.

### Owner
A market administrator. Can approve/suspend agents, view usage metrics, trigger pipelines, and set site-wide AI prompt overrides.

### Master
The platform administrator with access to all sites. Can create/delete markets, manage the registry, and masquerade as any user in any site.

---

## Full Permissions Matrix

| Capability | Guest | Client | Principal | Agent | Owner | Master |
|-----------|-------|--------|-----------|-------|-------|--------|
| **Browsing** | | | | | | |
| View listings | session | yes | yes | yes | yes | yes |
| View deal scores | session | yes | yes | yes | yes | yes |
| View listing detail | yes | yes | yes | yes | yes | yes |
| View map | yes | yes | yes | yes | yes | yes |
| View digest | yes | yes | yes | yes | yes | yes |
| **Interactions** | | | | | | |
| Flag (favorite/maybe/hidden) | session | yes | yes | yes | yes | yes |
| Listing notes | — | yes | yes | yes | yes | yes |
| Visit status tracking | — | yes | yes | yes | yes | yes |
| **AI Analysis** | | | | | | |
| AI deal brief | — | yes | yes | yes | yes | yes |
| AI portfolio analysis | — | yes | yes | yes | yes | yes |
| AI preference coaching | — | yes | — | yes | yes | yes |
| **Preferences** | | | | | | |
| View scoring weights | session | yes | yes | yes | yes | yes |
| Edit scoring weights | session | yes | yes | yes | yes | yes |
| Set price range | session | yes | yes | yes | yes | yes |
| Set avoid areas | — | — | — | — | — | yes |
| **Street Watch** | | | | | | |
| Create watches | — | yes | yes | yes | yes | yes |
| Manage watches | — | yes | yes | yes | yes | yes |
| Receive alert emails | — | yes | yes | yes | yes | yes |
| **Tour Planning** | | | | | | |
| Plan tours | — | yes | yes | yes | yes | yes |
| Contact assigned agent | — | — | yes | — | — | — |
| **Agent Features** | | | | | | |
| Agent dashboard | — | — | — | yes | yes | yes |
| Manage clients | — | — | — | yes | yes | yes |
| Create principal accounts | — | — | — | yes | yes | yes |
| Edit client preferences | — | — | — | yes | yes | yes |
| Agent branding | — | — | — | yes | — | — |
| Agent AI prompts | — | — | — | yes | yes | yes |
| Masquerade (own clients) | — | — | — | yes | — | — |
| **Admin Features** | | | | | | |
| Trigger pipeline | — | — | — | yes | yes | yes |
| Toggle scheduler | — | — | — | — | yes | yes |
| View metrics | — | — | — | — | yes | yes |
| View diagnostics | — | — | — | — | yes | yes |
| Approve/suspend agents | — | — | — | — | yes | yes |
| Agent notes (contract etc.) | — | — | — | — | yes | yes |
| Site-wide AI prompts | — | — | — | — | yes | yes |
| Masquerade (any user) | — | — | — | — | yes | yes |
| **Platform Features** | | | | | | |
| Site management (create/edit) | — | — | — | — | — | yes |
| Cross-site navigation | — | — | — | — | — | yes |
| Registry management | — | — | — | — | — | yes |
| Documentation management | — | — | — | — | — | yes |
| **Social & Points** | | | | | | |
| View points balance | — | yes | yes | yes | yes | yes |
| Earn points | — | yes | yes | yes | yes | yes |
| View leaderboard | — | yes | yes | yes | yes | yes |
| **Friend Listings** | | | | | | |
| Submit friend listing | — | yes | yes | yes | yes | yes |
| Review pending tips | — | — | — | yes | yes | yes |
| Approve/reject friend listing | — | — | — | yes | yes | yes |
| **Agent Listings** | | | | | | |
| Create listing directly | — | — | — | yes | yes | yes |
| **User Management** | | | | | | |
| Suspend user | — | — | — | — | yes | yes |
| Reactivate user | — | — | — | — | yes | yes |
| Delete user | — | — | — | — | yes | yes |
| **Billing & Quotas** | | | | | | |
| View billing/usage | — | — | — | — | yes | yes |
| Manage billing tiers | — | — | — | — | yes | yes |
| **Social Digest** | | | | | | |
| Trigger social digest email | — | — | — | — | yes | yes |

---

## Role Assignment

| Role | How Assigned |
|------|-------------|
| Guest | Automatic (no account) |
| Client | Self-registration via `/auth/register` |
| Principal | Created by agent via `/agent/clients/create` |
| Agent | Self-registration via `/auth/agent-signup` + owner approval |
| Owner | Promoted from client by master |
| Master | Initial setup only (never created via UI) |

---

## Masquerade Rules

| Actor | Can Impersonate |
|-------|-----------------|
| Agent | Own principals only |
| Owner | Any user in their site |
| Master | Any user in any site |

Masquerade sessions:
- Store original user in `session['masquerade_original_id']`
- Display a visible banner with "End Masquerade" link
- Are audited (original + target user IDs)

**Chained masquerade (master only):** A master can masquerade as an agent, and then the agent can masquerade as one of their principals (via the Preview button on the agent dashboard). The chain is master -> agent -> principal. The session always stores the TRUE original user (master) in `masquerade_original_id` -- intermediate hops never overwrite it. "End Preview" returns straight to the master regardless of chain depth.

**Role switcher (master only):** Master users see a "Switch Role" section in the username dropdown listing all sibling accounts that share the same email address. Each sibling shows a role badge with a colored icon. Clicking a sibling triggers a one-click masquerade without logout/login. The switcher is hidden during an active masquerade session.

---

## Migration Safety

**Critical rule:** Never write migrations that modify `role='master'` accounts. Masters are provisioned during initial setup and must not be altered by automated processes.

Promotion path: `client` → `owner` (via master action only).

---

## User Suspension Rules

| Action | Owner | Master |
|--------|-------|--------|
| Suspend user | Any non-master in own site | Any non-master in any site |
| Reactivate user | Any suspended user in own site | Any suspended user |
| Delete user | Any non-master in own site | Any non-master |

**Constraints:**
- Master accounts are protected from suspension and deletion by non-master users
- Users cannot suspend, reactivate, or delete their own account via admin tools
- Suspended users see the suspension reason at login and cannot access the site
- Deleted users have their credentials renamed and account locked

---

## Points Earning Actions

| Action | Points | Available To |
|--------|--------|-------------|
| Share a listing | +1 | Client, Principal, Agent |
| Reaction received on your share | +3 | Client, Principal, Agent |
| Collection created | +2 | Client, Principal, Agent |
| Friend listing submitted | +5 | Client, Principal, Agent |
| Listing created by agent | +5 | Agent only |
| Listing approved by agent | +3 | Agent only |
| Referral registered | +10 | Client, Principal, Agent |

**Daily cap:** 50 points per day per user.
