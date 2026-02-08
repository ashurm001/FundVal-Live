import requests

# Test the account positions API
url = "http://localhost:21345/api/account/positions?account_id=1"

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\nResponse Keys:")
        print(list(data.keys()))
        
        if 'positions' in data and len(data['positions']) > 0:
            first_pos = data['positions'][0]
            print("\nFirst Position Keys:")
            print(list(first_pos.keys()))
            
            print("\nFirst Position Data:")
            print(f"Code: {first_pos.get('code')}")
            print(f"Name: {first_pos.get('name')}")
            print(f"Cost: {first_pos.get('cost')}")
            print(f"Shares: {first_pos.get('shares')}")
            print(f"NAV: {first_pos.get('nav')}")
            print(f"Latest NAV: {first_pos.get('latest_nav')}")
            print(f"Estimate: {first_pos.get('estimate')}")
            print(f"Day Income: {first_pos.get('day_income')}")
            print(f"Day Income from NAV: {first_pos.get('day_income_from_nav')}")
            print(f"Total Income: {first_pos.get('total_income')}")
            
            # Calculate expected total income
            cost = first_pos.get('cost')
            shares = first_pos.get('shares')
            latest_nav = first_pos.get('latest_nav')
            expected_total_income = (latest_nav - cost) * shares if latest_nav else 0
            print(f"Expected Total Income: ({latest_nav} - {cost}) * {shares} = {expected_total_income}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error: {e}")
