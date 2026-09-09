from decimal import Decimal, ROUND_HALF_UP


def american_to_decimal(odds):
    odds = Decimal(odds)
    if odds > 0:
        return Decimal(1) + odds / Decimal(100)
    return Decimal(1) + Decimal(100) / abs(odds)


def combined_decimal_odds(american_odds_list):
    combined = Decimal(1)
    for odds in american_odds_list:
        combined *= american_to_decimal(odds)
    return combined


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_bet_outcome(bet):
    """Derive (result, profit) for a Bet from its legs' results and stake.

    Mirrors standard sportsbook parlay rules: any losing leg loses the whole
    bet; push legs are dropped and odds recombined over the remaining legs;
    if every leg pushes, the whole bet pushes (stake returned).
    """
    risk = Decimal(bet.risk_amount)

    if not bet.is_parlay:
        leg = bet.legs[0]
        if leg.result == "pending":
            return "pending", None
        if leg.result == "loss":
            return "loss", money(-risk)
        if leg.result == "push":
            return "push", money(0)
        decimal_odds = american_to_decimal(leg.odds)
        return "win", money(risk * (decimal_odds - 1))

    leg_results = [leg.result for leg in bet.legs]
    if "pending" in leg_results:
        return "pending", None
    if "loss" in leg_results:
        return "loss", money(-risk)

    winning_legs = [leg for leg in bet.legs if leg.result == "win"]
    if not winning_legs:
        return "push", money(0)

    combined = combined_decimal_odds(leg.odds for leg in winning_legs)
    return "win", money(risk * (combined - 1))
