# HomeFinder — Deployment Guide

**Version:** 2026.03.12
**Last Updated:** 2026-03-13

---

## Prerequisites

- **Windows Server** with IIS 10+ and HttpPlatformHandler installed
- **Python 3.10+** (system-wide or per-app virtual environment)
- **SMTP access** for email verification and Street Watch alerts
- **RapidAPI account** with Zillow/Realtor API subscriptions
- **Anthropic API key** for Claude AI deal analysis

---

## Local Development Setup

```bash
cd D:\Projects\home_finder_agents
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your API keys and SMTP credentials:
```ini
SECRET_KEY=<generate a random 64-char string>
RAPIDAPI_KEY=<your RapidAPI key>
ANTHROPIC_API_KEY=<your Anthropic key>
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=you@gmail.com
MAIL_PASSWORD=<app-specific password>
MAIL_DEFAULT_SENDER=you@gmail.com
GEOAPIFY_KEY=<optional, free at geoapify.com>
```

Start the development server:
```bash
python run_waitress.py
# Visit http://localhost:5000/home_finder_agents/welcome
```

---

## IIS Production Deployment

### 1. Application Pool

Create a new IIS Application Pool:
- **Name:** `HomeFinderAgents`
- **Pipeline Mode:** Integrated
- **.NET CLR Version:** No Managed Code
- **Start Mode:** AlwaysRunning (recommended)
- **Idle Timeout:** 0 (disable)

### 2. Site / Virtual Application

Create a virtual application under your IIS site:
- **Alias:** `home_finder_agents`
- **Physical Path:** `D:\Projects\home_finder_agents`
- **Application Pool:** `HomeFinderAgents`

### 3. web.config

The `web.config` in the project root configures HttpPlatformHandler:

```xml
<httpPlatform processPath="D:\Projects\home_finder_agents\.venv\Scripts\python.exe"
              arguments="run_waitress.py --port=%HTTP_PLATFORM_PORT%"
              stdoutLogEnabled="true"
              stdoutLogFile="logs\iis-stdout.log"
              startupTimeLimit="60"
              processesPerApplication="1">
</httpPlatform>
```

**Security rules block direct access to:**
- `.env` — environment secrets
- `instance/` — SQLite databases
- `__pycache__/` — bytecode
- `.venv/` — virtual environment
- `.py`, `.pyc`, `.db`, `.sqlite` file extensions

### 4. Directory Permissions

The IIS app pool identity needs read/write access to:
- `instance/` — SQLite databases
- `logs/` — application logs
- `data/` — Census shapefiles (read only)

Run the permissions script:
```powershell
.\bin\set_permissions.ps1
```

### 5. SSL Certificate

Ensure HTTPS is configured on the parent IIS site. HomeFinder generates all external URLs (email links, unsubscribe links) using `https://`.

---

## Pipeline Scheduling

### Windows Task Scheduler (Recommended)

Create a scheduled task for nightly pipeline runs:

- **Trigger:** Daily at 3:00 AM
- **Action:** `D:\Projects\home_finder_agents\.venv\Scripts\python.exe`
- **Arguments:** `bin\scheduled_pipeline.py`
- **Start in:** `D:\Projects\home_finder_agents`
- **Run whether user is logged on or not**

### Manual Pipeline Trigger

From the command line:
```bash
python pipeline.py --site charleston          # fetch + score all
python pipeline.py --site charleston --rescore # re-score only (no API calls)
```

From the web dashboard (owner/master role):
1. Navigate to Dashboard
2. Click the "Fetch Now" button
3. Pipeline runs inline and shows results

---

## Post-Deployment Changes

After modifying any Python, template, or config file:

### 1. Clear bytecode cache
```powershell
Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ |
    Remove-Item -Recurse -Force
```

### 2. Recycle IIS app pool
```powershell
C:\Windows\System32\inetsrv\appcmd.exe recycle apppool /apppool.name:HomeFinderAgents
```

### 3. Hard-refresh browser
Press **Ctrl+Shift+R** to bypass cached templates and static files.

---

## Database Management

### Registry Database

Location: `instance/registry.db`

Override with environment variable:
```ini
HOMEFINDER_REGISTRY=D:\Data\registry.db
```

The registry is auto-initialized with a default Charleston, SC site on first run.

### Per-Site Databases

Each market has its own SQLite database:
- `instance/charlestonsc.db`
- `instance/catonsvillemd.db`
- etc.

Created automatically when a new site is added via the Site Manager.

### Migrations

Database migrations run automatically at app startup via `app/migrations.py`. All migrations are idempotent (guarded with `inspector.has_table()` checks).

### Backups

SQLite databases can be backed up by copying the `.db` files while the app pool is stopped:

```powershell
# Stop the pool
Stop-WebAppPool -Name 'HomeFinderAgents'

# Copy databases
Copy-Item instance\*.db D:\Backups\homefinder\

# Restart
Start-WebAppPool -Name 'HomeFinderAgents'
```

---

## Creating a New Market

1. Log in as **master** role
2. Navigate to **Sites** in the top nav
3. Click **Map Picker** to set the center location
4. Type a city name to jump the map
5. Click zip codes on the map to select them
6. Fill in the display name and area configuration
7. Click **Create Site**

The system will:
- Create a new row in `registry.db`
- Initialize a new per-site SQLite database
- Create all ORM tables via migrations
- The site is immediately available at `/site/<key>/`

---

## Test Accounts

Each site is provisioned with four test accounts using the master email (`philipalarson@gmail.com`):

| Username | Role | Purpose |
|----------|------|---------|
| `master_<site>` | master | Full system access |
| `owner_<site>` | owner | Site administration |
| `agent_<site>` | agent | Agent features |
| `user_<site>` | client | Buyer experience |

---

## Monitoring

### Application Logs

- **IIS stdout:** `logs/iis-stdout.log`
- **Python logging:** Console output captured by IIS

### API Diagnostics

Navigate to `/admin/diagnostics` (owner/master) to view:
- API call history with success/failure rates
- Response times
- Quota remaining
- Estimated costs

### Metrics Dashboard

Navigate to `/admin/metrics` (owner/master) to view:
- Active users by role
- Listings by status and source
- Scoring distribution
- API call volume over time

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 500 error after deploy | Stale bytecode | Clear `__pycache__`, recycle pool |
| Templates not updating | Browser cache | Ctrl+Shift+R |
| Pipeline not running | Task Scheduler disabled | Check Task Scheduler history |
| Email not sending | SMTP credentials | Verify `.env` MAIL_* vars |
| AI analysis fails | API key invalid/expired | Check `ANTHROPIC_API_KEY` in `.env` |
| Street autocomplete empty | No Geoapify key | Add `GEOAPIFY_KEY` to `.env` |
| Database locked | Concurrent writes | Ensure single IIS process (`processesPerApplication=1`) |
| Login fails after pool recycle | Session lost | Expected — users re-login |
