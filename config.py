import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")

METALS = {
    "XAU": "Gold",
    "XAG": "Silver",
}

BASE_URL = "https://www.goldapi.io/api"

def make_api_request(symbol, date=None):
    """Gets metal prices from goldapi"""

    currency = "USD"

    if date:
        url = f"{BASE_URL}/price/{symbol}/{currency}/{date}"
    else:
        url = f"{BASE_URL}/price/{symbol}/{currency}"

    headers = {
        "x-access-token": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching {symbol}: {e}")

        if e.response is not None:
            print(f"Status: {e.response.status_code}")
            print(f"Response: {e.response.text}")

        return None