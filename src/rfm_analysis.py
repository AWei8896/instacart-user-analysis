"""
RFM 用户分层模型。

R - Recency:  最近一次购买距分析截止日的天数
F - Frequency: 历史购买次数
M - Monetary:  购买商品总数(作为消费金额的代理变量)

"""

import pandas as pd
import numpy as np
from config import RFM_QUANTILES, LTV_TIER_LABELS, OUTPUT_DIR


def build_rfm(df: pd.DataFrame, reference_date: str = "2015-12-31") -> pd.DataFrame:

    # 构建 RFM 特征表。
    # 按用户聚合 R/F/M 三维度
    # R: 累计购买间隔天数总和（越小越活跃）
    # F: 独立订单数
    # M: 购买商品总数
    rfm = df.groupby("user_id").agg(
        recency=("days_since_prior_order", "sum"),
        frequency=("order_id", "nunique"),
        monetary=("product_id", "count"),
    ).reset_index()

    print(f"\n[RFM] 特征构建完成")
    print(f"  用户数: {rfm.shape[0]:,}")
    print(f"  R 均值: {rfm['recency'].mean():.1f} 天")
    print(f"  F 均值: {rfm['frequency'].mean():.1f} 单")
    print(f"  M 均值: {rfm['monetary'].mean():.1f} 件")

    return rfm


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:

    # 对 RFM 三维度打分 (分位数法, 1-5 分)。
    rfm = rfm.copy()

    # Recency 反向打分
    rfm["r_score"] = pd.qcut(
        rfm["recency"], q=RFM_QUANTILES, labels=range(RFM_QUANTILES, 0, -1)
    ).astype(int)

    # Frequency 正向打分
    rfm["f_score"] = pd.qcut(
        rfm["frequency"], q=RFM_QUANTILES, labels=range(1, RFM_QUANTILES + 1)
    ).astype(int)

    # Monetary 正向打分
    rfm["m_score"] = pd.qcut(
        rfm["monetary"], q=RFM_QUANTILES, labels=range(1, RFM_QUANTILES + 1)
    ).astype(int)

    # 总分
    rfm["rfm_total"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    # 分层标签 (按总分划分5层)
    rfm["ltv_tier"] = pd.qcut(
        rfm["rfm_total"], q=RFM_QUANTILES, labels=range(1, RFM_QUANTILES + 1)
    ).astype(int)
    rfm["ltv_label"] = rfm["ltv_tier"].map(LTV_TIER_LABELS)

    return rfm


def rfm_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    """输出各层级用户的画像汇总"""
    summary = (
        rfm.groupby("ltv_label")
        .agg(
            用户数=("user_id", "count"),
            用户占比=("user_id", lambda x: f"{len(x)/len(rfm)*100:.1f}%"),
            平均复购次数=("frequency", "mean"),
            平均商品购买数=("monetary", "mean"),
            平均活跃度=("recency", "mean"),
        )
        .round(1)
    )
    print(f"\n[RFM 分层画像]")
    print(summary.to_string())
    return summary


def run_rfm_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """一键执行 RFM 全流程"""
    rfm = build_rfm(df)
    rfm = score_rfm(rfm)
    rfm_summary(rfm)

    # 保存结果
    output_path = f"{OUTPUT_DIR}/rfm_user_segments.csv"
    rfm.to_csv(output_path, index=False)
    print(f"\n[RFM] 结果已保存至 {output_path}")

    return rfm


if __name__ == "__main__":
    from data_preprocessing import preprocess
    df = preprocess(verbose=False)
    rfm = run_rfm_pipeline(df)
