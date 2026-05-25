"""
全局配置：路径、参数、常量定义。
"""

import os

# ---- 项目根目录 ----
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- 数据目录 ----
DATA_DIR = os.path.join(ROOT_DIR, "data")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---- 数据文件路径 ----
DATA_FILES = {
    "aisles":               "aisles.csv",
    "departments":          "departments.csv",
    "products":             "products.csv",
    "orders":               "orders.csv",
    "order_products_prior": "order_products__prior.csv",
    "order_products_train": "order_products__train.csv",
}

# ---- RFM 参数 ----
RFM_QUANTILES = 5
LTV_TIER_LABELS = {
    1: "高价值用户",
    2: "中高价值用户",
    3: "中价值用户",
    4: "中低价值用户",
    5: "低价值用户",
}

# ---- 可视化参数 ----
FIGURE_DPI = 150
FIGURE_SIZE_DEFAULT = (12, 6)

# 全局设置 matplotlib
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 自动检测可用的中文字体
_cjk_candidates = ["Microsoft YaHei", "SimHei", "KaiTi", "SimSun", "FangSong",
                   "Noto Sans CJK SC", "WenQuanYi Micro Hei", "PingFang SC"]
_available = {f.name for f in fm.fontManager.ttflist}
_found = next((f for f in _cjk_candidates if f in _available), None)

plt.rcParams.update({
    "font.sans-serif": [_found] + plt.rcParams["font.sans-serif"] if _found
                       else plt.rcParams["font.sans-serif"],
    "axes.unicode_minus": False,
    "figure.dpi": FIGURE_DPI,
})
print(f"[config] 中文字体: {_found if _found else '未找到CJK字体，中文可能显示为方块'}")

# ---- 分析参数 ----
TOP_N = 20
COHORT_LOOKBACK_WEEKS = 12
MIN_PURCHASES_FOR_REORDER = 100
