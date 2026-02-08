from app.services.fund import get_combined_valuation, get_eastmoney_valuation, get_sina_valuation,get_latest_nav

code = "110020"
print(f"Testing valuation for fund {code}...")

# 测试东方财富API
print("\n=== Eastmoney Valuation ===")
eas_data = get_eastmoney_valuation(code)
print(eas_data)

# 测试新浪API
print("\n=== Sina Valuation ===")
sina_data = get_sina_valuation(code)
print(sina_data)

# 测试组合API
print("\n=== Combined Valuation ===")
combined_data = get_combined_valuation(code)
print(combined_data)

print("\n=== latest NAV ===")
latest_nav = get_latest_nav(code)
print(latest_nav)
