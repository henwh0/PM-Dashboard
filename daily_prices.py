from database import initialize_database
from prices import record_daily_spot_prices


initialize_database()

recorded, failed = record_daily_spot_prices()

print(f"Prices recorded: {recorded}")
print(f"Prices failed: {failed}")
