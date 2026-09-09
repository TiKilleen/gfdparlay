from datetime import date

from extensions import db

RESULT_VALUES = ("pending", "win", "loss", "push")


class Bettor(db.Model):
    __tablename__ = "bettors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    short_code = db.Column(db.String(20), unique=True, nullable=False)

    def __repr__(self):
        return f"<Bettor {self.short_code}>"


class BetType(db.Model):
    __tablename__ = "bet_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    # Drives the New Bet form's "Group Parlay?" checkbox default -- a real
    # column instead of string-matching on the bet type name at request time.
    default_is_group = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<BetType {self.name}>"


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), unique=True, nullable=False)
    external_id = db.Column(db.String(40), unique=True, nullable=True)
    source = db.Column(db.String(20), nullable=False, default="manual")

    def __repr__(self):
        return f"<Player {self.display_name}>"


class PropCategory(db.Model):
    __tablename__ = "prop_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f"<PropCategory {self.name}>"


class Bet(db.Model):
    __tablename__ = "bets"

    id = db.Column(db.Integer, primary_key=True)
    sport = db.Column(db.String(20), nullable=False)
    bet_type_id = db.Column(db.Integer, db.ForeignKey("bet_types.id"), nullable=False)
    is_group_bet = db.Column(db.Boolean, nullable=False, default=False)
    sportsbook = db.Column(db.String(40), nullable=True)
    placed_date = db.Column(db.Date, nullable=False, default=date.today)
    risk_amount = db.Column(db.Numeric(10, 2), nullable=False)
    to_win_amount = db.Column(db.Numeric(10, 2), nullable=True)
    # Sportsbooks apply odds boosts/promos that don't match straight odds
    # math -- when set, this is what actually gets paid out on a win,
    # overriding the odds-derived to_win_amount above (which stays intact
    # as the "what plain math says" reference figure).
    to_win_override = db.Column(db.Numeric(10, 2), nullable=True)
    profit = db.Column(db.Numeric(10, 2), nullable=True)
    result = db.Column(db.String(10), nullable=False, default="pending")
    notes = db.Column(db.Text, nullable=True)
    is_parlay = db.Column(db.Boolean, nullable=False, default=False)

    bet_type = db.relationship("BetType")
    legs = db.relationship(
        "Leg", backref="bet", cascade="all, delete-orphan", order_by="Leg.id"
    )


class Leg(db.Model):
    __tablename__ = "legs"

    id = db.Column(db.Integer, primary_key=True)
    bet_id = db.Column(db.Integer, db.ForeignKey("bets.id"), nullable=False)
    bettor_id = db.Column(db.Integer, db.ForeignKey("bettors.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=True)
    prop_category_id = db.Column(
        db.Integer, db.ForeignKey("prop_categories.id"), nullable=False
    )
    description = db.Column(db.String(200), nullable=False)
    odds = db.Column(db.Integer, nullable=False)
    result = db.Column(db.String(10), nullable=False, default="pending")

    bettor = db.relationship("Bettor")
    player = db.relationship("Player")
    prop_category = db.relationship("PropCategory")
