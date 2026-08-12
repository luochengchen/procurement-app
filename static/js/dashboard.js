// Dashboard — fetch featured materials and render stats
(async function () {
    const container = document.getElementById("featuredMaterials");

    try {
        const res = await fetch("/api/materials/featured");
        if (!res.ok) throw new Error("Failed to fetch");
        const materials = await res.json();

        // Stats
        const categories = new Set(materials.map((m) => m.category_name));
        const upCount = materials.filter((m) => m.trend === "up").length;
        const downCount = materials.filter((m) => m.trend === "down").length;
        document.getElementById("statCategories").textContent = categories.size;
        document.getElementById("statUpdated").textContent = materials.length;
        document.getElementById("statUp").textContent = upCount;
        document.getElementById("statDown").textContent = downCount;

        // Cards
        if (!materials.length) {
            container.innerHTML =
                '<p class="text-muted text-center py-4">暂无数据，请先运行 <code>python seed_data.py</code> 填充数据</p>';
            return;
        }

        const trendIcon = { up: "↑", down: "↓", stable: "→" };
        const trendClass = { up: "trend-up", down: "trend-down", stable: "trend-stable" };

        container.innerHTML = `<div class="row g-3">${materials
            .slice(0, 12)
            .map(
                (m) => `
            <div class="col-md-4 col-lg-3">
                <div class="card h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <span class="badge bg-light text-dark">${m.category_name}</span>
                            <span class="${trendClass[m.trend]} fw-bold">${trendIcon[m.trend]} ${m.current_price.toFixed(2)}</span>
                        </div>
                        <h6 class="card-title mt-2">${m.name}</h6>
                        <small class="text-muted">${m.spec} / ${m.unit}</small>
                        <div class="mt-2">
                            <small class="text-muted">${m.price_date} · ${m.price_source}</small>
                        </div>
                    </div>
                </div>
            </div>`
            )
            .join("")}</div>`;
    } catch (e) {
        container.innerHTML = `<p class="text-danger text-center py-4">加载失败: ${e.message}</p>`;
    }
})();
