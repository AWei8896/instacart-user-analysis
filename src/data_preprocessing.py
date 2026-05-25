"""
数据加载与预处理模块。

完成以下任务：
  1. 从 CSV 加载 6 张原始表
  2. 处理缺失值、类型转换
  3. 多表合并构建分析宽表
  4. 输出数据质量报告
"""

import pandas as pd
import numpy as np
from config import DATA_DIR, DATA_FILES


def load_all_tables() -> dict[str, pd.DataFrame]:
    """加载所有 CSV 文件并返回字典。"""
    tables = {}
    for name, filename in DATA_FILES.items():
        path = f"{DATA_DIR}/{filename}"
        try:
            df = pd.read_csv(path)
            tables[name] = df
            print(f"[OK] {name}: {df.shape[0]:,} rows × {df.shape[1]} cols")
        except FileNotFoundError:
            print(f"[SKIP] {name}: 文件不存在 ({path})，将从已有数据推导")
    return tables


def check_missing(df: pd.DataFrame, name: str) -> None:
    """检查缺失值并打印报告。"""
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if len(missing) > 0:
        print(f"\n[缺失值] {name}:")
        for col, cnt in missing.items():
            print(f"  {col}: {cnt} ({cnt/len(df)*100:.2f}%)")
    else:
        print(f"[缺失值] {name}: 无缺失")


def build_analysis_table(
    orders: pd.DataFrame,
    order_products: pd.DataFrame,
    products: pd.DataFrame,
    departments: pd.DataFrame,
    aisles: pd.DataFrame,
) -> pd.DataFrame:
    """
    构建核心分析宽表：订单-商品-用户维度完全展开。

    返回字段：
        order_id, user_id, product_id, product_name,
        aisle, department, order_number, order_dow,
        order_hour_of_day, days_since_prior_order,
        add_to_cart_order, reordered, eval_set
    """
    # 合并商品维度
    products_enriched = (
        products
        .merge(departments, on="department_id", how="left")
        .merge(aisles, on="aisle_id", how="left")
    )

    # 合并订单 + 商品明细
    df = (
        order_products
        .merge(orders[["order_id", "user_id", "order_number",
                        "order_dow", "order_hour_of_day",
                        "days_since_prior_order", "eval_set"]],
               on="order_id", how="left")
        .merge(products_enriched, on="product_id", how="left")
    )

    print(f"\n[分析宽表] {df.shape[0]:,} rows × {df.shape[1]} cols")
    return df


def preprocess(verbose: bool = True) -> pd.DataFrame:
    """
    主预处理流程：
      加载 → 检查 → 清洗 → 合并 → 返回分析宽表。
    """
    tables = load_all_tables()

    # --- 缺失值检查 ---
    if verbose:
        for name, df in tables.items():
            check_missing(df, name)

    # --- 清洗 orders ---
    orders = tables["orders"].copy()
    # days_since_prior_order 首单为 NaN，填充为 0
    orders["days_since_prior_order"] = orders["days_since_prior_order"].fillna(0)

    # --- 清洗 products ---
    products = tables["products"].copy()
    departments = tables["departments"].copy()
    aisles = tables["aisles"].copy()

    # --- 构建分析宽表 ---
    df = build_analysis_table(
        orders=orders,
        order_products=tables["order_products_prior"],
        products=products,
        departments=departments,
        aisles=aisles,
    )

    if verbose:
        print(f"\n[数据概览]")
        print(f"  用户数: {df['user_id'].nunique():,}")
        print(f"  商品数: {df['product_id'].nunique():,}")
        print(f"  品类数: {df['department'].nunique()}")
        print(f"  订单数: {df['order_id'].nunique():,}")
        print(f"  时间跨度: {orders['order_number'].max()} 单/用户(最大)")
        print(f"  复购率(商品级): {df['reordered'].mean()*100:.1f}%")

    return df


if __name__ == "__main__":
    df = preprocess()
