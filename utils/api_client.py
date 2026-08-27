import requests
from config.environment import Config

HEADERS = {
    "X-API-Key": Config.ACCOUNTING_API_KEY,
    "Content-Type": "application/json"
}

def get_partners():
    """Fetches the valid partners from the mock accounting API."""
    try:
        response = requests.get(f"{Config.ACCOUNTING_API_URL}/partners", headers=HEADERS)
        if response.status_code == 200:
            return response.json()["data"]["partners"]
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the Accounting API. Is accounting_api.py running?")
    return []

def submit_invoice(invoice_data: dict):
    """Submits the extracted JSON payload to the mock accounting API."""
    try:
        response = requests.post(
            f"{Config.ACCOUNTING_API_URL}/invoices",
            headers=HEADERS,
            json=invoice_data,
            timeout=30,
        )
    except requests.exceptions.RequestException as error:
        print(f"❌ Could not submit invoice: {error}")
        return False
    
    if response.status_code == 201:
        print("✅ Successfully registered invoice in Accounting System!")
        print(response.json())
        return True
    else:
        print(f"❌ Failed to register invoice. Status code: {response.status_code}")
        print(response.json())
        return False