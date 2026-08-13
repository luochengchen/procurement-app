// Factory matching — search factories by product/region/scale, view detail
let factoryModal = null;

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("searchBtn").addEventListener("click", searchFactories);
    document.getElementById("searchInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter") searchFactories();
    });
    factoryModal = new bootstrap.Modal(document.getElementById("factoryModal"));

    // 支持从识图搜索联动跳转：/factory?q=<产品关键词>
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
        document.getElementById("searchInput").value = q;
        searchFactories();
    }
});

function fmtRevenue(v) {
    // 年销售额单位：万元 → 自动转「亿/万」
    if (v >= 10000) return `${(v / 10000).toFixed(1)}亿`;
    return `${v}万`;
}

async function searchFactories() {
    const q = document.getElementById("searchInput").value.trim();
    const region = document.getElementById("regionFilter").value;
    const industry = document.getElementById("industryFilter").value;
    const scale = document.getElementById("scaleFilter").value;
    const sort = document.getElementById("sortBy").value;

    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (region) params.set("region", region);
    if (industry) params.set("industry", industry);
    if (scale) params.set("scale", scale);
    params.set("sort", sort);

    const tbody = document.getElementById("factoryTable");
    const countEl = document.getElementById("resultCount");
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div> 匹配中...</td></tr>';

    try {
        const res = await fetch(`/api/factory?${params}`);
        if (!res.ok) throw new Error("查询失败");
        const data = await res.json();

        countEl.textContent = `共 ${data.total} 家工厂`;
        if (!data.total) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">未找到匹配的工厂，换个关键词试试</td></tr>';
            return;
        }

        tbody.innerHTML = data.results.map(renderFactoryRow).join("");

        tbody.querySelectorAll(".view-detail").forEach((btn) => {
            btn.addEventListener("click", () => openDetail(btn.dataset.id));
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">加载失败: ${e.message}</td></tr>`;
    }
}

function renderFactoryRow(f) {
    const matched = new Set(f.matched_products || []);
    const products = f.main_products
        .map((p) => {
            const cls = matched.has(p) ? "badge-soft" : "text-muted";
            const check = matched.has(p) ? " <i class='bi bi-check2'></i>" : "";
            return `<span class="badge border ${matched.has(p) ? "badge-soft" : ""}" style="margin:1px">${p}${check}</span>`;
        })
        .join("");

    return `
    <tr>
        <td>
            <div class="fw-semibold">${f.name}
                ${f.verified ? '<i class="bi bi-patch-check-fill text-primary ms-1" title="已验证"></i>' : ""}
            </div>
            <small class="text-muted">${f.certifications.slice(0, 2).join(" · ")}</small>
        </td>
        <td><span class="badge-soft">${f.industry}</span></td>
        <td class="text-muted">${f.region}</td>
        <td><small>${f.employees}人 · ${(f.factory_area / 10000).toFixed(1)}万㎡</small></td>
        <td><strong style="font-variant-numeric: tabular-nums">${fmtRevenue(f.annual_revenue)}</strong></td>
        <td>${products}</td>
        <td class="text-end">
            <button class="btn btn-sm btn-outline-primary view-detail" data-id="${f.id}">
                <i class="bi bi-eye"></i>
            </button>
        </td>
    </tr>`;
}

async function openDetail(id) {
    try {
        const res = await fetch(`/api/factory/${id}`);
        if (!res.ok) throw new Error("加载详情失败");
        const f = await res.json();

        document.getElementById("factoryTitle").textContent = f.name;
        document.getElementById("factoryBody").innerHTML = `
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="text-muted small">行业</div>
                    <div class="fw-semibold">${f.industry}</div>
                </div>
                <div class="col-md-6">
                    <div class="text-muted small">地址</div>
                    <div class="fw-semibold">${f.region}</div>
                </div>
                <div class="col-md-6">
                    <div class="text-muted small">员工规模</div>
                    <div class="fw-semibold">${f.employees} 人</div>
                </div>
                <div class="col-md-6">
                    <div class="text-muted small">厂房面积</div>
                    <div class="fw-semibold">${f.factory_area.toLocaleString()} ㎡</div>
                </div>
                <div class="col-md-6">
                    <div class="text-muted small">年销售额</div>
                    <div class="fw-semibold" style="color: var(--primary)">${fmtRevenue(f.annual_revenue)}</div>
                </div>
                <div class="col-md-6">
                    <div class="text-muted small">数据来源</div>
                    <div class="fw-semibold">${f.source} ${f.verified ? "（已认证）" : ""}</div>
                </div>
                <div class="col-12">
                    <div class="text-muted small mb-1">可生产产品</div>
                    <div>${f.main_products.map((p) => `<span class="badge-soft me-1">${p}</span>`).join("")}</div>
                </div>
                <div class="col-12">
                    <div class="text-muted small mb-1">加工工艺</div>
                    <div>${f.processes.map((p) => `<span class="badge border me-1">${p}</span>`).join("")}</div>
                </div>
                <div class="col-12">
                    <div class="text-muted small mb-1">资质认证</div>
                    <div>${f.certifications.map((c) => `<span class="badge-soft me-1">${c}</span>`).join("")}</div>
                </div>
                <div class="col-12">
                    <div class="text-muted small mb-1">主要出口市场</div>
                    <div>${f.export_markets.map((m) => `<span class="badge border me-1">${m}</span>`).join("")}</div>
                </div>
            </div>`;
        factoryModal.show();
    } catch (e) {
        alert(e.message);
    }
}
