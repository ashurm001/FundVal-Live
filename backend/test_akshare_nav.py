import akshare as ak

# 测试使用 AkShare 获取基金最新净值
def get_latest_nav(code):
    """
    使用 AkShare 获取基金最新净值
    """
    try:
        # 获取单位净值走势
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        
        if df is not None and not df.empty:
            # 按日期排序，取最新两条记录
            df_sorted = df.sort_values(by="净值日期", ascending=False)
            
            if len(df_sorted) >= 1:
                latest_row = df_sorted.iloc[0]
                latest_date = latest_row["净值日期"]
                latest_nav = float(latest_row["单位净值"])
                
                # 获取前一日净值
                previous_nav = None
                if len(df_sorted) >= 2:
                    previous_row = df_sorted.iloc[1]
                    previous_nav = float(previous_row["单位净值"])
                
                return {
                    "latest_date": latest_date,
                    "latest_nav": latest_nav,
                    "previous_nav": previous_nav
                }
        
    except Exception as e:
        print(f"Error getting NAV for {code}: {e}")
    
    return None

# 测试函数
if __name__ == "__main__":
    code = "110020"
    result = get_latest_nav(code)
    print(f"Fund {code}:")
    print(result)
