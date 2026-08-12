// Materials query page
document.getElementById("searchBtn").addEventListener("click", searchMaterials);
document.getElementById("searchInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") searchMaterials();
});

// Load on page enter
searchMaterials();

async function searchMaterials() {
    const q = document.getElementById("searchInput").value.trim();
    const category = document.getElementById("categoryFilter").value;
    const sort = document.getElementById("sortBy").value;

    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    params.set("sort", sort);

    const tbody = document.getElementById("materialsTable");
    const countEl = document.getElementById("resultCount");
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4"><div class="spinner-border spinner-border-sm"></div> 查询中...</td></tr>';

    try {
        const res = await fetch(`/api/materials?${params}`);
        if (!res.ok) throw new Error("查询失败");
        const materials = await res.json();

        countEl.textContent = `共 ${materials.length} 条`;
        if (!materials.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">未找到匹配材料</td></tr>';
            return;
        }

        const trendIcon = { up: "↑", down: "↓", stable: "→" };
        const trendClass = { up: "trend-up", down: "trend-down", stable: "trend-stable" };

        tbody.innerHTML = materials
            .map(
                (m) => `
            <tr>
                <td><span class="badge bg-light text-dark">${m.category_name}</span></td>
                <td><strong>${m.name}</strong></td>
                <td>${m.spec}</td>
                <td>${m.unit}</td>
                <td><strong>${m.currency} ${m.current_price.toFixed(2)}</strong></td>
                <td><span class="${trendClass[m.trend]} fw-bold">${trendIcon[m.trend]}</span></td>
                <td>${m.price_date}</td>
                <td>${m.price_source}</td>
            </tr>`
            )
            .join("");
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">加载失败: ${e.message}</td></tr>`;
    }
}
