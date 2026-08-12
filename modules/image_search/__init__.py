"""Image search module — upload product image, search suppliers across B2B platforms."""
from __future__ import annotations

import os
import uuid

from flask import Blueprint, jsonify, render_template, request
from werkzeug.utils import secure_filename

from config import ALLOWED_IMAGE_TYPES, MAX_UPLOAD_SIZE_MB, UPLOAD_DIR

image_search_bp = Blueprint("image_search", __name__, template_folder="../../templates")


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_TYPES


@image_search_bp.route("/image-search")
def page() -> str:
    return render_template("image_search.html")


@image_search_bp.route("/api/image-search/upload", methods=["POST"])
def api_upload():
    if "image" not in request.files:
        return jsonify({"error": "请上传图片文件"}), 400

    file = request.files["image"]
    if file.filename == "" or not _allowed_file(file.filename):
        return jsonify({"error": f"不支持的文件格式，允许: {', '.join(ALLOWED_IMAGE_TYPES)}"}), 400

    file.seek(0, os.SEEK_END)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > MAX_UPLOAD_SIZE_MB:
        return jsonify({"error": f"文件大小超过限制 ({MAX_UPLOAD_SIZE_MB}MB)"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    keyword = request.form.get("keyword", "").strip()

    mock_results = [
        {
            "platform": "1688",
            "title": f"厂家直销 {keyword or '同款产品'} 批发定制",
            "price": "¥12.50-18.00",
            "supplier": "义乌市XX工艺品有限公司",
            "location": "浙江 金华",
            "url": "https://detail.1688.com/offer/example.html",
        },
        {
            "platform": "Alibaba International",
            "title": f"Factory Direct {keyword or 'Product'} Custom Logo Accept",
            "price": "$1.80-2.50",
            "supplier": "Yiwu XX Crafts Co., Ltd.",
            "location": "Zhejiang, China",
            "url": "https://www.alibaba.com/product-detail/example.html",
        },
        {
            "platform": "义乌购",
            "title": f"{keyword or '热销产品'} 源头厂家 一件代发",
            "price": "¥10.00-15.00",
            "supplier": "义乌国际商贸城XX商位",
            "location": "浙江 义乌",
            "url": "https://www.yiwugo.com/product/detail/example.html",
        },
    ]

    return jsonify({
        "ok": True,
        "filename": filename,
        "keyword": keyword,
        "results": mock_results,
        "total": len(mock_results),
        "note": "当前为模拟结果。实时搜索引擎接口预留中。",
    })
