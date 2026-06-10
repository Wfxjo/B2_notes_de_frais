const uploadZone = document.getElementById("upload-zone");
const fileInput = document.getElementById("file-input");
const preview = document.getElementById("preview");
const analyzeBtn = document.getElementById("analyze-btn");
const formContainer = document.getElementById("form-container");

function handleFile(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        preview.src = e.target.result;
        preview.style.display = "block";
        analyzeBtn.style.display = "block";
    };
    reader.readAsDataURL(file);

    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
}

uploadZone.addEventListener("click", () => fileInput.click());

uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = "#2563eb";
});

uploadZone.addEventListener("dragleave", () => {
    uploadZone.style.borderColor = "#444";
});

uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = "#444";
    handleFile(e.dataTransfer.files[0]);
});

fileInput.addEventListener("change", () => handleFile(fileInput.files[0]));

analyzeBtn.addEventListener("click", () => {
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    analyzeBtn.textContent = "Analyse en cours...";
    analyzeBtn.disabled = true;

    fetch("/api/analyze", {
        method: "POST",
        body: formData
    })
    .then(res => res.text())
    .then(html => {
        formContainer.innerHTML = html;
        htmx.process(formContainer);
        analyzeBtn.textContent = "Analyser";
        analyzeBtn.disabled = false;
    })
    .catch(err => {
        formContainer.innerHTML = `<p>❌ Erreur : ${err.message}</p>`;
        analyzeBtn.textContent = "Analyser";
        analyzeBtn.disabled = false;
    });
});

document.body.addEventListener("htmx:responseError", () => {
    document.getElementById("confirmation-container").innerHTML =
        `<p>❌ Erreur serveur.</p>`;
});