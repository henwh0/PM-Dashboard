import sqlite3
from pathlib import Path



DATABASE_FILE = Path("/mnt/portfolio_disk/pm_dashboard/portfolio.db")

def get_connection():
    """Creates connection to sqlite DB"""
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Creates purchase table if it doesn't already exist"""

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            metal TEXT NOT NULL,
            quantity_oz REAL NOT NULL CHECK (quantity_oz > 0),
            purchase_price REAL NOT NULL CHECK (purchase_price >= 0),
            purchase_total REAL NOT NULL CHECK (purchase_total >= 0),
            spot_price_at_purchase REAL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS spot_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            metal TEXT NOT NULL,
            price REAL,
            status TEXT NOT NULL DEFAULT 'Trading Day',
            checked_at TEXT,
            UNIQUE(date, metal)
        )
    """)

    # Add checked_at if the database already existed
    columns = connection.execute(
        "PRAGMA table_info(spot_prices)"
    ).fetchall()

    column_names = [column["name"] for column in columns]

    if "checked_at" not in column_names:
        connection.execute(
            "ALTER TABLE spot_prices ADD COLUMN checked_at TEXT"
        )
    if "status" not in column_names:
        connection.execute(
            """
            ALTER TABLE spot_prices
            ADD COLUMN status TEXT NOT NULL DEFAULT 'Trading Day'
            """
        )


    # Add comments column
    columns = connection.execute(
        "PRAGMA table_info(purchases)"
    ).fetchall()

    column_names = [column["name"] for column in columns]

    if "comments" not in column_names:
        connection.execute(
            "ALTER TABLE purchases ADD COLUMN comments TEXT"
        )


    connection.commit()
    connection.close()



def add_purchase(
    date,
    metal,
    quantity_oz,
    purchase_price,
    purchase_total,
    spot_price_at_purchase=None,
    comments="",
):
    """Add new purchase to database"""
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO purchases (
            date,
            metal,
            quantity_oz,
            purchase_price,
            purchase_total,
            spot_price_at_purchase,
            comments
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            date,
            metal,
            quantity_oz,
            purchase_price,
            purchase_total,
            spot_price_at_purchase,
            comments
        ),
    )
    connection.commit()
    connection.close()


def get_all_purchases():
    """Returns all purchases from the database"""
    connection = get_connection()

    purchases = connection.execute(
        """
        SELECT *
        FROM purchases
        ORDER BY date DESC, id DESC
        """
    ).fetchall()

    connection.close()
    return purchases

def get_holdings():
    connection = get_connection()

    holdings = connection.execute("""
        SELECT
            metal,
            SUM(quantity_oz) AS total_oz,
            SUM(purchase_total) AS total_cost
        FROM purchases
        GROUP BY metal
    """).fetchall()

    connection.close()
    return holdings


def get_all_spot_prices():
    """Returns all historic spot prices"""
    connection = get_connection()

    prices = connection.execute(
        """
        SELECT date, metal, price
        FROM spot_prices
        ORDER BY date DESC, metal ASC
        """
    ).fetchall()

    connection.close()
    return prices


def get_cached_price(date, metal):
    """Return a cached spot price for a specific date and metal"""
    connection = get_connection()

    result = connection.execute(
        """
        SELECT price
        FROM spot_prices
        WHERE date = ? AND metal = ?
        """,
        (date, metal),
    ).fetchone()

    connection.close()

    if result is None:
        return None

    return result["price"]

def get_cached_price_checked_at(date, metal):
    """Return when the cached price was checked."""

    connection = get_connection()

    result = connection.execute(
        """
        SELECT checked_at
        FROM spot_prices
        WHERE date = ? AND metal = ?
        """,
        (date, metal),
    ).fetchone()

    connection.close()

    if result is None:
        return None

    return result["checked_at"]




def save_cached_price(date, metal, price, checked_at=None, status="Trading Day"):
    """Save spot price and the time it was checked. Updates purchases missing spot prices"""

    if price is not None:
        price = round(float(price), 2)

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO spot_prices (
                date,
                metal,
                price,
                status,
                checked_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date, metal)
            DO UPDATE SET
                price = excluded.price,
                status = excluded.status,
                checked_at = excluded.checked_at
            """,
            (date, metal, price, status, checked_at),
        )

        # Update purchases made on this date that lack a spot price
        if price is not None:
            connection.execute(
                """
                UPDATE purchases
                SET spot_price_at_purchase = ?
                WHERE date = ?
                    AND metal = ?
                    AND spot_price_at_purchase IS NULL
                """,
                (float(price), str(date), metal),
            )

        connection.commit()

    finally:
        connection.close()


def get_spot_price_history():
    """Return daily spot prices with Gold and Silver as separate fields."""
    connection = get_connection()

    history = connection.execute(
        """
        SELECT
            date,
            MAX(CASE WHEN metal = 'Gold' THEN price END) AS gold_price,
            MAX(CASE WHEN metal = 'Silver' THEN price END) AS silver_price,
            MAX(status) AS status
        FROM spot_prices
        GROUP BY date
        ORDER BY date DESC
        """
    ).fetchall()

    connection.close()

    return history


def save_weekend_status(date):
    """ Records that the date was a weekend with no spot price collected """
    connection = get_connection()

    for metal in ("Gold", "Silver"):
        connection.execute(
            """
            INSERT INTO spot_prices (
                date,
                metal,
                price,
                status,
                checked_at
            )
            VALUES (?, ?, NULL, 'Weekend', NULL)
            ON CONFLICT(date, metal)
            DO UPDATE SET
                price = NULL,
                status = 'Weekend',
                checked_at = NULL
            """,
            (date, metal),
        )
    connection.commit()
    connection.close()


def get_latest_cached_price(date, metal):
    """Return the most recent available price on or before the specified date."""

    connection = get_connection()

    result = connection.execute(
        """
        SELECT price
        FROM spot_prices
        WHERE date <= ?
          AND metal = ?
          AND price IS NOT NULL
        ORDER BY date DESC
        LIMIT 1
        """,
        (date, metal),
    ).fetchone()

    connection.close()

    if result is None:
        return None

    return result["price"]


def get_latest_cached_price_checked_at(date, metal):
    """Return the checked_at timestamp for the most recent available price."""

    connection = get_connection()

    result = connection.execute(
        """
        SELECT checked_at
        FROM spot_prices
        WHERE date <= ?
          AND metal = ?
          AND price IS NOT NULL
        ORDER BY date DESC
        LIMIT 1
        """,
        (date, metal),
    ).fetchone()

    connection.close()

    if result is None:
        return None

    return result["checked_at"]


def update_purchase_comments(purchase_id, comments):
    """Update comments for an existing purchase."""
    connection = get_connection()

    connection.execute(
        """
        UPDATE purchases
        SET comments = ?
        WHERE id = ?
        """,
        (comments, purchase_id),
    )

    connection.commit()
    connection.close()