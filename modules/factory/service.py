"""Factory data service — real external APIs with graceful fallback.

降级链：天眼查（主，需 token）→ Apizero（保底，匿名 20 次/天）→ None（触发本地 mock 兜底）。

字段真相：
  - 工商数据（天眼查/Apizero）只有「企业名称、注册地址、注册资本、经营范围、
    法定代表人、成立日期」，**没有「年销售额」和「员工数/厂房面积」**。
  - 年销售额/员工规模/产能仅 1688 工厂 API 有（需企业资质 + 信息共享协议），后续接入。
  - 因此真实数据里 annual_revenue / employees / factory_area 归一化为 None，
    前端用 reg_capital（注册资本）体现规模、用 business_scope（经营范围）体现「能生产什么」。
"""
from __future__ import annotations

import requests

from config import APIZERO_API_KEY, TIANYANCHA_TOKEN


def _pick(mapping: dict, *keys, default=""):
    """从多个候选字段名中取第一个非空值，容错不同 API 的字段命名。"""
    for k in keys:
        v = mapping.get(k)
        if v not in (None, ""):
            return v
    return default


def _fmt_ts(value):
    """时间戳（秒/毫秒）转 'YYYY-MM-DD'，失败返回空串。"""
    if not value:
        return ""
    try:
        v = float(value)
        if v > 1e12:
            v /= 1000.0
        from datetime import datetime
        return datetime.fromtimestamp(v).strftime("%Y-%m-%d")
    except (ValueError, OSError, OverflowError):
        return str(value)


def _normalize(name, industry, region, reg_capital, business_scope,
               legal_person="", established="", credit_code="", source=""):
    """归一化为前端统一字段结构（外部数据缺失项置 None/空）。"""
    return {
        "name": name,
        "industry": industry or "工商企业",
        "region": region,
        "employees": None,          # 工商数据无员工数
        "factory_area": None,       # 工商数据无厂房面积
        "annual_revenue": None,     # 工商数据无年销售额
        "reg_capital": reg_capital,
        "business_scope": business_scope,
        "legal_person": legal_person,
        "established": established,
        "credit_code": credit_code,
        "main_products": [],
        "processes": [],
        "certifications": [],
        "export_markets": [],
        "verified": True,
        "source": source,
        "is_external": True,
    }


def search_tianyancha(query: str, limit: int = 20) -> list[dict]:
    """主 API：天眼查开放平台（免费 500 次/天）。

    1. search/2.0 按关键词搜索企业列表（名称/地址/注册资本/行业）
    2. ic/baseinfo/2.0 补全前 5 家的经营范围（「能生产什么」的法律口径）
    """
    headers = {"Authorization": TIANYANCHA_TOKEN}
    search_url = "https://open.api.tianyancha.com/services/open/search/2.0"

    resp = requests.get(
        search_url,
        params={"word": query, "pageSize": limit, "pageNum": 1},
        headers=headers,
        timeout=6,
    )
    data = resp.json()
    if data.get("error_code") != 0:
        raise RuntimeError(data.get("reason") or "天眼查调用失败")

    items = (data.get("result") or {}).get("items") or []
    factories = []
    for it in items[:limit]:
        name = _pick(it, "name")
        if not name:
            continue
        factories.append(_normalize(
            name=name,
            industry=_pick(it, "industry"),
            region=_pick(it, "regLocation", "reg_location", "location"),
            reg_capital=_pick(it, "regCapital", "reg_capital"),
            legal_person=_pick(it, "legalPersonName", "legal_person"),
            established=_fmt_ts(_pick(it, "estiblishTime", "estiblish_time", "estDate")),
            source="天眼查",
        ))

    # 补全前 5 家的经营范围
    baseinfo_url = "https://open.api.tianyancha.com/services/open/ic/baseinfo/2.0"
    for f in factories[:5]:
        try:
            r2 = requests.get(
                baseinfo_url,
                params={"keyword": f["name"]},
                headers=headers,
                timeout=6,
            )
            d2 = r2.json()
            if d2.get("error_code") == 0:
                res = d2.get("result") or {}
                f["business_scope"] = _pick(res, "businessScope", "business_scope")
                f["credit_code"] = _pick(res, "creditCode", "credit_code")
        except Exception:
            pass  # 单条经营范围补全失败不影响整体
    return factories


def search_apizero(query: str, limit: int = 20) -> list[dict]:
    """保底 API：Apizero 企业工商查询（匿名 20 次/天，无需 key 即可运行）。"""
    url = "https://v1.apizero.cn/api/company-search"
    headers = {"X-API-Key": APIZERO_API_KEY} if APIZERO_API_KEY else {}
    resp = requests.get(url, params={"name": query}, headers=headers, timeout=5)
    data = resp.json()

    # Apizero 返回结构可能在 data.list / data / 直接 list 之间，容错取值
    raw_list = None
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        d = data.get("data") if isinstance(data.get("data"), (list, dict)) else data
        if isinstance(d, list):
            raw_list = d
        elif isinstance(d, dict):
            raw_list = d.get("list") or d.get("items") or d.get("results") or []

    factories = []
    for it in (raw_list or [])[:limit]:
        name = _pick(it, "company_name", "companyName", "name", "title")
        if not name:
            continue
        factories.append(_normalize(
            name=name,
            industry=_pick(it, "industry", "category"),
            region=_pick(it, "reg_location", "regLocation", "address", "location"),
            reg_capital=_pick(it, "reg_capital", "regCapital", "capital"),
            business_scope=_pick(it, "business_scope", "businessScope", "scope"),
            legal_person=_pick(it, "legal_person", "legalPerson", "legalPersonName"),
            established=_fmt_ts(_pick(it, "establish_time", "estiblish_time", "estDate", "establish_date")),
            credit_code=_pick(it, "credit_code", "creditCode"),
            source="Apizero",
        ))
    return factories


def search_external(query: str, limit: int = 20) -> tuple[list[dict] | None, str]:
    """按降级链调用外部工厂数据 API。

    返回 (factories, source)：factories 为 None 表示全部失败（调用方用本地 mock 兜底），
    source 为实际命中的数据源名。
    """
    if TIANYANCHA_TOKEN:
        try:
            result = search_tianyancha(query, limit)
            if result:
                return result, "天眼查"
        except Exception:
            pass  # 降级到保底

    try:
        result = search_apizero(query, limit)
        if result:
            return result, "Apizero"
    except Exception:
        pass

    return None, ""
