"""One-off seed script for lookup tables. Safe to re-run -- skips rows that
already exist by their unique key."""

from app import create_app
from extensions import db
from models import Bettor, BetType, PropCategory

BETTORS = [
    ("Tim", "ME"),
    ("Chris", "CARR"),
    ("Mike", "MIKE"),
    ("Chuck", "CHUCK"),
    ("Joe", "JOE"),
]

BET_TYPES = [
    ("GFD Parlay", True),
    ("GFD ATD Parlay", True),
    ("DK", False),
    ("Parlay", False),
    ("SGP", False),
    ("Straight", False),
    ("Prop", False),
    ("Special", False),
]

PROP_CATEGORIES = [
    "QB Passing Yards",
    "QB Passing TDs",
    "QB Passing + Rushing",
    "QB Completions",
    "QB Pass Attempts",
    "QB 1Q Pass Yards",
    "QB 1H Pass Yards",
    "QB 1Q Pass Attempts",
    "QB 1Q Pass Completions",
    "QB Rush Attempts",
    "Rushing Yards by RB",
    "Rushing Yards by QB",
    "RB 1H Rush Yards",
    "Rushing + Receiving Yards",
    "Receptions by WR",
    "Receptions by TE",
    "Receptions by RB",
    "Receiving Yards by WR",
    "Receiving Yards by TE",
    "Receiving Yards by RB",
    "Anytime Touchdown",
    "Interceptions",
    "Tackles/Assists",
    "Kicker",
    "Team Total Points",
    "Game Total Points",
]


def run():
    app = create_app()
    with app.app_context():
        for name, short_code in BETTORS:
            if not Bettor.query.filter_by(short_code=short_code).first():
                db.session.add(Bettor(name=name, short_code=short_code))

        for name, default_is_group in BET_TYPES:
            if not BetType.query.filter_by(name=name).first():
                db.session.add(BetType(name=name, default_is_group=default_is_group))

        for name in PROP_CATEGORIES:
            if not PropCategory.query.filter_by(name=name).first():
                db.session.add(PropCategory(name=name))

        db.session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    run()
