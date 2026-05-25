"""
数据可视化模块 — 共 7 张核心图表。

图表清单：
  1. 复购周期分布直方图
  2. 用户留存热力图 (Cohort Heatmap)
  3. RFM 分层用户占比饼图
  4. RFM 维度雷达图 (各层用户画像)
  5. 品类复购率 Top-N 水平柱状图
  6. 品类连带率热力图
  7. 订单量-时段热力图

所有图表自动保存为 PNG 至 output/ 目录。
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from config import OUTPUT_DIR, FIGURE_DPI, FIGURE_SIZE_DEFAULT, TOP_N


def safe_save(fig, filename: str) -> None:
    """保存图片到输出目录。"""
    path = f"{OUTPUT_DIR}/{filename}"
    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight", facecolor="white")
    print(f"  [SAVED] {path}")
    plt.close(fig)


# ---- 图表 1: 复购周期分布 ----
def plot_repurchase_interval(df: pd.DataFrame) -> None:
    """用户复购间隔天数分布直方图。"""
    fig, ax = plt.subplots(figsize=FIGURE_SIZE_DEFAULT)

    intervals = df[df["days_since_prior_order"] > 0]["days_since_prior_order"]
    intervals = intervals[intervals <= 30]

    if len(intervals) == 0:
        print("  [SKIP] 无有效复购间隔数据")
        plt.close(fig)
        return

    ax.hist(intervals, bins=30, color="#4C72B0", edgecolor="white", alpha=0.85)
    ax.axvline(intervals.median(), color="#C44E52", linestyle="--",
               linewidth=2, label=f"median: {intervals.median():.1f}d")
    ax.axvline(intervals.mean(), color="#55A868", linestyle="--",
               linewidth=2, label=f"mean: {intervals.mean():.1f}d")

    ax.set_xlabel("Days since last order", fontsize=12)
    ax.set_ylabel("Order count", fontsize=12)
    ax.set_title("Repurchase interval distribution", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    safe_save(fig, "01_repurchase_interval_distribution.png")


# ---- 图表 2: Cohort 留存热力图 ----
def plot_cohort_heatmap(matrix: pd.DataFrame) -> None:
    """用户周留存率热力图。"""
    if matrix.empty:
        print("  [SKIP] Cohort matrix is empty")
        return

    # 取前 12 cohort, 前 12 周
    rows_to_show = min(len(matrix), 12)
    cols_to_show = min(len(matrix.columns), 12)
    m = matrix.iloc[:rows_to_show, :cols_to_show].copy()
    m.index = [f"C{i}" for i in range(len(m))]
    m.columns = [f"W{i}" for i in range(m.shape[1])]

    fig, ax = plt.subplots(figsize=(14, 8))
    sns.heatmap(
        m, annot=True, fmt=".0f", cmap="YlOrRd",
        linewidths=1, linecolor="white",
        cbar_kws={"label": "Retention (%)"},
        ax=ax, vmin=0, vmax=100,
    )
    ax.set_title("Weekly retention cohort heatmap", fontsize=14, fontweight="bold")
    ax.set_xlabel("Week N after first purchase", fontsize=12)
    ax.set_ylabel("Acquisition cohort", fontsize=12)

    safe_save(fig, "02_cohort_retention_heatmap.png")


# ---- 图表 3: RFM 用户分层饼图 ----
def plot_rfm_pie(rfm: pd.DataFrame) -> None:
    """各层级用户占比饼图。"""
    if "ltv_label" not in rfm.columns:
        print("  [SKIP] ltv_label column not found in RFM data")
        return

    fig, ax = plt.subplots(figsize=(8, 8))
    tier_counts = rfm["ltv_label"].value_counts()
    colors = ["#C44E52", "#DD8452", "#55A868", "#4C72B0", "#937860"]

    wedges, texts, autotexts = ax.pie(
        tier_counts.values,
        labels=tier_counts.index,
        autopct="%1.1f%%",
        colors=colors[:len(tier_counts)],
        startangle=90,
        pctdistance=0.6,
        labeldistance=1.1,
    )
    for t in autotexts:
        t.set_fontsize(10)

    ax.set_title("RFM user tiers", fontsize=14, fontweight="bold")
    safe_save(fig, "03_rfm_user_tiers_pie.png")


# ---- 图表 4: RFM 分层雷达图 ----
def plot_rfm_radar(rfm: pd.DataFrame) -> None:
    """各层用户的 RFM 三维度雷达图。"""
    radar_data = rfm.groupby("ltv_label", observed=False).agg(
        recency_norm=("r_score", "mean"),
        frequency_norm=("f_score", "mean"),
        monetary_norm=("m_score", "mean"),
    ).reset_index()

    categories = ["Recency", "Frequency", "Monetary"]
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    colors = ["#C44E52", "#DD8452", "#55A868", "#4C72B0", "#937860"]

    for idx, row in radar_data.iterrows():
        values = [row["recency_norm"], row["frequency_norm"], row["monetary_norm"]]
        values += values[:1]
        color_idx = idx % len(colors)
        ax.plot(angles, values, "o-", linewidth=2, color=colors[color_idx],
                label=row["ltv_label"])
        ax.fill(angles, values, alpha=0.1, color=colors[color_idx])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11)
    ax.set_ylim(0, 5.5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_title("RFM radar chart by tier", fontsize=14, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    safe_save(fig, "04_rfm_radar_chart.png")


# ---- 图表 5: 品类复购率 Top-N 柱状图 ----
def plot_dept_reorder(dept_reorder: pd.DataFrame) -> None:
    """品类复购率水平柱状图。"""
    if dept_reorder.empty or "reorder_rate" not in dept_reorder.columns:
        print("  [SKIP] No dept reorder data")
        return

    data = dept_reorder.head(15).copy()
    data = data.sort_values("reorder_rate", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(data["department"], data["reorder_rate"],
                   color="#4C72B0", alpha=0.85)

    for bar, val in zip(bars, data["reorder_rate"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=9)

    ax.set_xlabel("Reorder rate (%)", fontsize=12)
    ax.set_title("Top 15 department reorder rates", fontsize=14, fontweight="bold")
    ax.set_xlim(0, data["reorder_rate"].max() * 1.15)
    ax.grid(axis="x", alpha=0.3)

    safe_save(fig, "05_dept_reorder_rate_top15.png")


# ---- 图表 6: 品类连带率热力图 ----
def plot_association_heatmap(assoc_df: pd.DataFrame) -> None:
    """品类间连带率矩阵热力图。"""
    if assoc_df.empty:
        print("  [SKIP] Association dataframe is empty")
        return

    # 取出现频率最高的品类
    all_depts = pd.concat([
        assoc_df["dept_a"], assoc_df["dept_b"]
    ]).value_counts().head(12)

    if len(all_depts) < 2:
        print("  [SKIP] Not enough departments for association heatmap")
        return

    dept_list = all_depts.index.tolist()
    n = len(dept_list)
    # 初始化矩阵，对角 = 100
    matrix = pd.DataFrame(np.eye(n) * 100, index=dept_list, columns=dept_list)

    for _, row in assoc_df.iterrows():
        a, b = row["dept_a"], row["dept_b"]
        if a in dept_list and b in dept_list:
            matrix.loc[a, b] = row["pct_b_given_a"]
            matrix.loc[b, a] = row["pct_a_given_b"]

    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(
        matrix.astype(float), annot=True, fmt=".0f", cmap="YlOrRd",
        linewidths=1, linecolor="white",
        cbar_kws={"label": "Association (%)"},
        ax=ax, vmin=0, vmax=100,
    )
    ax.set_title("Category association matrix", fontsize=14, fontweight="bold")
    ax.set_xlabel("Department B", fontsize=12)
    ax.set_ylabel("Department A", fontsize=12)

    safe_save(fig, "06_category_association_heatmap.png")


# ---- 图表 7: 订单时段热力图 ----
def plot_time_heatmap(df: pd.DataFrame) -> None:
    """星期 x 小时 订单量热力图。"""
    dow_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    if "order_dow" not in df.columns:
        print("  [SKIP] order_dow column not found")
        return

    pivot = df.groupby(["order_dow", "order_hour_of_day"]).size().unstack(fill_value=0)

    # 安全映射 dow → 标签
    pivot.index = [dow_labels[int(i)] if 0 <= int(i) <= 6 else f"D{i}"
                   for i in pivot.index]

    fig, ax = plt.subplots(figsize=(14, 6))
    sns.heatmap(
        pivot, cmap="YlOrRd",
        linewidths=0.5, linecolor="gray",
        cbar_kws={"label": "Orders"},
        ax=ax,
    )
    ax.set_title("Order volume by day-of-week x hour", fontsize=14, fontweight="bold")
    ax.set_xlabel("Hour of day", fontsize=12)

    safe_save(fig, "07_order_time_heatmap.png")


# ---- 批量生成所有图表 ----
def generate_all_charts(
    df: pd.DataFrame,
    cohort_matrix: pd.DataFrame,
    rfm: pd.DataFrame,
    dept_reorder: pd.DataFrame,
    assoc_df: pd.DataFrame,
) -> None:
    """一键生成全部 7 张图表，单张失败不影响后续。"""
    print("\n" + "=" * 60)
    print("  Generating charts...")
    print("=" * 60)

    charts = [
        ("Repurchase interval", plot_repurchase_interval, [df]),
        ("Cohort heatmap",       plot_cohort_heatmap,       [cohort_matrix]),
        ("RFM pie",              plot_rfm_pie,              [rfm]),
        ("RFM radar",            plot_rfm_radar,            [rfm]),
        ("Dept reorder",         plot_dept_reorder,         [dept_reorder]),
        ("Association heatmap",  plot_association_heatmap,  [assoc_df]),
        ("Time heatmap",         plot_time_heatmap,         [df]),
    ]

    for name, func, args in charts:
        try:
            func(*args)
        except Exception as e:
            print(f"  [ERR] {name}: {e}")

    print(f"\n[可视化] Done. Output: {OUTPUT_DIR}/")
