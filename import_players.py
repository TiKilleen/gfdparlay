"""Seeds the players table from Sleeper's free public NFL player list
(no API key required). Re-runnable: matches existing rows by external_id
and only inserts new ones, so re-running after roster moves just adds
whoever's new.

Usage: python import_players.py
"""

import requests

from app import create_app
from extensions import db
from models import Player

SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"

# Restrict to skill positions people actually bet player props on -- the
# full Sleeper dump includes offensive linemen, practice-squad players, and
# thousands of inactive entries that would just be noise in the autocomplete.
RELEVANT_POSITIONS = {"QB", "RB", "WR", "TE", "K"}


def run():
    app = create_app()
    with app.app_context():
        existing_external_ids = {
            p.external_id for p in Player.query.filter(Player.external_id.isnot(None))
        }
        existing_names = {p.display_name for p in Player.query.all()}

        resp = requests.get(SLEEPER_PLAYERS_URL, timeout=30)
        resp.raise_for_status()
        all_players = resp.json()

        added = 0
        for external_id, info in all_players.items():
            if external_id in existing_external_ids:
                continue
            if info.get("position") not in RELEVANT_POSITIONS:
                continue
            full_name = info.get("full_name")
            if not full_name:
                continue

            display_name = full_name
            if display_name in existing_names:
                # Sleeper does have same-name collisions (e.g. multiple
                # "Josh Allen" entries) -- disambiguate by position.
                display_name = f"{full_name} ({info.get('position')})"
                if display_name in existing_names:
                    continue

            db.session.add(
                Player(
                    display_name=display_name,
                    external_id=external_id,
                    source="nfl_import",
                )
            )
            existing_names.add(display_name)
            added += 1

        db.session.commit()
        print(f"Imported {added} new players.")


if __name__ == "__main__":
    run()
