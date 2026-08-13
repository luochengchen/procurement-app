// Image search — upload preview, drag & drop, search
const uploadZone = document.getElementById("uploadZone");
const fileInput = document.getElementById("fileInput");
const previewContainer = document.getElementById("previewContainer");
const previewImg = document.getElementById("previewImg");
const clearPreviewBtn = document.getElementById("clearPreview");
const searchBtn = document.getElementById("searchBtn");
const resultsContainer = document.getElementById("resultsContainer");
const searchNote = document.getElementById("searchNote");

let selectedFile = null;

// Click to select
uploadZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => handleFile(e.target.files[0]));

// Drag & drop
uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.classList.add("drag-over");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));
uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("drag-over");
    handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
    if (!file) return;
    if (!file.type.startsWith("image/")) return alert("请选择图片文件");
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewContainer.style.display = "block";
        uploadZone.style.display = "none";
        searchBtn.disabled = false;
    };
    reader.readAsDataURL(file);
}

clearPreviewBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    previewContainer.style.display = "none";
    uploadZone.style.display = "block";
    searchBtn.disabled = true;
    resultsContainer.innerHTML = '<p class="text-muted text-center py-4">上传图片后点击搜索</p>';
    searchNote.textContent = "";
});

searchBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append("image", selectedFile);
    formData.append("keyword", document.getElementById("keywordInput").value.trim());

    searchBtn.disabled = true;
    searchBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 搜索中...';
    resultsContainer.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div></div>';

    try {
        const res = await fetch("/api/image-search/upload", { method: "POST", body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        if (data.note) searchNote.textContent = data.note;

        // 工厂匹配联动：跳转到工厂模块，按识别关键词匹配可生产的工厂
        const kw = data.keyword || "";
        const matchBar = kw
            ? `<a href="/factory?q=${encodeURIComponent(kw)}" class="btn btn-outline-primary w-100 mb-3">
                 <i class="bi bi-buildings me-1"></i> 匹配可生产该产品的工厂
               </a>`
            : "";

        resultsContainer.innerHTML = matchBar + data.results
            .map(
                (r) => `
            <div class="card mb-2 supplier-card">
                <div class="card-body position-relative">
                    <span class="badge bg-primary platform-badge">${r.platform}</span>
                    <h6 class="card-title pe-5">${r.title}</h6>
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="fw-bold text-success">${r.price}</span>
                            <small class="text-muted ms-2">${r.supplier}</small>
                        </div>
                        <small class="text-muted">${r.location}</small>
                    </div>
                    <a href="${r.url}" target="_blank" class="btn btn-sm btn-outline-primary mt-2">
                        <i class="bi bi-box-arrow-up-right"></i> 查看详情
                    </a>
                </div>
            </div>`
            )
            .join("");
    } catch (e) {
        resultsContainer.innerHTML = `<p class="text-danger text-center py-4">搜索失败: ${e.message}</p>`;
    } finally {
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="bi bi-search"></i> 开始搜索';
    }
});
