import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.account import get_all_positions

# Test with account ID 1
account_id = 1
print(f"Testing get_all_positions for account {account_id}...")

try:
    result = get_all_positions(account_id)
    print("Result:")
    print(f"Summary: {result.get('summary')}")
    print(f"Number of positions: {len(result.get('positions', []))}")
    
    # Check first position if available
    if result.get('positions'):
        first_pos = result['positions'][0]
        print("\nFirst position:")
        print(f"Code: {first_pos.get('code')}")
        print(f"Name: {first_pos.get('name')}")
        print(f"NAV: {first_pos.get('nav')}")
        print(f"Latest NAV: {first_pos.get('latest_nav')}")
        print(f"Estimate: {first_pos.get('estimate')}")
        print(f"Day income: {first_pos.get('day_income')}")
        print(f"Day income from NAV: {first_pos.get('day_income_from_nav')}")
        print("\nKeys in position:")
        print(list(first_pos.keys()))
        print("\nHas 'latest_nav' key:", "latest_nav" in first_pos)
        print("Has 'day_income_from_nav' key:", "day_income_from_nav" in first_pos)
        
except Exception as e:
    print(f"Error: {e}")
