"""Cost calculator service — Excel 模板导入解析。

Excel 模板约定（第 1 行为表头，第 2 行起为明细）：
    | 费用类型 | 项目名称 | 单位 | 单价 | 数量 | 小计 |
    | 原材料   | ABS塑料  | kg   | 18.5 | 0.12 | =D2*E2 |

「公式」处理：成本模板的核心关系是「小计 = 单价 × 数量」。该关系已内建在
CostItem 模型中（subtotal 由 unit_price * quantity 重算），因此 Excel 里的
小计列无论是公式 (=D2*E2) 还是手填数值，都会被忽略并在导入时自动重算——
既保留了公式语义，又避免解析任意 Excel 公式的复杂度。
"""
from __future__ import annotations

import io
import re

from openpyxl import load_workbook


# 中文标签 → 内部类型 key（同时兼容直接填英文 key）
TYPE_LABEL_TO_KEY = {
    "原材料": "material",
    "人力成本": "labor",
    "水电气": "utility",
    "委外加工": "processing_out",
    "自有产线": "processing_own",
    "模具摊销": "mold",
    "运费": "freight",
    "包装费": "packaging",
    "损耗": "loss",
    "其他费用": "other",
    # 兼容英文 key 直填
    "material": "material",
    "labor": "labor",
    "utility": "utility",
    "processing_out": "processing_out",
    "processing_own": "processing_own",
    "mold": "mold",
    "freight": "freight",
    "packaging": "packaging",
    "loss": "loss",
    "other": "other",
}

def _to_number(value) -> float:
    """单元格值转 float，容忍 '18.5'、'18.5元'、'1,200' 等写法；无法解析返回 0。"""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "").replace("，", "")
    s = re.sub(r"[^\d.\-]", "", s)  # 去掉单位/货币符号，保留数字、小数点、负号
    try:
        return float(s)
    except ValueError:
        return 0.0


def _normalize_type(value) -> str:
    """费用类型归一化为内部 key，无法识别归为 other。"""
    s = str(value or "").strip()
    if s in TYPE_LABEL_TO_KEY:
        return TYPE_LABEL_TO_KEY[s]
    # 模糊匹配：包含关系（如「委外加工费」→ 委外加工）
    for label, key in TYPE_LABEL_TO_KEY.items():
        if label in s:
            return key
    return "other"


def parse_excel(file_bytes: bytes) -> list[dict]:
    """解析 Excel 成本明细，返回 items 列表（type/name/unit/unit_price/quantity）。

    用小计列自动重算，故返回的 subtotal 恒为 unit_price * quantity。
    """
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    items: list[dict] = []
    for row in ws.iter_rows(min_row=1, values_only=True):
        if row is None:
            continue
        # 取前 6 列，缺列补空
        cells = list(row[:6]) + [None] * (6 - len(row[:6]))
        type_cell, name_cell, unit_cell, price_cell, qty_cell, _subtotal_cell = cells

        type_str = str(type_cell or "").strip()
        name = str(name_cell or "").strip()

        # 跳过表头行（首列含「费用类型/类型」或名称列含「项目名称/名称」）
        if any(h in type_str for h in ("费用类型", "类型")) or any(h in name for h in ("项目名称", "名称")):
            continue
        # 跳过空行
        if not name:
            continue

        unit_price = _to_number(price_cell)
        quantity = _to_number(qty_cell) or 1.0
        items.append({
            "type": _normalize_type(type_cell),
            "name": name,
            "unit": str(unit_cell or "").strip() or "pcs",
            "unit_price": round(unit_price, 4),
            "quantity": round(quantity, 4),
        })

    return items
