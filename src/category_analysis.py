"""
品类关联分析与连带率计算。

方法：
  1. 构建用户-品类购买矩阵
  2. 计算品类共现频率 (同时购买的品类对)
  3. 计算品类连带率: P(买了B | 已买A)
  4. 识别高连带品类组合
"""

import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from itertools import combinations
from config import OUTPUT_DIR, TOP_N


def build_dept_user_matrix(df: pd.DataFrame) -> pd.DataFrame:

    # 品类购买矩阵

    matrix = (
        df.groupby(["user_id", "department_id"])
        .size()
        .unstack(fill_value=0)
    )
    print(f"\n[品类矩阵] 用户×品类 = {matrix.shape[0]} × {matrix.shape[1]}")
    return matrix


def calc_pairwise_association(
    dept_matrix: pd.DataFrame,
    min_users: int = 50,
) -> pd.DataFrame:
    """
    计算品类两两之间的连带率。
    """
    results = []
    dept_names = dept_matrix.columns.tolist()
    n_users = len(dept_matrix)

    for dept_a, dept_b in combinations(dept_names, 2):
        # 买过 A 的用户
        users_a = set(dept_matrix.index[dept_matrix[dept_a] > 0])
        users_b = set(dept_matrix.index[dept_matrix[dept_b] > 0])
        joint = users_a & users_b

        if len(users_a) >= min_users and len(users_b) >= min_users:
            results.append({
                "dept_a": dept_a,
                "dept_b": dept_b,
                "pct_b_given_a": len(joint) / len(users_a) * 100,
                "pct_a_given_b": len(joint) / len(users_b) * 100,
                "joint_users": len(joint),
                "dept_a_users": len(users_a),
                "dept_b_users": len(users_b),
            })

    assoc_df = pd.DataFrame(results)
    assoc_df = assoc_df.sort_values("pct_b_given_a", ascending=False)
    assoc_df["rank"] = range(1, len(assoc_df) + 1)

    print(f"\n[品类关联] 共计算 {len(assoc_df)} 对品类组合")
    print(f"  Top 5 高连带组合:")
    for _, row in assoc_df.head(5).iterrows():
        print(
            f"  买【{row['dept_a']}】→ 也买【{row['dept_b']}】: "
            f"{row['pct_b_given_a']:.1f}% "
            f"(联合用户 {row['joint_users']:,})"
        )

    return assoc_df


def calc_dept_reorder_rate(df: pd.DataFrame) -> pd.DataFrame:
    """计算每个品类的复购率排行"""
    dept_reorder = (
        df.groupby("department_id")
        .agg(
            department=("department", "first"),
            total_purchases=("reordered", "count"),
            reorder_count=("reordered", "sum"),
            unique_users=("user_id", "nunique"),
        )
        .reset_index(drop=True)
    )
    dept_reorder["reorder_rate"] = (
        dept_reorder["reorder_count"] / dept_reorder["total_purchases"] * 100
    )
    dept_reorder = dept_reorder.sort_values("reorder_rate", ascending=False)
    dept_reorder["rank"] = range(1, len(dept_reorder) + 1)

    print(f"\n[品类复购率 Top {TOP_N}]")
    for _, row in dept_reorder.head(TOP_N).iterrows():
        print(f"  {row['rank']:2d}. {row['department']:<25s} "
              f"复购率 {row['reorder_rate']:.1f}%  "
              f"用户数 {row['unique_users']:,}")

    return dept_reorder


def calc_aisle_reorder_rate(df: pd.DataFrame) -> pd.DataFrame:
    """计算每个子品类的复购率排行"""
    aisle_reorder = (
        df.groupby("aisle_id")
        .agg(
            aisle=("aisle", "first"),
            department=("department", "first"),
            total_purchases=("reordered", "count"),
            reorder_count=("reordered", "sum"),
        )
        .reset_index(drop=True)
    )
    aisle_reorder["reorder_rate"] = (
        aisle_reorder["reorder_count"] / aisle_reorder["total_purchases"] * 100
    )
    # 过滤低频子品类
    aisle_reorder = aisle_reorder[aisle_reorder["total_purchases"] >= 100]
    aisle_reorder = aisle_reorder.sort_values("reorder_rate", ascending=False)

    return aisle_reorder


def run_category_pipeline(df: pd.DataFrame) -> dict:
    """一键执行品类分析全流程"""
    # 1. 品类复购率
    dept_reorder = calc_dept_reorder_rate(df)

    # 2. 品类关联
    dept_matrix = build_dept_user_matrix(df)
    assoc = calc_pairwise_association(dept_matrix)

    # 3. 子品类复购率
    aisle_reorder = calc_aisle_reorder_rate(df)

    # 保存
    dept_reorder.to_csv(f"{OUTPUT_DIR}/dept_reorder_rate.csv", index=False)
    assoc.to_csv(f"{OUTPUT_DIR}/category_association.csv", index=False)
    aisle_reorder.to_csv(f"{OUTPUT_DIR}/aisle_reorder_rate.csv", index=False)
    print(f"\n[品类分析] 结果已保存至 {OUTPUT_DIR}/")

    return {
        "dept_reorder": dept_reorder,
        "association": assoc,
        "aisle_reorder": aisle_reorder,
    }


if __name__ == "__main__":
    from data_preprocessing import preprocess
    df = preprocess(verbose=False)
    run_category_pipeline(df)
