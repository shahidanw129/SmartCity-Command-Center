# Smart City Command & Emergency Response System

A responsive Flask + SQLite final-year project prototype for incident intake, triage, coordination, analytics and map visualization.

## Included modules
- Role-aware login session (seeded admin/operator demo account)
- Executive dashboard, KPI cards, recent incidents and activity feed
- Incident reporting, search/filter, detail view, assignment and status updates
- Interactive map using Leaflet + OpenStreetMap (sample Ahmedabad demo coordinates)
- Analytics dashboard with category/severity/status charts
- Response team directory, city services catalog, CSV export and account settings
- Mobile-responsive layout and health endpoint

## Run on Windows
```bat
cd /d "path\to\SmartCity_Command_Center"
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set SECRET_KEY=replace-with-a-long-random-secret
set ADMIN_PASSWORD=Choose-A-Strong-Password
python app.py
```
Open http://127.0.0.1:5000 (or http://127.0.0.1:5000/login)

First-run demo account: `admin` / `Admin@123` unless `ADMIN_PASSWORD` is set before first launch. Change it immediately from Settings. The local SQLite database is created automatically.

## Deploy on Render
1. Push this folder to a GitHub repository.
2. Create a new **Web Service** on Render and connect the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn --workers 1 --threads 4 --timeout 120 app:app`
5. Add a strong `SECRET_KEY` environment variable. Set `ADMIN_PASSWORD` before the first deployment.
6. Deploy and open the Render URL on desktop or phone.

**Important:** Render's local filesystem may be ephemeral, and a free instance may sleep. SQLite data can be lost on redeploy/restart. For persistent production data, connect a managed PostgreSQL database and migrate the schema. This starter is a deployable academic prototype, not a certified municipal emergency system.

## Honest scope / production hardening
Map tiles require internet. The map uses demo/sample coordinates; users must enter valid latitude/longitude for map placement. Alerts and team availability are illustrative, not connected to live emergency dispatch. AI classification, live sensor ingestion, SMS/push alerts, GIS integrations, identity verification, audit-grade logging, PostgreSQL persistence, backups, rate limiting, CSRF protection, and formal security testing are future integration tasks. Never send real emergency or sensitive citizen data to this demo.


### Demo login behavior
For easy academic demonstration, the login page accepts any non-empty email/username and password and automatically creates a local demo user when needed. This is intentionally a demo convenience and must be replaced with real authentication before production use.
