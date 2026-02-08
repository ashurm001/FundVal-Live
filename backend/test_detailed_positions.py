import requests

# Test the account positions API
url = "http://localhost:21345/api/account/positions?account_id=1"

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        if 'positions' in data and len(data['positions']) > 0:
            first_pos = data['positions'][0]
            print("\nFirst Position (招商产业债券A - 217022):")
            print(f"Code: {first_pos.get('code')}")
            print(f"Name: {first_pos.get('name')}")
            print(f"Shares: {first_pos.get('shares')}")
            print(f"Cost: {first_pos.get('cost')}")
            print(f"NAV (前一日净值): {first_pos.get('nav')}")
            print(f"Latest NAV (当日净值): {first_pos.get('latest_nav')}")
            print(f"Estimate (估值): {first_pos.get('estimate')}")
            print(f"Day Income (预估收益): {first_pos.get('day_income')}")
            print(f"Day Income from NAV (当日收益): {first_pos.get('day_income_from_nav')}")
            
            # 计算验证
            shares = first_pos.get('shares')
            nav = first_pos.get('nav')
            latest_nav = first_pos.get('latest_nav')
            estimate = first_pos.get('estimate')
            
            print("\n计算验证:")
            print(f"预估收益计算: ({estimate} - {nav}) * {shares} = {(estimate - nav) * shares}")
            print(f"当日收益计算: ({latest_nav} - {nav}) * {shares} = {(latest_nav - nav) * shares}")
            
            # 查找基金 110020 的数据
            print("\n查找基金 110020 (易方达沪深300ETF联接A) 的数据:")
            for pos in data['positions']:
                if pos.get('code') == '110020':
                    print(f"Code: {pos.get('code')}")
                    print(f"Name: {pos.get('name')}")
                    print(f"Shares: {pos.get('shares')}")
                    print(f"Cost: {pos.get('cost')}")
                    print(f"NAV (前一日净值): {pos.get('nav')}")
                    print(f"Latest NAV (当日净值): {pos.get('latest_nav')}")
                    print(f"Estimate (估值): {pos.get('estimate')}")
                    print(f"Day Income (预估收益): {pos.get('day_income')}")
                    print(f"Day Income from NAV (当日收益): {pos.get('day_income_from_nav')}")
                    
                    # 计算验证
                    shares = pos.get('shares')
                    nav = pos.get('nav')
                    latest_nav = pos.get('latest_nav')
                    estimate = pos.get('estimate')
                    
                    print("\n计算验证:")
                    print(f"预估收益计算: ({estimate} - {nav}) * {shares} = {(estimate - nav) * shares}")
                    print(f"当日收益计算: ({latest_nav} - {nav}) * {shares} = {(latest_nav - nav) * shares}")
                    break
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error: {e}")
