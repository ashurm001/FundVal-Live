-- 修复AI模拟账户历史数据
-- 1. 更新数字货币账户的历史source_value

-- 先查看需要修复的数据
SELECT 
    v.id,
    v.ai_account_id,
    a.name as account_name,
    a.source_type,
    v.record_date,
    v.ai_value,
    v.source_value as old_source_value,
    v.ai_return_rate,
    v.source_return_rate as old_source_return_rate
FROM ai_simulation_value_history v
JOIN ai_simulation_accounts a ON v.ai_account_id = a.id
WHERE a.source_type = 'crypto'
ORDER BY v.record_date DESC
LIMIT 20;

-- 更新数字货币账户的历史source_value
-- 使用crypto_positions和crypto_prices计算正确的市值
UPDATE ai_simulation_value_history
SET source_value = (
    SELECT COALESCE(SUM(cp.amount * COALESCE(cpr.price_usd, 0)), 0)
    FROM crypto_positions cp
    LEFT JOIN crypto_prices cpr ON cp.symbol = cpr.symbol
    WHERE cp.account_id = (
        SELECT source_account_id 
        FROM ai_simulation_accounts 
        WHERE id = ai_simulation_value_history.ai_account_id
    )
)
WHERE ai_account_id IN (
    SELECT id FROM ai_simulation_accounts WHERE source_type = 'crypto'
);

-- 更新source_return_rate
UPDATE ai_simulation_value_history
SET source_return_rate = (
    SELECT (v.source_value - a.initial_capital) * 100.0 / NULLIF(a.initial_capital, 0)
    FROM ai_simulation_accounts a
    WHERE a.id = ai_simulation_value_history.ai_account_id
)
WHERE ai_account_id IN (
    SELECT id FROM ai_simulation_accounts WHERE source_type = 'crypto'
);

-- 更新outperformance
UPDATE ai_simulation_value_history
SET outperformance = ai_return_rate - source_return_rate
WHERE ai_account_id IN (
    SELECT id FROM ai_simulation_accounts WHERE source_type = 'crypto'
);

-- 验证修复结果
SELECT 
    v.id,
    v.ai_account_id,
    a.name as account_name,
    a.source_type,
    v.record_date,
    v.ai_value,
    v.source_value as new_source_value,
    v.ai_return_rate,
    v.source_return_rate as new_source_return_rate,
    v.outperformance
FROM ai_simulation_value_history v
JOIN ai_simulation_accounts a ON v.ai_account_id = a.id
WHERE a.source_type = 'crypto'
ORDER BY v.record_date DESC
LIMIT 20;
