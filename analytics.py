"""Query helpers backing the two dashboard sections. Every function takes an
`is_group_bet` filter so Group Parlay Analysis and Solo Bet Analysis stay
built from the same code path but never mix data.
"""

from decimal import Decimal

from sqlalchemy import case, func

from extensions import db
from models import Bet, BetType, Bettor, Leg, Player, PropCategory


def _win_pct(wins, losses):
    decided = wins + losses
    return round(100 * wins / decided, 1) if decided else None


def player_leaderboard(is_group_bet):
    wins = func.sum(case((Leg.result == "win", 1), else_=0))
    losses = func.sum(case((Leg.result == "loss", 1), else_=0))
    pushes = func.sum(case((Leg.result == "push", 1), else_=0))

    rows = (
        db.session.query(Player.display_name, wins, losses, pushes)
        .join(Leg, Leg.player_id == Player.id)
        .join(Bet, Bet.id == Leg.bet_id)
        .filter(Bet.is_group_bet == is_group_bet, Leg.result != "pending")
        .group_by(Player.id)
        .order_by(wins.desc())
        .all()
    )
    return [
        {"name": name, "wins": w, "losses": l, "pushes": p, "win_pct": _win_pct(w, l)}
        for name, w, l, p in rows
    ]


def category_breakdown(is_group_bet):
    wins = func.sum(case((Leg.result == "win", 1), else_=0))
    losses = func.sum(case((Leg.result == "loss", 1), else_=0))

    rows = (
        db.session.query(PropCategory.name, wins, losses)
        .join(Leg, Leg.prop_category_id == PropCategory.id)
        .join(Bet, Bet.id == Leg.bet_id)
        .filter(Bet.is_group_bet == is_group_bet, Leg.result != "pending")
        .group_by(PropCategory.id)
        .order_by(wins.desc())
        .all()
    )
    return [
        {"name": name, "wins": w, "losses": l, "win_pct": _win_pct(w, l)}
        for name, w, l in rows
    ]


def bettor_scoreboard(is_group_bet):
    """Win/loss record, win%, current streak, and average odds per bettor,
    scoped to group-parlay legs only. Streak is computed in Python (over
    chronologically-ordered results) rather than SQL -- there are only a
    handful of bettors, and a portable streak query is far more code than
    the loop below.
    """
    bettors = Bettor.query.order_by(Bettor.name).all()
    scoreboard = []
    for bettor in bettors:
        legs = (
            db.session.query(Leg)
            .join(Bet, Bet.id == Leg.bet_id)
            .filter(
                Leg.bettor_id == bettor.id,
                Bet.is_group_bet == is_group_bet,
                Leg.result != "pending",
            )
            .order_by(Bet.placed_date, Leg.id)
            .all()
        )
        wins = sum(1 for leg in legs if leg.result == "win")
        losses = sum(1 for leg in legs if leg.result == "loss")
        avg_odds = round(sum(leg.odds for leg in legs) / len(legs)) if legs else None

        streak = 0
        streak_type = None
        for leg in reversed(legs):
            if leg.result == "push":
                continue
            if streak_type is None:
                streak_type = leg.result
                streak = 1
            elif leg.result == streak_type:
                streak += 1
            else:
                break

        scoreboard.append(
            {
                "name": bettor.name,
                "wins": wins,
                "losses": losses,
                "win_pct": _win_pct(wins, losses),
                "avg_odds": avg_odds,
                "streak": f"{'W' if streak_type == 'win' else 'L'}{streak}"
                if streak_type
                else "-",
            }
        )
    return sorted(scoreboard, key=lambda row: row["win_pct"] or -1, reverse=True)


def solo_roi_by_sport_and_type():
    risk = func.sum(Bet.risk_amount)
    profit = func.sum(Bet.profit)

    rows = (
        db.session.query(Bet.sport, BetType.name, risk, profit)
        .join(BetType, BetType.id == Bet.bet_type_id)
        .filter(Bet.is_group_bet.is_(False), Bet.result != "pending")
        .group_by(Bet.sport, BetType.name)
        .order_by(Bet.sport)
        .all()
    )
    results = []
    for sport, bet_type, total_risk, total_profit in rows:
        total_risk = total_risk or Decimal(0)
        total_profit = total_profit or Decimal(0)
        roi = round(100 * total_profit / total_risk, 1) if total_risk else None
        results.append(
            {
                "sport": sport,
                "bet_type": bet_type,
                "risk": total_risk,
                "profit": total_profit,
                "roi": roi,
            }
        )
    return results
