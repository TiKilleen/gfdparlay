"""Query helpers backing the two dashboard sections: Group Parlay Analysis
(is_group_bet-scoped, about the friend group's picks) and My Overall
Performance (Tim's own money and picks across everything, group parlays
included). Most functions take an optional `sport` filter (None = all
sports); a couple take an optional `bet_type_id` filter too. None of these
group by bet type -- bet type is purely a filter dimension, sport is the
only thing rows ever get broken out by.
"""

from decimal import Decimal

from sqlalchemy import case, func

from extensions import db
from models import Bet, BetType, Bettor, Leg, Player, PropCategory


def _win_pct(wins, losses):
    decided = wins + losses
    return round(100 * wins / decided, 1) if decided else None


def distinct_sports():
    rows = db.session.query(Bet.sport).distinct().order_by(Bet.sport).all()
    return [row[0] for row in rows]


def player_leaderboard(is_group_bet, sport=None):
    wins = func.sum(case((Leg.result == "win", 1), else_=0))
    losses = func.sum(case((Leg.result == "loss", 1), else_=0))
    pushes = func.sum(case((Leg.result == "push", 1), else_=0))

    query = (
        db.session.query(Player.display_name, wins, losses, pushes)
        .join(Leg, Leg.player_id == Player.id)
        .join(Bet, Bet.id == Leg.bet_id)
        .filter(Bet.is_group_bet == is_group_bet, Leg.result != "pending")
    )
    if sport:
        query = query.filter(Bet.sport == sport)

    rows = query.group_by(Player.id).order_by(wins.desc()).all()
    return [
        {"name": name, "wins": w, "losses": l, "pushes": p, "win_pct": _win_pct(w, l)}
        for name, w, l, p in rows
    ]


def category_breakdown(is_group_bet, sport=None):
    wins = func.sum(case((Leg.result == "win", 1), else_=0))
    losses = func.sum(case((Leg.result == "loss", 1), else_=0))

    query = (
        db.session.query(PropCategory.name, wins, losses)
        .join(Leg, Leg.prop_category_id == PropCategory.id)
        .join(Bet, Bet.id == Leg.bet_id)
        .filter(Bet.is_group_bet == is_group_bet, Leg.result != "pending")
    )
    if sport:
        query = query.filter(Bet.sport == sport)

    rows = query.group_by(PropCategory.id).order_by(wins.desc()).all()
    return [
        {"name": name, "wins": w, "losses": l, "win_pct": _win_pct(w, l)}
        for name, w, l in rows
    ]


def bettor_scoreboard(is_group_bet, sport=None, bet_type_id=None):
    """Win/loss record, win%, current streak, and average odds per bettor,
    scoped to group-parlay legs only. Streak is computed in Python (over
    chronologically-ordered results) rather than SQL -- there are only a
    handful of bettors, and a portable streak query is far more code than
    the loop below.
    """
    bettors = Bettor.query.order_by(Bettor.name).all()
    scoreboard = []
    for bettor in bettors:
        query = (
            db.session.query(Leg)
            .join(Bet, Bet.id == Leg.bet_id)
            .filter(
                Leg.bettor_id == bettor.id,
                Bet.is_group_bet == is_group_bet,
                Leg.result != "pending",
            )
        )
        if sport:
            query = query.filter(Bet.sport == sport)
        if bet_type_id:
            query = query.filter(Bet.bet_type_id == bet_type_id)

        legs = query.order_by(Bet.placed_date, Leg.id).all()
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

        # Longest winning run to date -- pushes are no-decisions and don't
        # break a run, same as the current-streak logic above.
        longest_win_streak = 0
        run = 0
        for leg in legs:
            if leg.result == "push":
                continue
            if leg.result == "win":
                run += 1
                longest_win_streak = max(longest_win_streak, run)
            else:
                run = 0

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
                "longest_streak": f"W{longest_win_streak}" if longest_win_streak else "-",
            }
        )
    return sorted(scoreboard, key=lambda row: row["win_pct"] or -1, reverse=True)


def overall_roi_by_sport_and_type(sport=None, bet_type_id=None):
    """Money is tracked per-bet, not per-leg -- Tim carries the full stake
    and profit of a group parlay just like a solo bet (there's no separate
    concept of "whose money" a leg represents), so this covers every bet,
    group parlays included.

    Always groups by sport only, one row each. bet_type_id narrows which
    bets get counted but never splits a sport into multiple rows -- the
    default (no bet_type_id) rolls every bet type together per sport,
    displayed as "All" by the caller.
    """
    risk = func.sum(Bet.risk_amount)
    profit = func.sum(Bet.profit)

    query = db.session.query(Bet.sport, risk, profit).filter(Bet.result != "pending")
    if sport:
        query = query.filter(Bet.sport == sport)
    if bet_type_id:
        query = query.filter(Bet.bet_type_id == bet_type_id)

    rows = query.group_by(Bet.sport).order_by(Bet.sport).all()

    if bet_type_id:
        bet_type_label = BetType.query.get(bet_type_id).name
    else:
        bet_type_label = "All"

    results = []
    for sport_name, total_risk, total_profit in rows:
        total_risk = total_risk or Decimal(0)
        total_profit = total_profit or Decimal(0)
        roi = round(100 * total_profit / total_risk, 1) if total_risk else None
        results.append(
            {
                "sport": sport_name,
                "bet_type": bet_type_label,
                "risk": total_risk,
                "profit": total_profit,
                "roi": roi,
            }
        )
    return results


def roi_total(rows):
    """Sums the rows from overall_roi_by_sport_and_type() into one grand
    total -- kept as a separate step rather than a SQL-side grand total so
    the per-row and total figures can never drift out of sync with each
    other.
    """
    total_risk = sum((row["risk"] for row in rows), Decimal(0))
    total_profit = sum((row["profit"] for row in rows), Decimal(0))
    roi = round(100 * total_profit / total_risk, 1) if total_risk else None
    return {"risk": total_risk, "profit": total_profit, "roi": roi}


def bet_category_breakdown_by_bettor(bettor_id, sport=None):
    """Prop-category win% for one specific bettor's own leg picks -- unlike
    category_breakdown(is_group_bet), this filters by bettor, not by
    whether the bet was a group parlay, so it covers that person's solo
    bets *and* their own leg within each group parlay, but never a
    teammate's leg.
    """
    wins = func.sum(case((Leg.result == "win", 1), else_=0))
    losses = func.sum(case((Leg.result == "loss", 1), else_=0))

    query = (
        db.session.query(PropCategory.name, wins, losses)
        .join(Leg, Leg.prop_category_id == PropCategory.id)
        .join(Bet, Bet.id == Leg.bet_id)
        .filter(Leg.bettor_id == bettor_id, Leg.result != "pending")
    )
    if sport:
        query = query.filter(Bet.sport == sport)

    rows = query.group_by(PropCategory.id).order_by(wins.desc()).all()
    return [
        {"name": name, "wins": w, "losses": l, "win_pct": _win_pct(w, l)}
        for name, w, l in rows
    ]
