# Football Betting Tracker

Structured replacement for the manual "2025-2026 Football Betting" Google
Sheet. Every parlay leg (player, prop, odds, who picked it) is entered as a
real row instead of typed into one free-text cell, so the Player table,
Bettor scoreboard, and category win-rates on the dashboard are computed
live instead of re-tallied by hand.

Two dashboard sections stay strictly separate, matching how the sheet
already worked: **Group Parlay Analysis** (the weekly 5-friend parlays) and
**Solo Bet Analysis** (bets placed alone). A bet's `is_group_bet` flag is
what decides which section it counts toward -- not its bet type name.

## Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export FLASK_APP=app.py FLASK_DEBUG=1
flask db upgrade        # creates dev.db (SQLite) and applies migrations
python seed.py           # seeds bettors / bet types / prop categories
python import_players.py # seeds ~4k NFL skill-position players from Sleeper's public API

flask run --port=5050
```

Visit `http://localhost:5050`. No Postgres needed locally -- `config.py`
falls back to a local SQLite file (`dev.db`, gitignored) whenever
`DATABASE_URL` isn't set.

## Adding things as you go

- **New friend joins the group:** add them on the [Bettors](/bettors) page.
- **New bet type:** add it on the [Bet Types](/bet-types) page, and mark
  whether it should default to "Group Parlay" on the New Bet form.
- **New prop category or player:** just type the name on the New Bet form
  -- both fields autocomplete against what already exists and create a new
  row on the fly if it doesn't.

## Deploying to Render

This follows the same manual-dashboard pattern as `btwb-project` -- no
`render.yaml`, everything set up by hand:

1. Push this repo to GitHub.
2. In the Render dashboard, create a **Postgres** instance (Basic-256mb,
   ~$6-7/mo -- Render's free Postgres now auto-deletes after 30 days, so it
   isn't viable for a season-long tracker). Copy its internal connection
   string.
3. Create a **Web Service** from this repo, Docker runtime (uses the
   `Dockerfile` here). Set the `DATABASE_URL` env var to the Postgres
   connection string from step 2, and set `SECRET_KEY` to a random value.
4. Deploy. The container's start command (`flask db upgrade && gunicorn...`)
   runs migrations automatically on every deploy.
5. Once it's live, SSH/shell into the service (or run locally against the
   same `DATABASE_URL`) to run `python seed.py` and `python import_players.py`
   once, the same as local setup.

## Not built yet (by design -- see the plan for why)

- Backfilling the historical rows from the old Google Sheet.
- Mirroring data back out to Google Sheets.
