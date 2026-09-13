"""Image search module — upload a product photo, recognise it, match real factories.

流程：上传图片 → vision.recognize() 得到检索关键词 → 调用真实工厂数据源匹配工厂。

设计取舍：
  - 图片只用于识别，**不长期落盘**（Render 的 UPLOAD_DIR 指向 /tmp，重启即失，
    存下来只会造成「上传了却找不到」的错觉）。识别完立即删除临时文件。
  - 此前接口返回三条硬编码的假供应商（「义乌市XX工艺品有限公司」），
    用户在界面上看不出是假的。现在改为返回真实工商数据匹配到的工厂，
    拿不到数据时返回空列表 + 明确的降级原因，不再编造。
"""
from __future__ import annotations

import os
import tempfile

from flask import Blueprint, jsonify, render_template, request

from config import ALLOWED_IMAGE_TYPES, MAX_UPLOAD_SIZE_MB, VISION_API_KEY, VISION_API_URL
from modules.image_search.vision import recognize

image_search_bp = Blueprint("image_search", __name__, template_folder="../../templates")


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_TYPES


@image_search_bp.route("/image-search")
def page() -> str:
    return render_template("image_search.html", vision_enabled=bool(VISION_API_URL and VISION_API_KEY))


@image_search_bp.route("/api/image-search/status")
def api_status():
    """告知前端当前是否启用了 AI 识图，用于页面顶部如实提示用户。"""
    enabled = bool(VISION_API_URL and VISION_API_KEY)
    return jsonify({
        "vision_enabled": enabled,
        "note": "" if enabled else (
            "当前未配置视觉模型：上传图片不会做图像识别，"
            "需要你填写关键词才能检索。配置 VISION_API_URL / VISION_API_KEY / VISION_MODEL 后可启用。"
        ),
    })


@image_search_bp.route("/api/image-search/upload", methods=["POST"])
def api_upload():
    """上传图片 → 识别 → 用识别出的关键词匹配真实工厂。"""
    if "image" not in request.files:
        return jsonify({"error": "请上传图片文件"}), 400

    file = request.files["image"]
    if file.filename == "" or not _allowed_file(file.filename):
        return jsonify({"error": f"不支持的文件格式，允许: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"}), 400

    file.seek(0, os.SEEK_END)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > MAX_UPLOAD_SIZE_MB:
        return jsonify({"error": f"文件大小超过限制 ({MAX_UPLOAD_SIZE_MB}MB)"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    hint = request.form.get("keyword", "").strip()

    # 临时文件仅用于识别，finally 里一定删除
    fd, tmp_path = tempfile.mkstemp(suffix=f".{ext}")
    os.close(fd)
    try:
        file.save(tmp_path)
        result = recognize(tmp_path, hint)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass  # 删除失败不影响本次响应；/tmp 由系统回收

    keyword = (result.get("keyword") or "").strip()
    factories, total, notice, source = [], 0, result.get("note", ""), ""

    if keyword:
        try:
            from modules.factory import FACTORIES
            from modules.factory.service import search_external_multi

            external, source, _keywords, api_notice = search_external_multi(keyword)
            if external:
                for i, f in enumerate(external):
                    f["id"] = 1000 + i
                factories, total = external[:20], len(external)
            else:
                # 外部不可用时回退本地演示库，并如实说明
                from modules.factory import _match_text
                q = keyword.lower()
                factories = [dict(f) for f in FACTORIES if _match_text(f, q)][:20]
                total = len(factories)
                source = "本地模拟"
            if api_notice and not notice:
                notice = api_notice
        except Exception as e:  # noqa: BLE001 —— 工厂检索失败不应让整个识图流程失败
            notice = (notice + " " if notice else "") + f"工厂匹配失败：{e}"

    return jsonify({
        "ok": True,
        "engine": result.get("engine", "keyword"),
        "keyword": keyword,
        "candidates": result.get("candidates", []),
        "category": result.get("category", ""),
        "material": result.get("material", ""),
        "desc": result.get("desc", ""),
        "note": notice,
        "factories": factories,
        "total": total,
        "data_source": source,
        "links": [
            {"label": "工厂匹配页", "url": f"/factory?q={keyword}"},
            {"label": "认证查询", "url": f"/certification?q={keyword}"},
        ] if keyword else [],
    })
