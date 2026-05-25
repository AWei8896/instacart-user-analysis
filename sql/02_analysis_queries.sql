-- ============================================================
-- 核心分析 SQL (全部使用窗口函数)
-- ============================================================

-- -------------------------------------
-- 1. 用户复购间隔分析 (LAG)
-- 计算每个用户相邻两次购买相隔多少天
-- -------------------------------------
WITH user_orders AS (
    SELECT
        user_id,
        order_id,
        order_number,
        days_since_prior_order
    FROM orders
    WHERE eval_set = 'prior'
)
SELECT
    user_id,
    order_number,
    days_since_prior_order,
    AVG(days_since_prior_order) OVER (
        PARTITION BY user_id
    ) AS user_avg_interval,
    SUM(CASE WHEN days_since_prior_order <= 7 THEN 1 ELSE 0 END) OVER (
        PARTITION BY user_id
    ) AS weekly_repurchase_count,
    COUNT(*) OVER (
        PARTITION BY user_id
    ) AS total_orders_per_user
FROM user_orders
WHERE days_since_prior_order IS NOT NULL
ORDER BY user_id, order_number;


-- -------------------------------------
-- 2. 品类复购率排名 (RANK + 子查询)
-- 计算每个品类的购买用户数、占比、排名
-- -------------------------------------
WITH dept_users AS (
    SELECT
        p.department_id,
        d.department,
        COUNT(DISTINCT o.user_id) AS buyer_cnt
    FROM order_products_prior op
    JOIN products p  ON op.product_id = p.product_id
    JOIN orders o    ON op.order_id = o.order_id
    JOIN departments d ON p.department_id = d.department_id
    WHERE o.eval_set = 'prior'
    GROUP BY p.department_id, d.department
)
SELECT
    department,
    buyer_cnt,
    ROUND(buyer_cnt * 100.0 / SUM(buyer_cnt) OVER(), 2) AS buyer_pct,
    RANK() OVER(ORDER BY buyer_cnt DESC) AS dept_rank
FROM dept_users
ORDER BY dept_rank;


-- -------------------------------------
-- 3. 用户生命周期分层 (NTILE 分桶)
-- 将用户按总订单数分为 5 个层级，并为每层打标签
-- -------------------------------------
WITH user_summary AS (
    SELECT
        user_id,
        COUNT(DISTINCT order_id) AS total_orders,
        AVG(days_since_prior_order) AS avg_cycle_days,
        MAX(order_number) AS max_order_number
    FROM orders
    WHERE eval_set = 'prior'
    GROUP BY user_id
)
SELECT
    user_id,
    total_orders,
    avg_cycle_days,
    NTILE(5) OVER(ORDER BY total_orders DESC) AS ltv_tier,
    CASE
        WHEN NTILE(5) OVER(ORDER BY total_orders DESC) = 1 THEN '高价值'
        WHEN NTILE(5) OVER(ORDER BY total_orders DESC) = 2 THEN '中高价值'
        WHEN NTILE(5) OVER(ORDER BY total_orders DESC) = 3 THEN '中价值'
        WHEN NTILE(5) OVER(ORDER BY total_orders DESC) = 4 THEN '中低价值'
        ELSE '低价值'
    END AS ltv_label
FROM user_summary;


-- -------------------------------------
-- 4. 周度留存队列 (Cohort 分析)
-- 按用户首购周分组，计算后续每周的留存率
-- -------------------------------------
WITH first_purchase AS (
    SELECT
        user_id,
        MIN(order_date) AS cohort_date
    FROM orders
    GROUP BY user_id
),
weekly_activity AS (
    SELECT
        user_id,
        YEARWEEK(order_date) AS active_week,
        COUNT(DISTINCT order_id) AS weekly_orders
    FROM orders
    GROUP BY user_id, YEARWEEK(order_date)
)
SELECT
    fp.cohort_date,
    YEARWEEK(fp.cohort_date) AS cohort_week,
    COUNT(DISTINCT fp.user_id) AS cohort_size
FROM first_purchase fp
GROUP BY fp.cohort_date, YEARWEEK(fp.cohort_date)
ORDER BY cohort_week;


-- -------------------------------------
-- 5. 商品复购率排行 (SUM OVER + ROW_NUMBER)
-- 找出复购率最高的 Top 20 商品
-- -------------------------------------
WITH product_reorder AS (
    SELECT
        op.product_id,
        p.product_name,
        p.department_id,
        COUNT(*) AS total_purchases,
        SUM(op.reordered) AS reorder_count,
        ROUND(SUM(op.reordered) * 100.0 / COUNT(*), 2) AS reorder_rate
    FROM order_products_prior op
    JOIN products p ON op.product_id = p.product_id
    GROUP BY op.product_id, p.product_name, p.department_id
)
SELECT
    product_name,
    total_purchases,
    reorder_count,
    reorder_rate,
    RANK() OVER(ORDER BY reorder_rate DESC) AS reorder_rank
FROM product_reorder
WHERE total_purchases >= 100   -- 过滤低频商品避免偏差
ORDER BY reorder_rate DESC
LIMIT 20;


-- -------------------------------------
-- 6. 用户购物篮大小趋势 (滚动平均)
-- 用窗口函数计算每个用户购物篮大小的滚动平均值
-- -------------------------------------
SELECT
    user_id,
    order_number,
    cart_size,
    ROUND(
        AVG(cart_size) OVER (
            PARTITION BY user_id
            ORDER BY order_number
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 1
    ) AS rolling_avg_cart_size_3
FROM (
    SELECT
        o.user_id,
        o.order_number,
        COUNT(op.product_id) AS cart_size
    FROM orders o
    JOIN order_products_prior op ON o.order_id = op.order_id
    WHERE o.eval_set = 'prior'
    GROUP BY o.user_id, o.order_id, o.order_number
) t
ORDER BY user_id, order_number
LIMIT 500;


-- -------------------------------------
-- 7. 时段-品类交叉分析 (多维聚合)
-- 各品类在不同时段的订单量分布
-- -------------------------------------
SELECT
    d.department,
    CASE
        WHEN o.order_hour_of_day BETWEEN 0  AND 5  THEN '凌晨'
        WHEN o.order_hour_of_day BETWEEN 6  AND 11 THEN '上午'
        WHEN o.order_hour_of_day BETWEEN 12 AND 17 THEN '下午'
        ELSE '晚上'
    END AS time_period,
    COUNT(DISTINCT o.order_id) AS order_cnt,
    RANK() OVER(
        PARTITION BY d.department
        ORDER BY COUNT(DISTINCT o.order_id) DESC
    ) AS peak_rank
FROM orders o
JOIN order_products_prior op ON o.order_id = op.order_id
JOIN products p ON op.product_id = p.product_id
JOIN departments d ON p.department_id = d.department_id
WHERE o.eval_set = 'prior'
GROUP BY d.department, time_period
ORDER BY department, order_cnt DESC;
