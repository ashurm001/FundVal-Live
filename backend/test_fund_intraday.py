import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.fund import get_fund_intraday

# Test with fund code 110020
fund_code = "110020"
print(f"Testing get_fund_intraday for fund {fund_code}...")

try:
    result = get_fund_intraday(fund_code)
    print("Result:")
    print(f"ID: {result.get('id')}")
    print(f"Name: {result.get('name')}")
    print(f"Type: {result.get('type')}")
    print(f"Manager: {result.get('manager')}")
    print(f"Previous day NAV: {result.get('nav')}")
    print(f"Latest NAV: {result.get('latest_nav')}")
    print(f"Estimate: {result.get('estimate')}")
    print(f"Estimate Rate: {result.get('estRate')}")
    print(f"Update Time: {result.get('time')}")
    print("\nKeys in result:")
    print(list(result.keys()))
    print("\nHas 'latest_nav' key:", "latest_nav" in result)
except Exception as e:
    print(f"Error: {e}")
