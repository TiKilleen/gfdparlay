from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Flask, abort, redirect, render_template, request, url_for
from flask_migrate import Migrate

import analytics
import config
from extensions import db
from models import Bet, BetType, Bettor, Leg, Player, PropCategory, RESULT_VALUES
from odds import combined_decimal_odds, compute_bet_outcome, money

migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)
    migrate.init_app(app, db)

    @app.template_filter("money")
    def money_filter(value):
        if value is None:
            return "-"
        return f"-${-value:.2f}" if value < 0 else f"${value:.2f}"

    register_routes(app)
    return app


def get_or_create_player(name):
    name = name.strip()
    if not name:
        return None
    player = Player.query.filter(func_lower_eq(Player.display_name, name)).first()
    if player:
        return player
    player = Player(display_name=name, source="manual")
    db.session.add(player)
    db.session.flush()
    return player


def get_or_create_prop_category(name):
    name = name.strip()
    category = PropCategory.query.filter(func_lower_eq(PropCategory.name, name)).first()
    if category:
        return category
    category = PropCategory(name=name)
    db.session.add(category)
    db.session.flush()
    return category


def func_lower_eq(column, value):
    return db.func.lower(column) == value.lower()


def parse_optional_decimal(raw_value):
    if raw_value is None or not raw_value.strip():
        return None
    return Decimal(raw_value)


def register_routes(app):
    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def dashboard():
        pending_bets = (
            Bet.query.filter_by(result="pending")
            .order_by(Bet.placed_date)
            .all()
        )
        return render_template(
            "dashboard.html",
            pending_bets=pending_bets,
            group_players=analytics.player_leaderboard(is_group_bet=True),
            group_bettors=analytics.bettor_scoreboard(is_group_bet=True),
            group_categories=analytics.category_breakdown(is_group_bet=True),
            solo_categories=analytics.category_breakdown(is_group_bet=False),
            solo_roi=analytics.solo_roi_by_sport_and_type(),
        )

    @app.get("/bets")
    def bets_list():
        scope = request.args.get("scope", "all")
        status = request.args.get("status", "all")

        query = Bet.query
        if scope == "group":
            query = query.filter(Bet.is_group_bet.is_(True))
        elif scope == "solo":
            query = query.filter(Bet.is_group_bet.is_(False))
        if status == "pending":
            query = query.filter(Bet.result == "pending")
        elif status == "graded":
            query = query.filter(Bet.result != "pending")

        bets = query.order_by(Bet.placed_date.desc(), Bet.id.desc()).all()
        return render_template("bets_list.html", bets=bets, scope=scope, status=status)

    @app.route("/bets/new", methods=["GET", "POST"])
    def bets_new():
        if request.method == "GET":
            return render_template(
                "bets_form.html",
                bet_types=BetType.query.order_by(BetType.name).all(),
                bettors=Bettor.query.order_by(Bettor.name).all(),
                player_names=[p.display_name for p in Player.query.all()],
                category_names=[c.name for c in PropCategory.query.all()],
                today=date.today().isoformat(),
            )

        form = request.form
        try:
            bet_type_id = int(form["bet_type_id"])
            placed_date = date.fromisoformat(form["placed_date"])
            risk_amount = Decimal(form["risk_amount"])
            to_win_override = parse_optional_decimal(form.get("to_win_override"))
        except (KeyError, ValueError, InvalidOperation):
            abort(400, "Missing or invalid bet fields")

        bettor_ids = request.form.getlist("leg_bettor_id")
        player_names = request.form.getlist("leg_player_name")
        category_names = request.form.getlist("leg_prop_category")
        descriptions = request.form.getlist("leg_description")
        odds_values = request.form.getlist("leg_odds")

        if not bettor_ids:
            abort(400, "A bet needs at least one leg")

        bet = Bet(
            sport=form["sport"],
            bet_type_id=bet_type_id,
            is_group_bet="is_group_bet" in form,
            sportsbook=form.get("sportsbook") or None,
            placed_date=placed_date,
            risk_amount=risk_amount,
            notes=form.get("notes") or None,
            is_parlay=len(bettor_ids) > 1,
            to_win_override=to_win_override,
        )

        leg_odds = []
        for i in range(len(bettor_ids)):
            odds_int = int(odds_values[i])
            leg_odds.append(odds_int)
            bet.legs.append(
                Leg(
                    bettor_id=int(bettor_ids[i]),
                    player=get_or_create_player(player_names[i]),
                    prop_category=get_or_create_prop_category(category_names[i]),
                    description=descriptions[i].strip(),
                    odds=odds_int,
                )
            )

        combined = combined_decimal_odds(leg_odds)
        bet.to_win_amount = money(risk_amount * (combined - 1))

        db.session.add(bet)
        db.session.commit()
        return redirect(url_for("bet_detail", bet_id=bet.id))

    @app.get("/bets/<int:bet_id>")
    def bet_detail(bet_id):
        bet = Bet.query.get_or_404(bet_id)
        return render_template("bets_detail.html", bet=bet, result_values=RESULT_VALUES)

    @app.post("/bets/<int:bet_id>/grade")
    def bet_grade(bet_id):
        bet = Bet.query.get_or_404(bet_id)
        for leg in bet.legs:
            result = request.form.get(f"leg_result_{leg.id}")
            if result in RESULT_VALUES:
                leg.result = result

        bet.result, bet.profit = compute_bet_outcome(bet)
        db.session.commit()
        return redirect(url_for("bet_detail", bet_id=bet.id))

    @app.post("/bets/<int:bet_id>/override")
    def bet_override(bet_id):
        bet = Bet.query.get_or_404(bet_id)
        try:
            bet.to_win_override = parse_optional_decimal(request.form.get("to_win_override"))
        except InvalidOperation:
            abort(400, "Invalid override amount")

        # A pending bet has no result yet to recompute; a graded one needs
        # its stored profit refreshed immediately so it reflects the new
        # override rather than waiting for a re-grade that may never happen.
        if bet.result != "pending":
            bet.result, bet.profit = compute_bet_outcome(bet)
        db.session.commit()
        return redirect(url_for("bet_detail", bet_id=bet.id))

    @app.route("/bettors", methods=["GET", "POST"])
    def bettors_page():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            short_code = request.form.get("short_code", "").strip().upper()
            if name and short_code:
                db.session.add(Bettor(name=name, short_code=short_code))
                db.session.commit()
            return redirect(url_for("bettors_page"))
        return render_template(
            "bettors.html", bettors=Bettor.query.order_by(Bettor.name).all()
        )

    @app.route("/bet-types", methods=["GET", "POST"])
    def bet_types_page():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            default_is_group = "default_is_group" in request.form
            if name:
                db.session.add(BetType(name=name, default_is_group=default_is_group))
                db.session.commit()
            return redirect(url_for("bet_types_page"))
        return render_template(
            "bet_types.html", bet_types=BetType.query.order_by(BetType.name).all()
        )

    @app.route("/players", methods=["GET", "POST"])
    def players_page():
        if request.method == "POST":
            name = request.form.get("display_name", "").strip()
            if name:
                get_or_create_player(name)
                db.session.commit()
            return redirect(url_for("players_page"))
        return render_template(
            "players.html", players=Player.query.order_by(Player.display_name).all()
        )


app = create_app()

if __name__ == "__main__":
    import os

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
