# Y Stainer Pressure Drop Calculator

> **Forbes Marshall Method | FastAPI | Bootstrap 5 | PostgreSQL**

A production-ready web application that calculates pressure drop across Y-strainers for 100% clean and 50% clogged screen conditions. Built with Python/FastAPI, validated against 14 real Forbes Marshall software screenshots (all pass ≤ 0.5% deviation).

---

## Table of Contents

1. [Business Model — One-Time Client Delivery](#1-business-model--one-time-client-delivery)
2. [Architecture Overview](#2-architecture-overview)
3. [Prerequisites](#3-prerequisites)
4. [Railway Deployment — Step by Step](#4-railway-deployment--step-by-step)
5. [PostgreSQL Setup on Railway](#5-postgresql-setup-on-railway)
6. [Environment Variables Reference](#6-environment-variables-reference)
7. [Uploading the Excel Reference File](#7-uploading-the-excel-reference-file)
8. [Post-Deployment Checklist](#8-post-deployment-checklist)
9. [Handing Credentials to Your Client](#9-handing-credentials-to-your-client)
10. [Maintenance & Support](#10-maintenance--support)

---

## 1. Business Model — One-Time Client Delivery

This application is designed for the **"build once, sell once"** model:

```
You build the app  →  Client pays cash (one-time)
    │
    ▼
You deploy on Railway under YOUR account
    │
    ▼
You create ONE admin account for the client
    │
    ▼
You hand over:
  - App URL  (e.g. https://ystainer-client.up.railway.app)
  - Admin username & password
    │
    ▼
Client uses the app. You own the infra.
```

### Recommended Pricing Structure

| What | Amount |
|------|--------|
| One-time build fee (your fee) | ₹50,000 – ₹1,50,000 |
| Railway hosting / year (your cost) | ~$60/year (~₹5,000) |
| Annual maintenance retainer (optional) | ₹10,000 – ₹20,000/year |

**Tip**: Charge the client the one-time fee upfront in cash. Keep the Railway account under your name. Offer an optional annual support contract for updates and hosting renewals. This keeps recurring revenue with you.

---

## 2. Architecture Overview

```
Browser (Client)
      │  HTTPS
      ▼
Railway CDN / Proxy
      │
      ▼
FastAPI App (Railway Web Service)
  ├── Auth        → PostgreSQL (Railway Postgres plugin)
  ├── Calculator  → Pure Python (no DB needed)
  ├── Lookups     → Excel file (bundled in repo)
  └── Templates   → Jinja2 + Bootstrap 5
```

**Stack:**

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL (Railway managed) |
| Auth | Session cookies + PBKDF2 passwords |
| Frontend | Jinja2 templates + Bootstrap 5 |
| Hosting | Railway.app |
| SSL | Auto (Let's Encrypt via Railway) |

---

## 3. Prerequisites

Before deploying, ensure you have:

- [ ] A **Railway account** — sign up free at https://railway.app
- [ ] **Git** installed on your machine
- [ ] The **Excel reference file** (`Pr drop cal data for Y strainer.xlsx`) ready
- [ ] **Python 3.11+** installed locally (for testing)
- [ ] This repo cloned locally and working (`python -m pytest test_api.py` passes)

---

## 4. Railway Deployment — Step by Step

### Step 1 — Prepare the repository

Ensure the Excel file is in the repo root (it is excluded from git by default because of `.gitignore`). You have two options:

**Option A (Recommended): Include the Excel file in the repo**

```bash
# Remove xlsx from .gitignore
# Edit .gitignore and delete the line: *.xlsx

# Add and commit the file
git add "Pr drop cal data for Y strainer.xlsx"
git commit -m "Add Excel reference data"
git push origin main
```

**Option B: Upload via Railway Volume** (see Section 7)

---

### Step 2 — Migrate database.py to PostgreSQL

Railway provides a PostgreSQL connection string via the `DATABASE_URL` environment variable.
Update `database.py` to use it:

```python
# database.py  — add at the top
import os

# Use PostgreSQL on Railway, fall back to SQLite locally
_DATABASE_URL = os.getenv("DATABASE_URL")

if _DATABASE_URL:
    # Railway PostgreSQL
    import psycopg2
    def _get_conn():
        return psycopg2.connect(_DATABASE_URL)
else:
    # Local SQLite fallback
    import sqlite3
    def _get_conn():
        return sqlite3.connect(DB_PATH)
```

For simplicity on a single-client deployment, the existing SQLite approach works fine on Railway too — just ensure a **Persistent Volume** is attached (Step 6). If the client needs multi-user concurrent access, use PostgreSQL.

---

### Step 3 — Add required files for Railway

**`Procfile`** (already should exist — create if not):
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**`runtime.txt`**:
```
python-3.11
```

Commit these files:
```bash
git add Procfile runtime.txt
git commit -m "Add Railway deployment files"
git push origin main
```

---

### Step 4 — Create a new Railway project

1. Go to https://railway.app → **New Project**
2. Select **Deploy from GitHub repo**
3. Connect your GitHub account and select **awajirwad123/Y-strainer**
4. Railway auto-detects Python and starts building

---

### Step 5 — Add PostgreSQL database

1. In your Railway project dashboard, click **+ New**
2. Select **Database → Add PostgreSQL**
3. Railway creates a Postgres instance and sets `DATABASE_URL` automatically in your service's environment

---

### Step 6 — Add Persistent Volume (for SQLite / uploaded files)

If using SQLite:

1. In Railway project → your web service → **Volumes** tab
2. Click **Add Volume**
3. Mount path: `/data`
4. Add environment variable: `DATA_DIR=/data`

This ensures `users.db` and the Excel file survive redeployments.

---

### Step 7 — Set Environment Variables

In Railway dashboard → your service → **Variables** tab, add:

| Variable | Value | Notes |
|----------|-------|-------|
| `SECRET_KEY` | (random 32-char string) | Run: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATA_DIR` | `/data` | Persistent volume mount path |
| `ENVIRONMENT` | `production` | Disables debug mode |

Railway automatically sets:
- `PORT` — the port uvicorn should bind to
- `DATABASE_URL` — PostgreSQL connection string (if Postgres plugin added)

---

### Step 8 — Deploy

Railway automatically builds and deploys when you push to `main`.

To trigger a manual deploy: Railway dashboard → **Deploy** button.

**Build logs** are visible in real-time in the dashboard. A successful deploy shows:
```
✓ Build succeeded
✓ Deploy succeeded
● Running on https://your-app-name.up.railway.app
```

---

### Step 9 — Verify

Open your app URL. You should see the **Login page**.

Run the health check:
```bash
curl https://your-app-name.up.railway.app/login
# Should return HTTP 200
```

---

## 5. PostgreSQL Setup on Railway

If you opted for full PostgreSQL (recommended for production):

### Install the Python driver

```bash
pip install psycopg2-binary
# Add to requirements.txt
echo "psycopg2-binary>=2.9.9" >> requirements.txt
```

### Update database.py for PostgreSQL

Replace the SQLite `sqlite3` calls with `psycopg2`. The key change is in `init_db()`:

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ["DATABASE_URL"]

def init_db():
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            SERIAL PRIMARY KEY,
                    username      TEXT UNIQUE NOT NULL,
                    email         TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at    TIMESTAMP DEFAULT NOW()
                )
            """)
        conn.commit()
```

---

## 6. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | Auto (Railway) | 8000 | Port for uvicorn |
| `SECRET_KEY` | **Yes** | — | Session signing key |
| `DATABASE_URL` | Auto (Railway Postgres) | — | PostgreSQL connection string |
| `DATA_DIR` | Yes (if SQLite) | `.` | Directory for `users.db` |
| `ENVIRONMENT` | No | `development` | Set to `production` |

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 7. Uploading the Excel Reference File

The Excel file (`Pr drop cal data for Y strainer.xlsx`) contains all lookup tables (mesh, perforation, strainer dimensions). It must be available to the running app.

### Option A — Include in Git repo (simplest)

```bash
# In .gitignore, remove or comment out the *.xlsx line
git add "Pr drop cal data for Y strainer.xlsx"
git commit -m "Include lookup data"
git push
```

The file is read-only reference data, so committing it is safe. File size is typically < 1MB.

### Option B — Upload via Railway Volume

1. SSH into your Railway service (Railway shell)
2. Upload the file to `/data/` using the Railway CLI:
```bash
railway run -- python -c "print('shell works')"
```
3. Update `config.py` to read from `DATA_DIR`:
```python
import os
_EXCEL_PATH = Path(os.getenv("DATA_DIR", Path(__file__).parent)) / "Pr drop cal data for Y strainer.xlsx"
```

**Recommendation**: Use Option A. Include the file in git. It is reference data, not secrets.

---

## 8. Post-Deployment Checklist

After deploying, verify each item:

- [ ] App loads at your Railway URL
- [ ] Login page renders correctly
- [ ] Signup creates a new account
- [ ] Calculator page loads and dropdowns populate
- [ ] Enter a known case and verify the result:
  - Density: `0.951`, Viscosity: `0.248`, Flow: `165 kg/hr`
  - Pipe ID: `2.5 cm`, Screen D: `2.6 cm`, Length: `8.0 cm`
  - D open: `0.05 cm`, Q%: `62.7`, P%: `51`
  - Expected ΔP (100% clean): **0.037029 cm WC**
  - Expected ΔP (50% clogged): **0.11761 cm WC**
- [ ] SSL is active (padlock in browser)
- [ ] App URL is accessible from client's browser

---

## 9. Handing Credentials to Your Client

Once deployed and tested, hand over the following to your client **in person or via encrypted channel**:

### What to give the client

```
Application URL:   https://your-app-name.up.railway.app
Admin Username:    (create via signup on the deployed app)
Admin Password:    (strong password, e.g. 16+ chars)
```

### Create the admin account before handover

1. Open the deployed app URL
2. Click **Create one** (signup)
3. Register with:
   - Username: something professional, e.g. `client_admin`
   - Email: client's email address
   - Password: a strong generated password
4. Test login works
5. Write credentials on paper or in a password manager — hand to client in person

### What NOT to give the client

- Railway dashboard access (keep this under your account)
- `.session_secret` file
- Database credentials
- GitHub repo access (unless negotiated)

### Protecting yourself

1. **Keep Railway under your name** — you control uptime and renewals
2. **Charge for hosting annually** or include 1 year in the project price
3. **Keep a copy of the codebase** — you built it
4. **Service agreement**: get a simple written agreement that defines support scope

---

## 10. Maintenance & Support

### Typical ongoing tasks

| Task | Frequency | Time |
|------|-----------|------|
| Railway billing renewal | Annual (~$60/year) | 5 min |
| Password reset for client | On request | 2 min |
| Adding new strainer models to Excel | On request | 30 min |
| Bug fixes or formula updates | On request | Variable |

### How to deploy an update

```bash
# Make changes locally, test them
python -m pytest test_api.py -v
python validate_production.py

# Commit and push — Railway auto-deploys
git add .
git commit -m "Update: describe what changed"
git push origin main
# Railway builds and deploys in ~2 minutes. Zero downtime.
```

### Monitoring (free)

Set up **UptimeRobot** (https://uptimerobot.com — free) to ping your app every 5 minutes and email you if it goes down.

1. Create free account
2. Add monitor → HTTP(S) → your Railway URL
3. Add your email for alerts

---

## Running Locally

```bash
# Clone
git clone https://github.com/awajirwad123/Y-strainer.git
cd Y-strainer

# Install dependencies
pip install -r requirements.txt

# Run
uvicorn main:app --reload

# Open browser
# http://localhost:8000
```

**Run tests:**
```bash
python -m pytest test_api.py -v          # 20 API tests
python validate_production.py            # 27 production checks
```

---

## License

Private — all rights reserved. Built by [Your Name / Company].
Not for redistribution without written permission.
