-- ============================================================
-- Instacart Market Basket Analysis - 建表语句
-- 数据集来源: Kaggle "Instacart Market Basket Analysis"
-- 共计 6 张表，覆盖 20万+ 用户、300万+ 订单
-- ============================================================

-- 商品类目表
CREATE TABLE aisles (
    aisle_id    INT PRIMARY KEY,
    aisle       VARCHAR(100)
);

-- 商品部门表
CREATE TABLE departments (
    department_id   INT PRIMARY KEY,
    department      VARCHAR(100)
);

-- 商品信息表
CREATE TABLE products (
    product_id      INT PRIMARY KEY,
    product_name    VARCHAR(255),
    aisle_id        INT,
    department_id   INT,
    FOREIGN KEY (aisle_id) REFERENCES aisles(aisle_id),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- 订单表 (prior: 历史订单, train: 训练集订单)
CREATE TABLE orders (
    order_id                INT PRIMARY KEY,
    user_id                 INT,
    eval_set                VARCHAR(10),   -- prior / train / test
    order_number            INT,            -- 该用户的第几单
    order_dow               INT,            -- 周几下单 (0=周日)
    order_hour_of_day       INT,            -- 几点下单
    days_since_prior_order  DECIMAL(10,2)   -- 距上一单天数
);

-- 订单-商品明细表 (历史订单)
CREATE TABLE order_products_prior (
    order_id            INT,
    product_id          INT,
    add_to_cart_order   INT,     -- 加入购物车顺序
    reordered           TINYINT, -- 是否为复购商品 (0/1)
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 订单-商品明细表 (训练集，用于预测用户下次购买)
CREATE TABLE order_products_train (
    order_id            INT,
    product_id          INT,
    add_to_cart_order   INT,
    reordered           TINYINT,
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
