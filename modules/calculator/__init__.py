"""Cost calculator module — raw materials, labor, utilities, processing fees."""
from __future__ import annotations

import io
from urllib.parse import quote

from flask import Blueprint, Response, jsonify, render_template, request
from database import get_session
from models import CostItem, CostTemplate
from modules.calculator.service import parse_excel

calculator_bp = Blueprint("calculator", __name__, template_folder="../../templates")

ITEM_TYPES = {
    "material": "原材料",
    "labor": "人力成本",
    "utility": "水电气",
    "processing_out": "委外加工",
    "processing_own": "自有产线",
    "mold": "模具摊销",
    "freight": "运费",
    "packaging": "包装费",
    "loss": "损耗",
    "other": "其他费用",
}


@calculator_bp.route("/calculator")
def page() -> str:
    return render_template("calculator.html", item_types=ITEM_TYPES)


@calculator_bp.route("/api/calculator/calculate", methods=["POST"])
def api_calculate():
    data = request.get_json()
    if not data or "items" not in data:
        return jsonify({"error": "请提供成本明细"}), 400

    items: list[dict] = data["items"]
    results = []
    grand_total = 0.0
    subtotals: dict[str, float] = {}

    for item in items:
        item_type = item.get("type", "other")
        name = item.get("name", "").strip()
        unit_price = float(item.get("unit_price", 0) or 0)
        quantity = float(item.get("quantity", 1) or 1)
        subtotal = round(unit_price * quantity, 2)

        results.append({
            "type": item_type,
            "type_label": ITEM_TYPES.get(item_type, item_type),
            "name": name,
            "unit": item.get("unit", "pcs"),
            "unit_price": unit_price,
            "quantity": quantity,
            "subtotal": subtotal,
        })

        subtotals[item_type] = subtotals.get(item_type, 0) + subtotal
        grand_total += subtotal

    return jsonify({
        "items": results,
        "subtotals": {ITEM_TYPES.get(k, k): round(v, 2) for k, v in subtotals.items()},
        "grand_total": round(grand_total, 2),
        "currency": data.get("currency", "CNY"),
    })


@calculator_bp.route("/api/calculator/templates")
def api_templates():
    session = get_session()
    try:
        templates = session.query(CostTemplate).order_by(CostTemplate.created_at.desc()).all()
        return jsonify([t.to_dict() for t in templates])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@calculator_bp.route("/api/calculator/templates/example")
def api_template_example():
    """下载 Excel 模板示例（表头 + 示例行，含小计公式），方便用户按格式填写。"""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "成本明细"
    ws.append(["费用类型", "项目名称", "单位", "单价", "数量", "小计"])
    ws.append(["原材料", "ABS塑料", "kg", 18.5, 0.12, "=D2*E2"])
    ws.append(["人力成本", "注塑操作工", "小时", 35, 0.05, "=D3*E3"])
    ws.append(["水电气", "水电", "件", 0.3, 1, "=D4*E4"])

    buf = io.BytesIO()
    wb.save(buf)
    data = buf.getvalue()

    resp = Response(data, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp.headers["Content-Disposition"] = "attachment; filename*=UTF-8''" + quote("成本核算模板示例.xlsx")
    return resp


@calculator_bp.route("/api/calculator/templates/import", methods=["POST"])
def api_import_template():
    """导入 Excel 成本明细，解析为 items 返回（不落库，供前端预览后保存）。"""
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "请选择要导入的 Excel 文件"}), 400
    try:
        items = parse_excel(file.read())
    except Exception as e:
        return jsonify({"error": f"Excel 解析失败：{e}"}), 400

    if not items:
        return jsonify({
            "error": "未解析到任何成本明细，请确保表头为：费用类型/项目名称/单位/单价/数量/小计",
        }), 400

    suggested = file.filename.rsplit(".", 1)[0].strip() or "导入模板"
    return jsonify({"items": items, "total": len(items), "suggested_name": suggested})


@calculator_bp.route("/api/calculator/templates", methods=["POST"])
def api_save_template():
    """保存当前成本明细为预设模板（支持自定义命名）。"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请提供模板数据"}), 400

    name = (data.get("name") or "").strip()
    items = data.get("items") or []
    if not name:
        return jsonify({"error": "请填写模板名称"}), 400
    if not items:
        return jsonify({"error": "模板至少需要一行成本明细"}), 400

    session = get_session()
    try:
        tpl = CostTemplate(name=name, description=(data.get("description") or "").strip())
        session.add(tpl)
        session.flush()  # 先拿到 tpl.id
        for it in items:
            unit_price = float(it.get("unit_price", 0) or 0)
            quantity = float(it.get("quantity", 1) or 1)
            session.add(CostItem(
                template_id=tpl.id,
                item_type=it.get("type", "other"),
                name=(it.get("name") or "").strip() or "未命名",
                unit=(it.get("unit") or "pcs").strip() or "pcs",
                unit_price=unit_price,
                quantity=quantity,
                subtotal=round(unit_price * quantity, 2),
            ))
        session.commit()
        return jsonify(tpl.to_dict()), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@calculator_bp.route("/api/calculator/templates/<int:template_id>")
def api_template_detail(template_id: int):
    session = get_session()
    try:
        tpl = session.query(CostTemplate).get(template_id)
        if not tpl:
            return jsonify({"error": "模板不存在"}), 404
        return jsonify(tpl.to_dict())
    finally:
        session.close()


@calculator_bp.route("/api/calculator/templates/<int:template_id>", methods=["DELETE"])
def api_delete_template(template_id: int):
    session = get_session()
    try:
        tpl = session.query(CostTemplate).get(template_id)
        if not tpl:
            return jsonify({"error": "模板不存在"}), 404
        session.delete(tpl)
        session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
