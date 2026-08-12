"""Cost calculator module — raw materials, labor, utilities, processing fees."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from database import get_session
from models import CostTemplate

calculator_bp = Blueprint("calculator", __name__, template_folder="../../templates")

ITEM_TYPES = {
    "material": "原材料",
    "labor": "人力成本",
    "utility": "水电气",
    "processing_out": "委外加工",
    "processing_own": "自有产线",
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
