"""
主执行入口 — 一键运行全部分析流程。
"""

import time
import pandas as pd
from config import DATA_DIR, OUTPUT_DIR


def main():
    start_time = time.time()

    print("=" * 60)
    print("Instacart 用户复购行为与品类偏好分析")
    print("数据: Kaggle Instacart Market Basket Analysis")
    print("=" * 60)

    # 数据预处理
    print("\n" + "-" * 60)
    print("  [Step 1/5] 数据预处理")
    print("-" * 60)
    from data_preprocessing import preprocess
    df = preprocess()

    orders = pd.read_csv(f"{DATA_DIR}/orders.csv")

    # RFM 分析
    print("\n" + "-" * 60)
    print("  [Step 2/5] RFM 用户分层")
    print("-" * 60)
    from rfm_analysis import run_rfm_pipeline
    rfm = run_rfm_pipeline(df)

    # 留存分析
    print("\n" + "-" * 60)
    print("  [Step 3/5] Cohort 留存分析")
    print("-" * 60)
    from cohort_analysis import run_cohort_pipeline
    cohort_matrix = run_cohort_pipeline(orders)

    # 品类分析
    print("\n" + "-" * 60)
    print("  [Step 4/5] 品类关联分析")
    print("-" * 60)
    from category_analysis import run_category_pipeline
    cat_results = run_category_pipeline(df)

    # 可视化
    print("\n" + "-" * 60)
    print("  [Step 5/5] 可视化图表生成")
    print("-" * 60)
    from visualization import generate_all_charts
    generate_all_charts(
        df=df,
        cohort_matrix=cohort_matrix,
        rfm=rfm,
        dept_reorder=cat_results["dept_reorder"],
        assoc_df=cat_results["association"],
    )

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  全部分析完成! 总耗时 {elapsed:.1f} 秒")
    print(f"  输出目录: {OUTPUT_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
