"""
队列留存分析 (Cohort Retention)。

方法：1. 按用户首购周划分 Cohort 2. 跟踪每 Cohort 在后续各周的留存情况 3. 输出留存热力图矩阵
"""

import pandas as pd
import numpy as np
from config import OUTPUT_DIR


def build_cohort_matrix(
    orders: pd.DataFrame,
    period: str = "W",
) -> pd.DataFrame:
    """
    构建 Cohort 留存矩阵。
    """
    df = orders[["user_id", "order_id", "order_number", "days_since_prior_order"]].copy()

    # 通过累计 days_since_prior_order 推算每个订单的"相对天数"
    df["days_since_prior_order"] = df["days_since_prior_order"].fillna(0)

    # 首单为第0天，后续订单累加间隔天数
    df["cumulative_days"] = df.groupby("user_id")["days_since_prior_order"].cumsum()

    # 每个用户的首次购买日期
    first_purchase = df.groupby("user_id")["cumulative_days"].min().reset_index()
    first_purchase.columns = ["user_id", "first_day"]

    df = df.merge(first_purchase, on="user_id")
    df["days_since_first"] = df["cumulative_days"] - df["first_day"]

    if period == "W":
        df["cohort_period"] = (df["first_day"] // 7).astype(int)
        df["activity_period"] = (df["days_since_first"] // 7).astype(int)
    else:  # 月度
        df["cohort_period"] = (df["first_day"] // 30).astype(int)
        df["activity_period"] = (df["days_since_first"] // 30).astype(int)

    # Cohort大小
    cohort_size = (
        df.groupby("cohort_period")["user_id"]
        .nunique()
        .reset_index()
    )
    cohort_size.columns = ["cohort_period", "cohort_size"]

    # 每个 cohort 在每个 period 的活跃用户数
    activity = (
        df.groupby(["cohort_period", "activity_period"])["user_id"]
        .nunique()
        .reset_index()
    )
    activity.columns = ["cohort_period", "activity_period", "active_users"]

    # 计算留存率
    retention = activity.merge(cohort_size, on="cohort_period")
    retention["retention_rate"] = (
        retention["active_users"] / retention["cohort_size"] * 100
    )

    # 转换为矩阵形式
    matrix = retention.pivot_table(
        index="cohort_period",
        columns="activity_period",
        values="retention_rate",
    )

    print(f"\n[Cohort] 留存矩阵构建完成")
    print(f"Cohort 数: {len(matrix)}")
    print(f"最大Period: {matrix.columns.max()}")

    return matrix


def cohort_summary(matrix: pd.DataFrame) -> pd.DataFrame:
    """输出每个cohort在关键节点的留存率汇总。"""
    # 确保列索引是整数
    matrix.columns = matrix.columns.astype(int)

    cols_available = [c for c in [0, 1, 2, 3, 4, 7, 11] if c in matrix.columns]

    summary = matrix[cols_available].copy()
    summary.columns = [f"第{c}周" for c in cols_available]

    print(f"\n[Cohort 留存汇总]")
    print(summary.round(2).to_string())

    return summary


def run_cohort_pipeline(orders: pd.DataFrame) -> pd.DataFrame:
    """一键执行Cohort分析全流程"""
    matrix = build_cohort_matrix(orders)
    cohort_summary(matrix)

    # 保存
    output_path = f"{OUTPUT_DIR}/cohort_retention_matrix.csv"
    matrix.to_csv(output_path)
    print(f"\n[Cohort] 结果已保存至 {output_path}")

    return matrix


if __name__ == "__main__":
    from data_preprocessing import preprocess
    import pandas as pd

    orders = pd.read_csv("../data/orders.csv")
    matrix = run_cohort_pipeline(orders)
