// Certification query page — 支持关键词/类别/市场筛选，强制 vs 附加值分组展示
document.getElementById("queryBtn").addEventListener("click", queryCerts);

// 回车触发查询
document.getElementById("keywordInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") queryCerts();
});

// 从识图搜索联动跳转：/certification?q=<产品关键词>
const initQ = new URLSearchParams(window.location.search).get("q");
if (initQ) {
    document.getElementById("keywordInput").value = initQ;
}

// 进入页面即加载
queryCerts();

async function queryCerts() {
    const keyword = document.getElementById("keywordInput").value.trim();
    const product = document.getElementById("productFilter").value;
    const country = document.getElementById("countryFilter").value;

    const params = new URLSearchParams();
    if (keyword) params.set("q", keyword);
    if (product) params.set("product", product);
    if (country) params.set("country", country);

    const mandBody = document.getElementById("mandatoryTable");
    const valueBody = document.getElementById("valueTable");
    const hint = document.getElementById("matchHint");
    const matchCategory = document.getElementById("matchCategory");
    mandBody.innerHTML = '<tr><td colspan="6" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div> 查询中...</td></tr>';
    valueBody.innerHTML = '<tr><td colspan="6" class="text-center py-4">—</td></tr>';
    hint.classList.add("d-none");

    try {
        const res = await fetch(`/api/certification?${params}`);
        if (!res.ok) throw new Error("查询失败");
        const data = await res.json();

        // 关键词识别提示
        if (data.matched_category) {
            matchCategory.textContent = data.matched_category;
            hint.classList.remove("d-none");
        }

        const certs = data.certifications || [];
        const mandatory = certs.filter((c) => c.is_mandatory);
        const valueAdd = certs.filter((c) => !c.is_mandatory);

        renderGroup("mandatoryTable", "mandatoryCount", mandatory, false);
        renderGroup("valueTable", "valueCount", valueAdd, true);
    } catch (e) {
        mandBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">加载失败: ${e.message}</td></tr>`;
        valueBody.innerHTML = '<tr><td colspan="6" class="text-center text-danger py-4">—</td></tr>';
    }
}

function renderGroup(tableId, countId, list, isValueAdd) {
    const tbody = document.getElementById(tableId);
    const countEl = document.getElementById(countId);

    if (!list.length) {
        countEl.textContent = isValueAdd ? "" : "0 项";
        tbody.innerHTML = isValueAdd
            ? '<tr><td colspan="6" class="text-center text-muted py-3">暂无附加值认证</td></tr>'
            : '<tr><td colspan="6" class="text-center text-muted py-3">未找到匹配的强制性认证</td></tr>';
        return;
    }

    countEl.textContent = `${list.length} 项`;
    tbody.innerHTML = list
        .map((c) => {
            const note = isValueAdd
                ? (c.value_benefit || c.description || "—")
                : (c.description || "—");
            const ref = c.reference_url
                ? `<br><a href="${c.reference_url}" target="_blank">参考链接</a>`
                : "";
            return `
            <tr>
                <td><strong>${c.target_country}</strong></td>
                <td>${c.cert_name}</td>
                <td><small class="text-muted">${c.cert_body || "—"}</small></td>
                <td>${c.estimated_cost || "—"}</td>
                <td>${c.lead_time_days ? c.lead_time_days + " 天" : "—"}</td>
                <td><small>${note}</small>${ref}</td>
            </tr>`;
        })
        .join("");
}
