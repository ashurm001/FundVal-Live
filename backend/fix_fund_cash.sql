-- 修复基金AI账户的CASH持仓
-- 为现有的基金AI账户添加缺失的CASH持仓记录

-- 先查看哪些账户缺少CASH持仓
SELECT 
    a.id as ai_account_id,
    a.name,
    a.initial_capital,
    a.current_value,
    COALESCE(SUM(p.market_value), 0) as positions_value,
    a.initial_capital - COALESCE(SUM(p.market_value), 0) as expected_cash
FROM ai_simulation_accounts a
LEFT JOIN ai_simulation_positions p ON a.id = p.ai_account_id AND p.code != 'CASH'
WHERE a.source_type = 'fund'
GROUP BY a.id
HAVING NOT EXISTS (
    SELECT 1 FROM ai_simulation_positions p2 
    WHERE p2.ai_account_id = a.id AND p2.code = 'CASH'
);

-- 为缺少CASH持仓的账户添加CASH持仓
INSERT INTO ai_simulation_positions 
(ai_account_id, code, name, asset_type, cost, shares, current_price, market_value, updated_at)
SELECT 
    a.id, 
    'CASH', 
    '现金', 
    'cash', 
    1.0, 
    a.initial_capital - COALESCE((
        SELECT SUM(p2.market_value) 
        FROM ai_simulation_positions p2 
        WHERE p2.ai_account_id = a.id AND p2.code != 'CASH'
    ), 0),
    1.0,
    a.initial_capital - COALESCE((
        SELECT SUM(p2.market_value) 
        FROM ai_simulation_positions p2 
        WHERE p2.ai_account_id = a.id AND p2.code != 'CASH'
    ), 0),
    datetime('now', 'localtime')
FROM ai_simulation_accounts a
WHERE a.source_type = 'fund'
AND NOT EXISTS (
    SELECT 1 FROM ai_simulation_positions p 
    WHERE p.ai_account_id = a.id AND p.code = 'CASH'
);

-- 验证结果
SELECT 
    a.id,
    a.name,
    a.source_type,
    a.initial_capital,
    p.code,
    p.name as position_name,
    p.market_value
FROM ai_simulation_accounts a
LEFT JOIN ai_simulation_positions p ON a.id = p.ai_account_id
WHERE a.source_type = 'fund' AND p.code = 'CASH'
ORDER BY a.id;
