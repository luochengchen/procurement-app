"""Factory data service — real external APIs with graceful fallback.

降级链：天眼查（主，需 token）→ Apizero（保底，匿名 20 次/天）→ None（触发本地 mock 兜底）。

字段真相（基于真实接口返回实测）：
  - 工商数据（天眼查/Apizero）只有「企业名称、注册地址、注册资本、经营范围、
    法定代表人、成立日期、联系方式、登记状态、企业类型」。
    **没有「年销售额」「员工数」「厂房面积」** —— 这是数据源本身的边界，不是实现缺陷。
  - 因此本模块不再伪造这三个字段，而是把「经营范围」解析成采购真正要的结论：
    能生产什么（main_products）、属于什么行业（industry）、是不是生产型厂家
    （is_manufacturer）、有没有出口资质（can_export）、规模档位（scale_label + 口径说明）。
  - 年销售额/员工规模/产能仅 1688 工厂 API 有（需企业资质 + 信息共享协议），后续接入。

额度约束：Apizero 匿名仅 20 次/天，单次搜索只返回 5 条。为在额度内提升结果量，
搜索走「多关键词并发聚合 + 进程内 TTL 缓存」：同一关键词 30 分钟内不重复消耗额度。
"""
from __future__ import annotations

import time

import requests

from config import APIZERO_API_KEY, TIANYANCHA_TOKEN
from modules.factory.industry_belt import (
    belt_bonus,
    belt_of,
    can_export,
    extract_products,
    infer_industry,
    is_manufacturer,
    related_terms,
    scale_from_capital,
)

# 进程内结果缓存：{cache_key: (expire_ts, results)}
_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 30 * 60  # 30 分钟


class FactoryAPIError(RuntimeError):
    """外部工厂数据源的业务错误（额度用尽/缺 Key/限流）。

    与网络异常区分开：这类错误必须透传到前端，否则用户只会看到「悄悄降级成模拟数据」，
    完全不知道真实原因。
    """


def _pick(mapping: dict, *keys, default=""):
    """从多个候选字段名中取第一个非空值，容错不同 API 的字段命名。"""
    for k in keys:
        v = mapping.get(k)
        if v not in (None, ""):
            return v
    return default


def _fmt_ts(value):
    """时间戳（秒/毫秒）转 'YYYY-MM-DD'，失败返回原值。"""
    if not value:
        return ""
    if isinstance(value, str) and "-" in value:
        return value[:10]
    try:
        v = float(value)
        if v > 1e12:
            v /= 1000.0
        from datetime import datetime
        return datetime.fromtimestamp(v).strftime("%Y-%m-%d")
    except (ValueError, OSError, OverflowError):
        return str(value)


def _normalize(name, industry="", region="", reg_capital="", business_scope="",
               legal_person="", established="", credit_code="", source="",
               city="", district="", phone="", email="", english_name="",
               reg_status="", company_org_type=""):
    """归一化为前端统一字段结构。

    工商事实直接透传；「行业/产品/生产型/出口/规模」五项由经营范围与注册资本派生，
    派生不出来的留空，前端据此隐藏该列而不是显示假数据。
    """
    scope = business_scope or ""
    scale_label, scale_basis = scale_from_capital(reg_capital)
    belt = belt_of(city or region)
    inferred = industry or infer_industry(scope)

    return {
        # ---- 工商事实 ----
        "name": name,
        "english_name": english_name,
        "industry": inferred or "工商企业",
        "region": region,
        "city": city,
        "district": district,
        "reg_capital": reg_capital,
        "business_scope": scope,
        "legal_person": legal_person,
        "established": established,
        "credit_code": credit_code,
        "phone": phone,
        "email": email,
        "reg_status": reg_status,
        "company_org_type": company_org_type,
        # ---- 派生结论 ----
        "main_products": extract_products(scope),
        "is_manufacturer": is_manufacturer(scope),
        "can_export": can_export(scope),
        "scale_label": scale_label,
        "scale_basis": scale_basis,
        "belt": belt["name"] if belt else "",
        # ---- 工商数据不提供的字段，保持 None 而不是编造 ----
        "employees": None,
        "factory_area": None,
        "annual_revenue": None,
        "processes": [],
        "certifications": [],
        "export_markets": [],
        # ---- 元信息 ----
        "verified": True,
        "source": source,
        "is_external": True,
    }


def search_tianyancha(query: str, limit: int = 20) -> list[dict]:
    """主 API：天眼查开放平台（免费 500 次/天）。

    1. search/2.0 按关键词搜索企业列表
    2. ic/baseinfo/2.0 补全前 5 家的经营范围（行业/产品/生产型判断都依赖它）
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
            region=_pick(it, "regLocation", "reg_location", "location"),
            reg_capital=_pick(it, "regCapital", "reg_capital"),
            legal_person=_pick(it, "legalPersonName", "legal_person"),
            established=_fmt_ts(_pick(it, "estiblishTime", "estiblish_time", "estDate")),
            phone=_pick(it, "phoneNum", "phone"),
            email=_pick(it, "email"),
            source="天眼查",
        ))

    # 补全前 5 家的经营范围 —— 行业/产品/生产型/出口判断全靠它
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
                f["reg_status"] = _pick(res, "regStatus", "reg_status")
                f["company_org_type"] = _pick(res, "companyOrgType", "company_org_type")
                f["english_name"] = _pick(res, "property3", "englishName")
                _reapply_derived(f)
        except Exception:
            pass  # 单条经营范围补全失败不影响整体
    return factories


def _apizero_get(url: str, params: dict, headers: dict, retries: int = 1) -> dict:
    """调用 Apizero 并把业务错误码翻译成 FactoryAPIError。

    实测错误码：4029「调用过快」（并发请求会触发，退避后重试一次即可）、
    4030「未携带 API Key，匿名试用次数已用完」（必须让用户看到，否则会误以为数据源坏了）。
    """
    for attempt in range(retries + 1):
        resp = requests.get(url, params=params, headers=headers, timeout=6)
        data = resp.json()
        code = data.get("code") if isinstance(data, dict) else None
        if code in (0, None):
            return data
        if code == 4029 and attempt < retries:
            time.sleep(0.8)  # 退避后重试，避免并发扇出时自己把自己限流
            continue
        if code == 4030:
            raise FactoryAPIError(
                "企业数据服务匿名额度已用完。配置环境变量 APIZERO_API_KEY"
                "（apizero.cn 可免费注册）后即可恢复真实工厂数据。"
            )
        raise FactoryAPIError(f"企业数据服务返回错误：{data.get('msg') or code}")
    return {}


def search_apizero(query: str, limit: int = 20) -> list[dict]:
    """保底 API：Apizero 企业工商查询（匿名 20 次/天，无需 key 即可运行）。

    实测该接口**恒定返回 5 条**（不受 pageSize 影响），因此调用方需自行多关键词聚合。
    """
    url = "https://v1.apizero.cn/api/company-search"
    headers = {"X-API-Key": APIZERO_API_KEY} if APIZERO_API_KEY else {}
    data = _apizero_get(url, {"name": query}, headers)

    # 返回结构可能在 data.list / data / 直接 list 之间，容错取值
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
            # 注意：不要用 category 当行业 —— 实测它给的是「批发业」这类国民经济行业分类，
            # 与采购关心的「五金配件/塑料制品」不是一个维度。行业一律由经营范围推断。
            industry="",
            region=_pick(it, "reg_location", "regLocation", "address", "location"),
            reg_capital=_pick(it, "reg_capital", "regCapital", "capital"),
            business_scope=_pick(it, "business_scope", "businessScope", "scope"),
            legal_person=_pick(it, "legal_person", "legalPerson", "legalPersonName"),
            established=_fmt_ts(_pick(it, "establish_time", "estiblish_time", "estDate",
                                      "establish_date")),
            credit_code=_pick(it, "credit_code", "creditCode"),
            city=_pick(it, "city"),
            district=_pick(it, "district"),
            phone=_pick(it, "phone"),
            email=_pick(it, "email"),
            english_name=_pick(it, "english_name", "englishName"),
            reg_status=_pick(it, "reg_status", "regStatus"),
            company_org_type=_pick(it, "company_org_type", "companyOrgType"),
            source="Apizero",
        ))
    return factories


def _reapply_derived(factory: dict) -> None:
    """经营范围在补全后才拿到时，重算依赖它的派生字段。"""
    scope = factory.get("business_scope") or ""
    if not scope:
        return
    factory["main_products"] = extract_products(scope)
    factory["is_manufacturer"] = is_manufacturer(scope)
    factory["can_export"] = can_export(scope)
    if factory.get("industry") in ("", "工商企业"):
        factory["industry"] = infer_industry(scope) or "工商企业"


def _score(factory: dict, query: str) -> int:
    """相关度打分：厂名直接命中 > 生产型厂家 > 落在对应产业带 > 有联系方式。"""
    q = (query or "").lower()
    score = 0
    if q and q in (factory.get("name") or "").lower():
        score += 3
    if factory.get("is_manufacturer"):
        score += 2
    if factory.get("can_export"):
        score += 1
    score += belt_bonus(factory.get("industry", ""), belt_of(factory.get("city") or ""))
    if factory.get("phone") or factory.get("email"):
        score += 1
    return score


def _dedupe(factories: list[dict]) -> list[dict]:
    """按统一社会信用代码去重（缺失时退回企业全名）。"""
    seen: set[str] = set()
    out: list[dict] = []
    for f in factories:
        key = f.get("credit_code") or f.get("name") or ""
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def _cached(key: str) -> list[dict] | None:
    hit = _CACHE.get(key)
    if not hit:
        return None
    expire, value = hit
    if time.time() > expire:
        _CACHE.pop(key, None)
        return None
    return value


def _store(key: str, value: list[dict]) -> list[dict]:
    # 简单的容量保护，避免长期运行内存无上限
    if len(_CACHE) > 200:
        _CACHE.clear()
    _CACHE[key] = (time.time() + _CACHE_TTL, value)
    return value


def search_external(query: str, limit: int = 20) -> tuple[list[dict] | None, str, str]:
    """按降级链调用外部工厂数据 API（单关键词）。

    返回 (factories, source, notice)：factories 为 None 表示全部失败（调用方用本地兜底），
    notice 为需要展示给用户的降级原因（额度用尽/缺 Key 等），无异常时为空串。
    """
    query = (query or "").strip()
    if not query:
        return None, "", ""

    cache_key = f"{query}|{limit}"
    cached = _cached(cache_key)
    if cached is not None:
        return cached, "天眼查" if TIANYANCHA_TOKEN else "Apizero", ""

    notices: list[str] = []

    if TIANYANCHA_TOKEN:
        try:
            result = search_tianyancha(query, limit)
            if result:
                return _store(cache_key, result), "天眼查", ""
        except FactoryAPIError as e:
            notices.append(str(e))
        except Exception:
            pass  # 网络异常，静默降级到保底

    try:
        result = search_apizero(query, limit)
        if result:
            return _store(cache_key, result), "Apizero", ""
    except FactoryAPIError as e:
        notices.append(str(e))
    except Exception:
        pass

    return None, "", "；".join(notices)


def _expand_queries(query: str) -> list[str]:
    """检索词扩展：原词 + 同义词/上位词。

    已配置 API Key 时扇出 3 词，匿名（Apizero 仅 20 次/天）时收敛到 2 词以节省额度。
    """
    fanout = 3 if (APIZERO_API_KEY or TIANYANCHA_TOKEN) else 2
    queries = [query] + related_terms(query, limit=fanout - 1)
    return queries[:fanout]


def search_external_multi(query: str, limit: int = 30) -> tuple[list[dict] | None, str, list[str], str]:
    """多关键词聚合搜索 —— 解决「单次只返回 5 条」的核心手段。

    工商库按企业名称检索，同一件东西换个叫法就命中另一批企业。跑「产品词 + 同义词 +
    上位行业词」再合并去重，结果量可从 5 条提升到 15-30 条，覆盖面更接近真实产业分布。

    调用节奏刻意保持**串行**：实测并发扇出会直接触发上游限流（错误码 4029），
    串行的额外延迟（约 1 秒）远小于被限流后拿不到数据的代价。

    返回 (factories, source, keywords, notice)；factories 为 None 表示全部失败。
    """
    query = (query or "").strip()
    if not query:
        return None, "", [], ""

    cache_key = f"multi|{query}|{limit}"
    cached = _cached(cache_key)
    if cached is not None:
        source = "天眼查" if TIANYANCHA_TOKEN else "Apizero"
        return cached, source, _expand_queries(query), ""

    keywords = _expand_queries(query)
    source = "天眼查" if TIANYANCHA_TOKEN else "Apizero"

    merged: list[dict] = []
    notices: list[str] = []
    for kw in keywords:
        try:
            result, _, notice = search_external(kw, limit)
        except Exception:
            continue
        if result:
            merged.extend(result)
        elif notice and notice not in notices:
            notices.append(notice)

    notice = "；".join(notices)
    if not merged:
        return None, "", keywords, notice

    merged = _dedupe(merged)
    merged.sort(key=lambda f: _score(f, query), reverse=True)
    merged = merged[:limit]
    return _store(cache_key, merged), source, keywords, notice
