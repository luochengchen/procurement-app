"""Competitor analysis module — pick a template, fill in, generate a ready-to-use report."""
from __future__ import annotations

import copy

from flask import Blueprint, jsonify, render_template, request

from modules.competitor.report import build_html, build_markdown
from modules.competitor.templates_data import TEMPLATE_MAP, TEMPLATES

competitor_bp = Blueprint("competitor", __name__, template_folder="../../templates")


@competitor_bp.route("/competitor")
def page() -> str:
    """Render the competitor analysis page."""
    cards = [
        {"key": t["key"], "name": t["name"], "icon": t["icon"], "tone": t["tone"], "desc": t["desc"]}
        for t in TEMPLATES
    ]
    return render_template("competitor.html", templates=cards)


@competitor_bp.route("/api/competitor/templates")
def api_templates():
    """模板列表（元信息，供页面渲染卡片）。"""
    return jsonify([
        {"key": t["key"], "name": t["name"], "icon": t["icon"], "tone": t["tone"], "desc": t["desc"]}
        for t in TEMPLATES
    ])


@competitor_bp.route("/api/competitor/templates/<key>")
def api_template_detail(key: str):
    """单模板完整内容（使用说明 + 分节字段），供前端渲染填写表单。"""
    tpl = TEMPLATE_MAP.get(key)
    if not tpl:
        return jsonify({"error": "模板不存在"}), 404
    # 深拷贝：避免调用方改动全局模板
    return jsonify(copy.deepcopy({
        "key": tpl["key"], "name": tpl["name"], "icon": tpl["icon"],
        "tone": tpl["tone"], "desc": tpl["desc"], "guide": tpl["guide"],
        "sections": tpl["sections"],
    }))


@competitor_bp.route("/api/competitor/report", methods=["POST"])
def api_generate_report():
    """根据填写的 answers 生成竞品分析报告，返回 Markdown + HTML + 文件名。"""
    data = request.get_json(silent=True) or {}
    key = (data.get("template_key") or "").strip()
    answers = data.get("answers") if isinstance(data.get("answers"), dict) else {}

    tpl = TEMPLATE_MAP.get(key)
    if not tpl:
        return jsonify({"error": "请先选择有效的分析模板"}), 400

    try:
        markdown = build_markdown(tpl, answers)
        document = build_html(tpl, answers)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"报告生成失败：{e}"}), 400

    return jsonify({
        "ok": True,
        "template_key": tpl["key"],
        "template_name": tpl["name"],
        "filename": f"{tpl['name']}_竞品分析",
        "markdown": markdown,
        "html": document,
    })
