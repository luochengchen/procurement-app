"""图片识别层 —— 可插拔，未配置视觉模型时诚实降级为「关键词模式」。

为什么要单独一层：
  上传图片本身不产生任何识别结果。此前接口直接回显用户填的关键词、并返回三条
  硬编码的假供应商，让「识图搜索」看起来在工作，实际什么都没做。
  本模块把「识别」这件事抽成显式依赖：配了模型就真识别，没配就明确告诉用户
  「这不是 AI 识图，是按你填的关键词在搜」。

接口协议选 OpenAI 兼容格式（POST {base}/chat/completions + image_url 传 base64），
因为国内主流视觉模型（通义千问-VL、智谱 GLM-4V、硅基流动、豆包等）都提供兼容端点，
用户换服务商只需改环境变量，不用动代码。

环境变量：
  VISION_API_URL  例如 https://dashscope.aliyuncs.com/compatible-mode/v1
  VISION_API_KEY  服务商 key
  VISION_MODEL    例如 qwen-vl-max / glm-4v / Qwen/Qwen2.5-VL-7B-Instruct
"""
from __future__ import annotations

import base64
import json
import mimetypes

import requests

from config import VISION_API_KEY, VISION_API_URL, VISION_MODEL

# 让模型只输出结构化结果，便于程序消费；同时约束关键词必须是「能拿去搜 1688/工商库的词」
_PROMPT = (
    "你是跨境电商采购选品专家。看这张产品图片，判断它是什么商品、由什么材料制成、"
    "属于什么品类，并给出最适合拿去 B2B 平台（1688/阿里巴巴）和工商企业库检索的中文关键词。\n"
    "只输出一个 JSON 对象，不要任何解释或 markdown 代码块，格式：\n"
    '{"keyword":"最核心的检索词，2-6个字","candidates":["同义词/上位词1","词2"],'
    '"category":"品类","material":"主要材质","desc":"一句话描述"}\n'
    "要求：keyword 必须是具体产品名（如「不锈钢保温杯」而不是「杯子」），"
    "candidates 给 2-3 个可替换的检索词。"
)


def _configured() -> bool:
    return bool(VISION_API_URL and VISION_API_KEY)


def _encode(filepath: str) -> str | None:
    """读取图片并转 data URL；失败返回 None。"""
    try:
        with open(filepath, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    mime = mimetypes.guess_type(filepath)[0] or "image/jpeg"
    if not mime.startswith("image/"):
        mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _parse_json(text: str) -> dict:
    """从模型回复里抠出 JSON 对象（容忍 ```json 包裹或前后有解释文字）。"""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(text[start:end + 1])
            except (ValueError, TypeError):
                pass
    return {}


def recognize(filepath: str, hint: str = "") -> dict:
    """识别图片 → 检索关键词。

    返回 {engine, keyword, candidates, category, material, desc, note}。
    engine 为 "keyword" 时表示**没有做图像识别**，只是在用用户给的关键词，
    前端必须据此如实提示，不能包装成「AI 识图成功」。
    """
    hint = (hint or "").strip()

    if not _configured():
        return {
            "engine": "keyword",
            "keyword": hint,
            "candidates": [],
            "category": "",
            "material": "",
            "desc": "",
            "note": (
                "未配置视觉模型，本次未做图像识别，仅按关键词检索。"
                "配置 VISION_API_URL / VISION_API_KEY / VISION_MODEL 后即可启用 AI 识图。"
                if hint else
                "未配置视觉模型，且未填写关键词，无法检索。请补充关键词，"
                "或配置 VISION_API_URL / VISION_API_KEY / VISION_MODEL 启用 AI 识图。"
            ),
        }

    data_url = _encode(filepath)
    if not data_url:
        return {
            "engine": "keyword", "keyword": hint, "candidates": [],
            "category": "", "material": "", "desc": "",
            "note": "图片读取失败，已按关键词检索。",
        }

    prompt = _PROMPT
    if hint:
        prompt += f"\n补充信息：用户提示这个产品可能是「{hint}」。"

    try:
        resp = requests.post(
            f"{VISION_API_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {VISION_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": VISION_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }],
                "temperature": 0.2,
            },
            timeout=30,
        )
        body = resp.json()
        if resp.status_code != 200:
            msg = (body.get("error") or {}).get("message") if isinstance(body, dict) else ""
            raise RuntimeError(msg or f"HTTP {resp.status_code}")

        content = ((body.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        parsed = _parse_json(content)
        keyword = str(parsed.get("keyword") or "").strip() or hint
        candidates = [str(c).strip() for c in (parsed.get("candidates") or []) if str(c).strip()]

        if not keyword:
            return {
                "engine": "keyword", "keyword": hint, "candidates": [],
                "category": "", "material": "", "desc": "",
                "note": "视觉模型未返回可用关键词，已按关键词检索。",
            }
        return {
            "engine": VISION_MODEL or "vision",
            "keyword": keyword,
            "candidates": candidates,
            "category": str(parsed.get("category") or "").strip(),
            "material": str(parsed.get("material") or "").strip(),
            "desc": str(parsed.get("desc") or "").strip(),
            "note": "",
        }
    except Exception as e:  # noqa: BLE001 —— 识别失败不能阻断搜索，降级到关键词
        return {
            "engine": "keyword",
            "keyword": hint,
            "candidates": [],
            "category": "", "material": "", "desc": "",
            "note": f"视觉识别调用失败（{e}），已降级为按关键词检索。",
        }
