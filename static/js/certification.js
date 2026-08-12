// Certification query page
document.getElementById("queryBtn").addEventListener("click", queryCerts);

// Load on page enter
queryCerts();

async function queryCerts() {
    const product = document.getElementById("productFilter").value;
    const country = document.getElementById("countryFilter").value;

    const params = new URLSearchParams();
    if (product) params.set("product", product);
    if (country) params.set("country", country);

    const tbody = document.getElementById("certTable");
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div> 查询中...</td></tr>';

    try {
        const res = await fetch(`/api/certification?${params}`);
        if (!res.ok) throw new Error("查询失败");
        const certs = await res.json();

        if (!certs.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">未找到匹配的认证要求</td></tr>';
            return;
        }

        tbody.innerHTML = certs
            .map(
                (c) => `
            <tr>
                <td>${c.product_category}</td>
                <td><strong>${c.target_country}</strong></td>
                <td>${c.cert_name}</td>
                <td>${c.cert_body}</td>
                <td>${c.is_mandatory ? '<span class="cert-badge-mandatory">强制</span>' : '<span class="cert-badge-optional">可选</span>'}</td>
                <td>${c.estimated_cost}</td>
                <td>${c.lead_time_days}</td>
                <td><small>${c.description}</small>${c.reference_url ? `<br><a href="${c.reference_url}" target="_blank">参考链接</a>` : ""}</td>
            </tr>`
            )
            .join("");
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">加载失败: ${e.message}</td></tr>`;
    }
}
