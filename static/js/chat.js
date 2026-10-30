// Chat: send text + any file type (progress bar, drag & drop, paste), poll for
// new messages, and embedded Jitsi video calls.
document.addEventListener("DOMContentLoaded", () => {
    const chatWindow = document.getElementById("chat-window");
    if (!chatWindow) return;

    const exchangeId = chatWindow.dataset.exchangeId;
    const videoRoom = chatWindow.dataset.videoRoom;
    const MAX_MB = parseInt(chatWindow.dataset.maxMb || "25", 10);
    const messagesEl = document.getElementById("chat-messages");
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const sendBtn = document.getElementById("chat-send");
    const errorEl = document.getElementById("chat-error");
    const fileInput = document.getElementById("chat-file-input");
    const preview = document.getElementById("attachment-preview");
    const previewThumb = document.getElementById("attachment-preview-thumb");
    const previewName = document.getElementById("attachment-preview-name");
    const previewSize = document.getElementById("attachment-preview-size");
    const previewRemove = document.getElementById("attachment-preview-remove");
    const progress = document.getElementById("upload-progress");
    const progressBar = document.getElementById("upload-progress-bar");
    const dropOverlay = document.getElementById("drop-overlay");

    let selectedFile = null;
    let lastId = 0;
    let sending = false;

    document.querySelectorAll(".chat-message").forEach((el) => {
        const id = parseInt(el.dataset.id, 10);
        if (id > lastId) lastId = id;
    });

    const ICONS = {
        pdf: "📕", doc: "📘", docx: "📘", txt: "📄", md: "📄", rtf: "📄",
        xls: "📗", xlsx: "📗", csv: "📗", ppt: "📙", pptx: "📙",
        zip: "🗜️", rar: "🗜️", "7z": "🗜️", tar: "🗜️", gz: "🗜️",
        mp3: "🎵", wav: "🎵", m4a: "🎵", flac: "🎵", ogg: "🎵",
        mp4: "🎬", mov: "🎬", webm: "🎬", mkv: "🎬", avi: "🎬",
        png: "🖼️", jpg: "🖼️", jpeg: "🖼️", gif: "🖼️", webp: "🖼️", svg: "🖼️",
        js: "🧩", py: "🧩", html: "🧩", css: "🧩", json: "🧩", java: "🧩", cpp: "🧩", c: "🧩",
    };
    function iconFor(name) {
        const ext = (name.split(".").pop() || "").toLowerCase();
        return ICONS[ext] || "📎";
    }
    function humanSize(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / 1024 / 1024).toFixed(1) + " MB";
    }

    function scrollToBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }
    scrollToBottom();

    // Fill in file-type icons on server-rendered attachment cards.
    document.querySelectorAll(".attachment-card").forEach((card) => {
        const icon = card.querySelector(".attachment-icon");
        if (icon && !icon.textContent) icon.textContent = iconFor(card.dataset.name || "");
    });

    function showError(message) {
        errorEl.textContent = message;
        errorEl.style.display = "block";
        setTimeout(() => { errorEl.style.display = "none"; }, 5000);
    }

    // ---------- Attachment selection / preview ----------
    function setFile(file) {
        if (!file) return;
        if (file.size === 0) { showError("That file is empty."); return; }
        if (file.size > MAX_MB * 1024 * 1024) {
            showError(`File is too large (max ${MAX_MB} MB).`);
            return;
        }
        selectedFile = file;
        previewName.textContent = file.name;
        previewSize.textContent = humanSize(file.size);
        previewThumb.innerHTML = "";
        if (file.type.startsWith("image/") && file.type !== "image/svg+xml") {
            const img = document.createElement("img");
            img.src = URL.createObjectURL(file);
            img.onload = () => URL.revokeObjectURL(img.src);
            previewThumb.appendChild(img);
        } else {
            previewThumb.textContent = iconFor(file.name);
        }
        preview.style.display = "flex";
    }

    function clearFile() {
        selectedFile = null;
        fileInput.value = "";
        preview.style.display = "none";
        previewThumb.innerHTML = "";
        progress.style.display = "none";
        progressBar.style.width = "0%";
    }

    fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
    previewRemove.addEventListener("click", () => { if (!sending) clearFile(); });

    // Drag & drop anywhere on the chat window
    let dragDepth = 0;
    chatWindow.addEventListener("dragenter", (e) => {
        if (!e.dataTransfer || !Array.from(e.dataTransfer.types).includes("Files")) return;
        e.preventDefault(); dragDepth++; dropOverlay.classList.add("show");
    });
    chatWindow.addEventListener("dragover", (e) => { e.preventDefault(); });
    chatWindow.addEventListener("dragleave", () => {
        dragDepth = Math.max(0, dragDepth - 1);
        if (dragDepth === 0) dropOverlay.classList.remove("show");
    });
    chatWindow.addEventListener("drop", (e) => {
        e.preventDefault(); dragDepth = 0; dropOverlay.classList.remove("show");
        if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
    });

    // Paste a screenshot / copied file straight into the box
    input.addEventListener("paste", (e) => {
        const files = e.clipboardData && e.clipboardData.files;
        if (files && files.length) { e.preventDefault(); setFile(files[0]); }
    });

    // ---------- Rendering ----------
    function renderAttachment(a, bubble) {
        if (!a) return;
        if (a.kind === "image") {
            const link = document.createElement("a");
            link.href = a.url; link.target = "_blank"; link.rel = "noopener";
            const img = document.createElement("img");
            img.src = a.url; img.alt = a.name; img.className = "chat-image";
            link.appendChild(img);
            bubble.appendChild(link);
            return;
        }
        if (a.kind === "video" || a.kind === "audio") {
            const media = document.createElement(a.kind);
            media.className = a.kind === "video" ? "chat-video" : "chat-audio";
            media.controls = true; media.preload = "metadata"; media.src = a.url;
            bubble.appendChild(media);
        }
        const card = document.createElement("a");
        card.className = "attachment-card";
        card.href = a.kind === "video" || a.kind === "audio" ? a.url + "?download=1" : a.url;
        card.target = "_blank"; card.rel = "noopener";
        card.dataset.kind = a.kind; card.dataset.name = a.name;

        const icon = document.createElement("span");
        icon.className = "attachment-icon"; icon.textContent = iconFor(a.name);
        const info = document.createElement("span");
        info.className = "attachment-info";
        const strong = document.createElement("strong"); strong.textContent = a.name;
        const small = document.createElement("small"); small.textContent = a.size_label || "";
        info.append(strong, small);
        const action = document.createElement("span");
        action.className = "attachment-action"; action.textContent = a.kind === "pdf" ? "↗" : "↓";
        card.append(icon, info, action);
        bubble.appendChild(card);
    }

    function appendMessage(msg) {
        const emptyState = document.getElementById("chat-empty-state");
        if (emptyState) emptyState.remove();
        if (messagesEl.querySelector(`[data-id="${msg.id}"]`)) return;

        const wrapper = document.createElement("div");
        wrapper.className = "chat-message " + (msg.mine ? "mine" : "theirs");
        wrapper.dataset.id = msg.id;
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";

        renderAttachment(msg.attachment, bubble);
        if (msg.body) {
            const p = document.createElement("p");
            p.textContent = msg.body;
            bubble.appendChild(p);
        }
        const meta = document.createElement("span");
        meta.className = "chat-meta";
        meta.textContent = msg.sender_username + " \u00b7 " + msg.created_at;
        bubble.appendChild(meta);

        wrapper.appendChild(bubble);
        messagesEl.appendChild(wrapper);
        if (msg.id > lastId) lastId = msg.id;
    }

    // ---------- Sending (XHR so we can show upload progress) ----------
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        if (sending) return;
        const body = input.value.trim();
        if (!body && !selectedFile) return;

        const formData = new FormData();
        formData.append("body", body);
        if (selectedFile) formData.append("file", selectedFile);

        sending = true;
        sendBtn.disabled = true;
        if (selectedFile) { progress.style.display = "block"; progressBar.style.width = "0%"; }

        const xhr = new XMLHttpRequest();
        xhr.open("POST", `/messages/${exchangeId}/send`);
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) progressBar.style.width = Math.round((e.loaded / e.total) * 100) + "%";
        };
        const finish = () => { sending = false; sendBtn.disabled = false; };
        xhr.onload = () => {
            finish();
            let data = {};
            try { data = JSON.parse(xhr.responseText); } catch (_) {}
            if (xhr.status < 200 || xhr.status >= 300) {
                showError(data.error || "Could not send message.");
                progress.style.display = "none";
                return;
            }
            appendMessage(data);
            input.value = "";
            clearFile();
            scrollToBottom();
        };
        xhr.onerror = () => { finish(); progress.style.display = "none"; showError("Network error \u2014 please try again."); };
        xhr.send(formData);
    });

    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            form.requestSubmit();
        }
    });

    // ---------- Polling ----------
    async function poll() {
        try {
            const res = await fetch(`/messages/${exchangeId}/poll?after=${lastId}`);
            if (!res.ok) return;
            const data = await res.json();
            if (data.messages && data.messages.length) {
                data.messages.forEach(appendMessage);
                scrollToBottom();
            }
        } catch (err) { /* next poll will retry */ }
    }
    setInterval(poll, 3000);

    // ---------- Video call ----------
    const videoBtn = document.getElementById("video-call-btn");
    const videoPanel = document.getElementById("video-call-panel");
    const videoFrame = document.getElementById("video-call-frame");
    const closeVideoBtn = document.getElementById("close-video-call");
    if (videoBtn) videoBtn.addEventListener("click", () => {
        videoFrame.src = `https://meet.jit.si/${encodeURIComponent(videoRoom)}#config.prejoinPageEnabled=true`;
        videoPanel.style.display = "block";
        videoPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    if (closeVideoBtn) closeVideoBtn.addEventListener("click", () => {
        videoFrame.src = "about:blank";
        videoPanel.style.display = "none";
    });
});
