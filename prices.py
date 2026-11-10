from config import METALS, make_api_request
from database import get_cached_price, get_latest_cached_price, save_cached_price, get_spot_price_history, get_all_purchases, get_cached_price_checked_at, get_latest_cached_price_checked_at, save_weekend_status
from datetime import date, datetime
from zoneinfo import ZoneInfo


def get_current_prices():
    """Return latest cached price for all metals."""

    today = date.today()
    prices = {}

    for metal in METALS.values():
        prices[metal] = get_latest_cached_price(today, metal)

    return prices


# Maybe add function to get historical prices?

def get_historic_price(metal, purchase_date):
    """Return historic price for the PM on the specified date"""


    symbol = {
        "Gold": "XAU",
        "Silver": "XAG",
    }.get(metal)

    if symbol is None:
        return None

    cached_price = get_cached_price(purchase_date, metal)
    if cached_price is not None:
        return cached_price

    result = make_api_request(symbol, purchase_date)

    if result is None:
        return None

    price = result.get("price")
    if price is None:
        return None

    price = float(price)

    save_cached_price(
        purchase_date,
        metal,
        price,
    )

    return price


def record_daily_spot_prices():
    """ Records daily spot price for Gold and Silver.
    Runs on systemd timer so it records once per day """
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")

    # Sat = 5, Sun = 6
    if today.weekday() >= 5:
        save_weekend_status(today_str)

        print(f"{today_str}: Weekend - No spot price collected")
        return 0, 0

    checked_at = datetime.now(
        ZoneInfo("America/New_York")
    ).isoformat()

    recorded = 0
    failed = 0

    for symbol, metal in METALS.items():

       result = make_api_request(symbol)

       if result is None:
           failed += 1
           continue

       price = result.get("price")

       if price is None:
           failed += 1
           continue

       save_cached_price(today, metal, float(price), checked_at=checked_at, status="Trading Day")

       recorded += 1

    return recorded, failed

def calculate_historical_gains():
    """Calculate daily historical portfolio gain/loss."""

    purchases = get_all_purchases()
    spot_history = get_spot_price_history()

    history = []

    for row in spot_history:
        history_date = row["date"]

        gold_price = row["gold_price"]
        silver_price = row["silver_price"]

        total_cost_basis = 0
        total_current_value = 0

        for purchase in purchases:

            # Don't include purchases that had not happened yet
            if purchase["date"] > history_date:
                continue

            metal = purchase["metal"]

            if metal == "Gold":
                spot_price = gold_price
            elif metal == "Silver":
                spot_price = silver_price
            else:
                continue

            # We can't value this metal on this date
            # if there is no spot price recorded.
            if spot_price is None:
                continue

            quantity = purchase["quantity_oz"]
            cost_basis = purchase["purchase_total"]

            current_value = quantity * spot_price

            total_cost_basis += cost_basis
            total_current_value += current_value

        # Don't create a historical point if there was
        # nothing to value on this date.
        if total_cost_basis == 0:
            continue

        history.append({
            "date": history_date,
            "cost_basis": total_cost_basis,
            "current_value": total_current_value,
            "gain_loss": total_current_value - total_cost_basis,
        })

    return history


def get_current_price_checked_at():
    """Return the timestamp of the price being used by the dashboard."""

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")

    # Weekend: use the most recent trading-day timestamp
    for metal in METALS.values():
        checked_at = get_latest_cached_price_checked_at(
            today_str,
            metal,
        )

        if checked_at is not None:
            return checked_at

    return None

    # Trading day: use today's timestamp
    for metal in METALS.values():
        checked_at = get_cached_price_checked_at(
            today_str,
            metal,
        )

        if checked_at is not None:
            return checked_at

    return None