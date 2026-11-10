import streamlit as st
import pandas as pd
from database import(
    initialize_database,
    add_purchase,
    get_all_purchases,
    get_spot_price_history,
    update_purchase_comments,
)
from prices import get_current_prices, get_historic_price, calculate_historical_gains, get_current_price_checked_at
from datetime import datetime
from zoneinfo import ZoneInfo



###### PAGE CONFIG ######

st.set_page_config(
    page_title="Precious Metals Dashboard",
    page_icon="💰",
    layout="wide",
)

###### INITIALIZE DB ######

initialize_database()



###### HELPERS ######

def calculate_portfolio(purchases, current_prices):
    """Calculate totals by metal"""
    portfolio = {}

    for purchase in purchases:
        metal = purchase["metal"]

        if metal not in portfolio:
            portfolio[metal] = {
                "quantity_oz": 0,
                "cost_basis": 0,
            }

        portfolio[metal]["quantity_oz"] += purchase["quantity_oz"]
        portfolio[metal]["cost_basis"] += purchase["purchase_total"]

    for metal, data in portfolio.items():
        spot_price = current_prices.get(metal)

        data["spot_price"] = spot_price

        if spot_price is not None:
            data["current_value"] = data["quantity_oz"] * spot_price
            data["unrealized_gain"] = (
                data["current_value"] - data["cost_basis"]
            )
        else:
            data["current_value"] = None
            data["unrealized_gain"] = None

    return portfolio




###### LOAD DATA ######
purchases = get_all_purchases()
current_prices = get_current_prices()
checked_at = get_current_price_checked_at()

#current_prices = {
#    "Gold": None,
#    "Silver": None,
#}

portfolio = calculate_portfolio(purchases, current_prices)


###### HEADER ######
st.title("💰 Precious Metals Portfolio")
st.caption("Gold and Silver holdings")



###### CURRENT PRICES #######
st.header("Current Prices")

price_columns = st.columns(len(current_prices))

for column, (metal, price) in zip(price_columns, current_prices.items()):
    with column:
        if price is not None:
            st.metric(
                label=f"{metal} Spot",
                value=f"${price:,.2f}/oz",
            )

            if checked_at:
                checked_at_dt = datetime.fromisoformat(checked_at)

                if datetime.now(ZoneInfo("America/New_York")).weekday() >= 5:
                    st.caption(
                        f"Prices from: {checked_at_dt.strftime('%b %d, %Y at %I:%M:%S %p ET')}"
                    )
                else:
                    st.caption(
                        f"Checked: {checked_at_dt.strftime('%b %d, %Y at %I:%M:%S %p ET')}"
                    )
            else:
                st.caption("Price Timestamp: Unknown")
        else:
            st.metric(
                label=f"{metal} Spot",
                value="Unavailable",
            )



###### PORTFOLIO SUMMARY ######
st.header("Portfolio")

if not portfolio:
    st.info("No purchases have been added yet")
else:
    total_cost = sum(
        data["cost_basis"]
        for data in portfolio.values()
    )

    total_value = sum(
        data["current_value"]
        for data in portfolio.values()
        if data["current_value"] is not None
    )

    all_prices_available = all(
        data["current_value"] is not None
        for data in portfolio.values()
    )
    if all_prices_available:
        total_value = sum(
            data["current_value"]
            for data in portfolio.values()
        )

        total_gain = total_value - total_cost
    else:
        total_gain = None
        total_value = None


    summary_columns = st.columns(3)

    with summary_columns[0]:
        st.metric(
            "Cost Basis",
            f"${total_cost:,.2f}",
        )

    with summary_columns[1]:
        if total_value is not None:
            st.metric(
                "Current Value",
                f"${total_value:,.2f}",
            )
        else:
            st.metric(
                "Current Value",
                "Unavailable",
            )

    with summary_columns[2]:
        if total_gain is not None:
            st.metric(
                "Unrealized Gain/Loss",
                f"${total_gain:,.2f}",
                delta=f"${total_gain:,.2f}",
            )
        else:
            st.metric(
                "Unrealized Gain/Loss",
                "Unavailable",
            )


###### HOLDINGS BY METAL TYPE ######
if portfolio:
    st.subheader("Holdings")

    for metal, data in portfolio.items():
        columns = st.columns(4)

        with columns[0]:
            st.metric(
                metal,
                f"{data['quantity_oz']:,.4f} oz",
            )

        with columns[1]:
            st.metric(
                "Cost Basis",
                f"${data['cost_basis']:,.2f}",
            )

        with columns[2]:
            if data["spot_price"] is not None:
              st.metric(
                    "Spot Price",
                    f"${data['spot_price']:,.2f}/oz",
                )
            else:
                st.metric(
                    "Spot Price",
                    "Unavailable",
                )

        with columns[3]:
            if data["current_value"] is not None:
                st.metric(
                    "Current Value",
                    f"${data['current_value']:,.2f}",
                )
            else:
                st.metric(
                    "Current Value",
                    "Unavailable",
                )


###### ADD PURCHASE ######
st.header("Add Purchase")
with st.form("Purchase Form"):
    date = st.date_input("Purchase Date")

    metal = st.selectbox(
    "Metal",
    ["Gold", "Silver"],
)

    quantity_oz = st.number_input(
        "Quantity (oz)",
        min_value=0.0001,
        step=0.01,
        format="%.4f",
    )

    purchase_price = st.number_input(
        "Purchase Price ($/oz)",
        min_value=0.0,
        step=1.00,
        format="%.2f",
    )

    purchase_total = st.number_input(
        "Total Cost Including Premiums/Fees ($)",
        min_value=0.0,
        step=1.00,
        format="%.2f",
    )

    comments = st.text_area(
        "Comments (Optional)",
        placeholder="Dealer, website, coin type, condition, or other notes.."
    )

    submitted = st.form_submit_button(
        "Add Purchase",
        type="primary",
    )

if submitted:
    if purchase_total < 0:
        st.error("Purchase total must be zero or greater.")

    elif purchase_price < 0:
        st.error("Purchase price must be zero or greater.")

    else:
        purchase_date = date.strftime("%Y-%m-%d")
        historical_spot = get_historic_price(metal, purchase_date)

        add_purchase(
            date=purchase_date,
            metal=metal,
            quantity_oz=quantity_oz,
            purchase_price=purchase_price,
            purchase_total=purchase_total,
            spot_price_at_purchase=historical_spot,
            comments=comments
        )

        if historical_spot is not None:
            st.success(
                f"Purchase added. "
                f"{metal} spot price on {purchase_date}: "
                f"${historical_spot:,.2f}/oz"
            )
        else:
            st.warning("Purchase added, but historical spot could not be retrieved.")
        st.rerun()


###### HISTORIC SPOT PRICES ######
st.header("Spot Price History")

spot_history = get_spot_price_history()

if spot_history:

    history_data = []

    for row in spot_history:

        if row["status"] == "Weekend":
            gold_spot = "Weekend"
            silver_spot = "Weekend"

        else:
            gold_spot = (
                f"${row['gold_price']:,.2f}/oz"
                if row["gold_price"] is not None
                else "Unavailable"
            )

            silver_spot = (
                f"${row['silver_price']:,.2f}/oz"
                if row["silver_price"] is not None
                else "Unavailable"
            )

        history_data.append({
            "Date": row["date"],
            "Status": row["status"],
            "Gold Spot": gold_spot,
            "Silver Spot": silver_spot,
        })

    st.dataframe(
        history_data,
        width="stretch",
        hide_index=True,
    )

else:
    st.info("No historical spot prices have been recorded yet.")


###### SPOT HISTORY GRAPHS######
st.header("Spot Graph")

spot_graph_history = get_spot_price_history()

if spot_graph_history:

    chart_data = []

    for row in spot_graph_history:

        #Skips Weekends
        if row["status"] == "Weekend":
            continue

        chart_data.append({
            "Date": row["date"],
            "Gold Spot": row["gold_price"],
            "Silver Spot": row["silver_price"],
        })

    if chart_data:
        df = pd.DataFrame(chart_data)

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")
        df = df.set_index("Date")


        # GOLD GRAPH
        st.subheader("Gold Spot Price History")

        gold_data = df[["Gold Spot"]].dropna()
        if not gold_data.empty:
            st.line_chart(
                gold_data,
                y_label="Price ($/oz)",
                color="#FFD700",
            )
        else:
            st.info("No gold spot price data is available to graph.")

        # SILVER GRAPH
        st.subheader("Silver Spot Price History")

        silver_data = df[["Silver Spot"]].dropna()

        if not silver_data.empty:
            st.line_chart(
                silver_data,
                y_label="Price ($/oz)",
                color="#C0C0C0",
            )
        else:
            st.info("No silver spot price data is available to graph.")

    else:
        st.info("No spot price data is available to graph.")

else:
    st.info("No historical spot prices have been recorded yet.")



###### HISTORICAL GAINS ######
st.header("Historical Gains")

historical_gains = calculate_historical_gains()

if historical_gains:

    df = pd.DataFrame(historical_gains)

    df = df.rename(columns={"date": "Date"})

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
    df = df.set_index("Date")

    # PORTFOLIO GAIN / LOSS GRAPH
    st.subheader("Historical Portfolio Gain / Loss")

    gains_data = df[["gain_loss"]].dropna()
    gains_data.columns = ["Portfolio Gain / Loss"]

    if not gains_data.empty:
        st.line_chart(
            gains_data,
            y_label="Gain / Loss ($)",
            color="#2E8B57",
        )
    else:
        st.info("No historical gains or losses are available to graph.")

    # CURRENT PORTFOLIO VALUE GRAPH
    st.subheader("Historical Portfolio Value")

    value_data = df[["current_value"]].dropna()
    value_data.columns = ["Portfolio Value"]

    if not value_data.empty:
        st.line_chart(
            value_data,
            y_label="Value ($)",
            color="#4169E1",
        )
    else:
        st.info("No historical portfolio value is available to graph.")

else:
    st.info("No historical gains have been recorded yet.")


###### PURCHASE HISTORY ######
st.header("Purchase History")

if purchases:
    purchase_data = []

    for purchase in purchases:
        purchase_data.append({
            "Date": purchase["date"],
            "Metal": purchase["metal"],
            "Quantity (oz)": purchase["quantity_oz"],
            "Price / oz": purchase["purchase_price"],
            "Total": purchase["purchase_total"],
            "Spot at Purchase": purchase["spot_price_at_purchase"],
            "Comments": purchase["comments"] or "",
        })

    st.dataframe(
        purchase_data,
        width= 'stretch',
        hide_index=True,
    )
else:
    st.info("Your purchase history will appear here")