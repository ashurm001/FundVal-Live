import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.fund import get_combined_valuation

# Test with fund code 110020
fund_code = "110020"
print(f"Testing get_combined_valuation for fund {fund_code}...")

try:
    result = get_combined_valuation(fund_code)
    print("Result:")
    print(result)
    print("\nKeys in result:")
    print(list(result.keys()))
    print("\nHas 'latest_nav' key:", "latest_nav" in result)
    if "latest_nav" in result:
        print(f"Latest NAV: {result['latest_nav']}")
    if "nav" in result:
        print(f"Previous day NAV: {result['nav']}")
except Exception as e:
    print(f"Error: {e}")
