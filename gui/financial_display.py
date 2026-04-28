"""财报分析表格显示辅助模块。"""

import pandas as pd


IDENTIFIER_KEYWORDS = ("代码", "名称", "简称", "序号", "行业", "日期", "公告日", "链接", "市场")
RANK_KEYWORDS = ("排名",)
AMOUNT_KEYWORDS = ("收入", "利润", "市值", "现金流", "金额", "资产", "负债", "权益", "总额", "资本")


def build_financial_display_config(df):
    """为财报分析 DataFrame 生成按列显示配置。"""
    config = {}
    for col in df.columns:
        column_name = str(col)
        numeric_series = pd.to_numeric(df[col], errors="coerce")
        column_config = {"kind": "text", "header": column_name}

        if _is_identifier_column(column_name):
            column_config["kind"] = "identifier"
        elif _is_rank_column(column_name):
            column_config["kind"] = "rank"
        elif numeric_series.notna().any():
            if _is_amount_column(column_name):
                unit = "亿" if numeric_series.abs().max() >= 100000000 else "万"
                divisor = 100000000 if unit == "亿" else 10000
                column_config = {
                    "kind": "amount",
                    "header": _build_unit_header(column_name, unit),
                    "unit": unit,
                    "divisor": divisor,
                }
            else:
                column_config["kind"] = "numeric"

        config[col] = column_config
    return config


def format_financial_value(value, column_config):
    """按配置格式化财报分析单元格内容。"""
    if pd.isna(value):
        return ""

    kind = column_config.get("kind", "text")
    if kind == "identifier":
        return str(value)
    if kind == "rank":
        numeric_value = pd.to_numeric(value, errors="coerce")
        return str(int(numeric_value)) if pd.notna(numeric_value) else str(value)

    numeric_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_value):
        return str(value)
    if kind == "amount":
        return f"{numeric_value / column_config['divisor']:.2f}"
    return f"{numeric_value:.2f}"


def _is_identifier_column(column_name):
    """判断是否为代码、名称、日期等标识列。"""
    return any(keyword in column_name for keyword in IDENTIFIER_KEYWORDS)


def _is_rank_column(column_name):
    """判断是否为排名列。"""
    return any(keyword in column_name for keyword in RANK_KEYWORDS)


def _is_amount_column(column_name):
    """判断是否为需要按万或亿换算的金额列。"""
    if _is_identifier_column(column_name) or _is_rank_column(column_name):
        return False
    if "每股" in column_name or "%" in column_name or "（%" in column_name or "(%" in column_name:
        return False
    if "率" in column_name or "增长" in column_name or "占比" in column_name or "比重" in column_name:
        return False
    return any(keyword in column_name for keyword in AMOUNT_KEYWORDS)


def _build_unit_header(column_name, unit):
    """把金额列标题统一替换为万或亿。"""
    base_name = str(column_name)
    for old_unit in ("(元)", "（元）", "(万元)", "（万元）", "(亿元)", "（亿元）", "(万)", "（万）", "(亿)", "（亿）"):
        base_name = base_name.replace(old_unit, "")
    return f"{base_name}（{unit}）"
