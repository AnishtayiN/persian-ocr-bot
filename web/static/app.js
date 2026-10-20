document.addEventListener("DOMContentLoaded", () => {
  // Telegram WebApp Integration
  if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();
  }

  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const filePreviewCard = document.getElementById("filePreviewCard");
  const previewName = document.getElementById("previewName");
  const previewSize = document.getElementById("previewSize");
  const previewIcon = document.getElementById("previewIcon");
  const removeFileBtn = document.getElementById("removeFileBtn");
  const startOcrBtn = document.getElementById("startOcrBtn");
  const langSelect = document.getElementById("langSelect");
  const binarizeCheck = document.getElementById("binarizeCheck");
  const loadingContainer = document.getElementById("loadingContainer");
  const resultSection = document.getElementById("resultSection");
  const resultTextArea = document.getElementById("resultTextArea");
  const charCountBadge = document.getElementById("charCountBadge");
  const wordCountBadge = document.getElementById("wordCountBadge");
  const pagesBadge = document.getElementById("pagesBadge");
  const copyBtn = document.getElementById("copyBtn");
  const downloadTxtBtn = document.getElementById("downloadTxtBtn");
  const downloadDocxBtn = document.getElementById("downloadDocxBtn");
  const verifyIgBtn = document.getElementById("verifyIgBtn");
  const igCodeInput = document.getElementById("igCodeInput");

  let selectedFile = null;

  // Fetch app info (IG links, etc.)
  fetch("/api/info")
    .then(r => r.json())
    .then(data => {
      if (data.ig_url) {
        const tgBtn = document.getElementById("tgChannelBtn");
        // Update links if needed
      }
    })
    .catch(() => {});

  // Dropzone drag & drop
  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    if (dt.files && dt.files.length > 0) {
      handleFileSelected(dt.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    selectedFile = file;
    previewName.textContent = file.name;
    previewSize.textContent = (file.size / 1024).toFixed(1) + " KB";
    previewIcon.textContent = file.name.endsWith(".pdf") ? "📑" : "📸";
    
    filePreviewCard.style.display = "flex";
    startOcrBtn.disabled = false;
  }

  removeFileBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    filePreviewCard.style.display = "none";
    startOcrBtn.disabled = true;
  });

  // Start OCR
  startOcrBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    loadingContainer.style.display = "block";
    resultSection.style.display = "none";
    startOcrBtn.disabled = true;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("lang", langSelect.value);
    formData.append("binarize", binarizeCheck.checked);

    try {
      const resp = await fetch("/api/ocr", {
        method: "POST",
        body: formData
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "خطا در پردازش فایل");
      }

      const data = await resp.json();
      resultTextArea.value = data.text;
      charCountBadge.textContent = `${data.char_count.toLocaleString("fa-IR")} کاراکتر`;
      wordCountBadge.textContent = `${data.word_count.toLocaleString("fa-IR")} کلمه`;
      pagesBadge.textContent = `${data.pages.toLocaleString("fa-IR")} صفحه`;

      resultSection.style.display = "block";
      resultSection.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      alert("❌ " + err.message);
    } finally {
      loadingContainer.style.display = "none";
      startOcrBtn.disabled = false;
    }
  });

  // Copy text
  copyBtn.addEventListener("click", () => {
    if (!resultTextArea.value) return;
    navigator.clipboard.writeText(resultTextArea.value);
    const origText = copyBtn.textContent;
    copyBtn.textContent = "✅ کپی شد!";
    setTimeout(() => { copyBtn.textContent = origText; }, 2000);
  });

  // Download TXT
  downloadTxtBtn.addEventListener("click", () => {
    const text = resultTextArea.value;
    if (!text) return;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "OCR_Result.txt";
    a.click();
    URL.revokeObjectURL(url);
  });

  // Download Word (.docx)
  downloadDocxBtn.addEventListener("click", async () => {
    const text = resultTextArea.value;
    if (!text) return;

    downloadDocxBtn.textContent = "⏳ در حال ساخت فایل...";
    downloadDocxBtn.disabled = true;

    try {
      const formData = new FormData();
      formData.append("text", text);
      formData.append("title", "سند استخراج شده توسط OCR رایگان");

      const resp = await fetch("/api/export-docx", {
        method: "POST",
        body: formData
      });

      if (!resp.ok) throw new Error("خطا در ایجاد فایل ورد");

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Persian_OCR_Document.docx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("❌ " + err.message);
    } finally {
      downloadDocxBtn.textContent = "📝 دانلود فایل Word (.docx)";
      downloadDocxBtn.disabled = false;
    }
  });

  // Verify Instagram code
  verifyIgBtn.addEventListener("click", async () => {
    const code = igCodeInput.value.trim();
    if (!code) {
      alert("لطفاً ابتدا کد استوری را وارد کنید.");
      return;
    }

    try {
      const formData = new FormData();
      formData.append("code", code);
      const resp = await fetch("/api/verify-code", {
        method: "POST",
        body: formData
      });
      const data = await resp.json();
      alert((data.valid ? "🎉 " : "⚠️ ") + data.message);
      if (data.valid) {
        igCodeInput.value = "";
      }
    } catch {
      alert("خطا در اتصال به سرور");
    }
  });
});
