document.addEventListener("DOMContentLoaded", function () {
  const chatForm = document.getElementById("chat-form");
  const messageInput = document.getElementById("message-input");
  const chatMessages = document.getElementById("chat-messages");
  const fileInput = document.getElementById("file-input");
  const uploadedFilesContainer = document.getElementById("uploaded-files");
  const clearHistoryBtn = document.getElementById("clear-history");

  const emojiBtn = document.getElementById("emoji-btn");
  let emojiPicker = null;

  let files = [];

  if (fileInput) {
    fileInput.addEventListener("change", function (e) {
      files = Array.from(e.target.files);
      updateFilePreviews();
    });
  }

  function updateFilePreviews() {
    if (!uploadedFilesContainer) return;
    uploadedFilesContainer.innerHTML = "";
    if (files.length === 0) {
      uploadedFilesContainer.style.display = "none";
      return;
    }
    uploadedFilesContainer.style.display = "flex";
    files.forEach((file, index) => {
      const filePreview = document.createElement("div");
      filePreview.className = "file-preview";
      const icon = getFileIcon(file);
      const size = formatFileSize(file.size);
      filePreview.innerHTML = `
                <span class="file-icon">${icon}</span>
                <span class="file-name" title="${file.name}">${file.name}</span>
                <span class="file-size">${size}</span>
                <span class="remove-file" data-index="${index}" title="O'chirish">
                    <i class="fas fa-times"></i>
                </span>
            `;
      uploadedFilesContainer.appendChild(filePreview);
    });
    document.querySelectorAll(".remove-file").forEach((btn) => {
      btn.addEventListener("click", function () {
        const index = parseInt(this.getAttribute("data-index"));
        files.splice(index, 1);
        if (files.length === 0 && fileInput) {
          fileInput.value = "";
        }
        updateFilePreviews();
      });
    });
  }

  function getFileIcon(file) {
    if (!file || typeof file.name !== "string") {
      return '<i class="fas fa-file"></i>';
    }
    const fileType = file.type ? file.type.split("/")[0] : "";
    const fileExtension = file.name.split(".").pop().toLowerCase();
    const fileIcons = {
      image: '<i class="fas fa-image"></i>',
      application:
        file.type && file.type.includes("pdf")
          ? '<i class="fas fa-file-pdf"></i>'
          : file.type &&
            (file.type.includes("word") || file.type.includes("document"))
          ? '<i class="fas fa-file-word"></i>'
          : file.type &&
            (file.type.includes("excel") || file.type.includes("spreadsheet"))
          ? '<i class="fas fa-file-excel"></i>'
          : file.type &&
            (file.type.includes("powerpoint") ||
              file.type.includes("presentation"))
          ? '<i class="fas fa-file-powerpoint"></i>'
          : file.type &&
            (file.type.includes("zip") ||
              file.type.includes("compressed") ||
              file.type.includes("archive"))
          ? '<i class="fas fa-file-archive"></i>'
          : '<i class="fas fa-file-alt"></i>',
      text: '<i class="fas fa-file-alt"></i>',
      video: '<i class="fas fa-file-video"></i>',
      audio: '<i class="fas fa-file-audio"></i>',
    };
    const extensionIcons = {
      py: '<i class="fab fa-python"></i>',
      js: '<i class="fab fa-js-square"></i>',
      html: '<i class="fab fa-html5"></i>',
      css: '<i class="fab fa-css3-alt"></i>',
      java: '<i class="fab fa-java"></i>',
      cpp: '<i class="fas fa-file-code"></i>',
      c: '<i class="fas fa-file-code"></i>',
      csv: '<i class="fas fa-file-csv"></i>',
      xls: '<i class="fas fa-file-excel"></i>',
      xlsx: '<i class="fas fa-file-excel"></i>',
      doc: '<i class="fas fa-file-word"></i>',
      docx: '<i class="fas fa-file-word"></i>',
      ppt: '<i class="fas fa-file-powerpoint"></i>',
      pptx: '<i class="fas fa-file-powerpoint"></i>',
      txt: '<i class="fas fa-file-alt"></i>',
      md: '<i class="fab fa-markdown"></i>',
      json: '<i class="fas fa-code"></i>',
      xml: '<i class="fas fa-code"></i>',
      zip: '<i class="fas fa-file-archive"></i>',
      rar: '<i class="fas fa-file-archive"></i>',
      tar: '<i class="fas fa-file-archive"></i>',
      gz: '<i class="fas fa-file-archive"></i>',
      "7z": '<i class="fas fa-file-archive"></i>',
    };
    return (
      extensionIcons[fileExtension] ||
      fileIcons[fileType] ||
      '<i class="fas fa-file"></i>'
    );
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return "0 Bayt";
    const k = 1024;
    const sizes = ["Bayt", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  if (chatForm) {
    chatForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      const messageText = messageInput.value.trim();
      if (!messageText && files.length === 0) return;

      displayMessage(messageText, files, "user", new Date());

      const currentMessageTextForApi = messageText;
      const currentFilesForApi = [...files];

      messageInput.value = "";
      files = [];
      if (fileInput) fileInput.value = "";
      updateFilePreviews();
      messageInput.style.height = "auto";

      const loadingMsgDiv = displayMessage(
        "Javob kutilmoqda...",
        [],
        "bot",
        new Date()
      );
      if (loadingMsgDiv) loadingMsgDiv.classList.add("loading-message");

      const formData = new FormData();
      if (currentMessageTextForApi)
        formData.append("message", currentMessageTextForApi);
      currentFilesForApi.forEach((file) => {
        formData.append("files", file);
      });

      try {
        const response = await fetch("/chat/xabar_yuborish", {
          method: "POST",
          body: formData,
        });

        if (
          chatMessages &&
          loadingMsgDiv &&
          chatMessages.contains(loadingMsgDiv)
        ) {
          chatMessages.removeChild(loadingMsgDiv);
        }

        if (!response.ok) {
          let errorDetail = response.statusText || "Noma'lum server xatoligi";
          try {
            const responseText = await response.text();
            try {
              const errorData = JSON.parse(responseText);
              errorDetail =
                errorData.error ||
                errorData.xato ||
                errorData.message ||
                responseText;
            } catch (jsonParseError) {
              errorDetail =
                responseText.length < 200 && responseText.length > 0
                  ? responseText
                  : response.statusText;
            }
          } catch (readError) {
            console.error("Xatolik javobini o'qishda muammo:", readError);
          }
          throw new Error(
            `Server xatoligi: ${response.status} - ${errorDetail}`
          );
        }

        const data = await response.json();
        if (data.error || data.xato) {
          displayMessage(
            `Xatolik: ${data.error || data.xato}`,
            [],
            "bot",
            new Date()
          );
        } else {
          displayMessage(data.xabar, data.fayllar || [], "bot", new Date());
        }
      } catch (error) {
        console.error("Fetch xatoligi:", error);
        if (
          chatMessages &&
          loadingMsgDiv &&
          chatMessages.contains(loadingMsgDiv)
        ) {
          chatMessages.removeChild(loadingMsgDiv);
        }
        displayMessage(
          `Ulanishda yoki serverda xatolik: ${error.message}`,
          [],
          "bot",
          new Date()
        );
      }
    });
  }

  function displayMessage(text, attachedFiles, sender, timestamp) {
    if (!chatMessages) return null;
    const messageElement = document.createElement("div");
    messageElement.className = `message ${sender}`;
    let filesHTML = "";
    if (attachedFiles && attachedFiles.length > 0) {
      filesHTML = '<div class="message-files">';
      attachedFiles.forEach((file) => {
        let iconHTML,
          fileNameDisplay,
          fileUrlForDownload,
          previewHTML = "";
        let originalFileName;
        if (typeof file === "string") {
          let displayName = file;
          const namePartsForDisplay = file.split("_");
          if (namePartsForDisplay.length > 1) {
            const actualNameWithExt = namePartsForDisplay
              .slice(0, -1)
              .join("_");
            const lastPart =
              namePartsForDisplay[namePartsForDisplay.length - 1];
            if (lastPart.includes(".")) {
              displayName = actualNameWithExt.includes(".")
                ? actualNameWithExt
                : actualNameWithExt + "." + lastPart.split(".").slice(-1)[0];
            } else {
              displayName = actualNameWithExt;
            }
            const firstUnderscoreIndex = file.indexOf("_");
            if (
              firstUnderscoreIndex > -1 &&
              file.lastIndexOf(".") > firstUnderscoreIndex
            ) {
              displayName =
                file.substring(0, firstUnderscoreIndex) +
                file.substring(file.lastIndexOf("."));
            } else {
              displayName = file;
            }
          }
          originalFileName = displayName;
          fileNameDisplay = originalFileName;
          fileUrlForDownload = `/yuklamalar/${encodeURIComponent(file)}`;
          const ext = originalFileName.split(".").pop().toLowerCase();
          iconHTML = getFileIcon({
            name: originalFileName,
            type: `application/${ext}`,
          });
          if (["png", "jpg", "jpeg", "gif", "webp"].includes(ext)) {
            previewHTML = `<img src="${fileUrlForDownload}" alt="${fileNameDisplay}" loading="lazy">`;
          }
        } else {
          originalFileName = file.name;
          fileNameDisplay = file.name;
          iconHTML = getFileIcon(file);
          fileUrlForDownload = null;
          if (file.type.startsWith("image/")) {
            const localUrl = URL.createObjectURL(file);
            previewHTML = `<img src="${localUrl}" alt="${fileNameDisplay}" loading="lazy" onload="URL.revokeObjectURL(this.src)">`;
          }
        }
        filesHTML += `
                    <div class="message-file">
                        <span class="file-icon">${iconHTML}</span>
                        <span class="file-name" title="${fileNameDisplay}">${fileNameDisplay}</span>
                        ${
                          fileUrlForDownload
                            ? `<a href="${fileUrlForDownload}" download="${originalFileName}" title="Yuklab olish"><i class="fas fa-download"></i></a>`
                            : ""
                        }
                        ${previewHTML}
                    </div>`;
      });
      filesHTML += "</div>";
    }
    let formattedText = text || "";
    formattedText = formattedText
      .replace(/```(\w*)\n([\s\S]*?)```\n?/g, (match, lang, code) => {
        const languageClass = lang
          ? `language-${lang.toLowerCase()}`
          : "language-plaintext";
        const escapedCode = code.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        return `<div class="code-block-container"><pre><code class="${languageClass}">${escapedCode.trim()}</code></pre></div>`;
      })
      .replace(/`([^`\n]+?)`/g, "<code>$1</code>");
    if (!formattedText.includes('<div class="code-block-container">')) {
      formattedText = formattedText.replace(/\n/g, "<br>");
    }
    const timeString = timestamp
      ? timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : "";
    messageElement.innerHTML = `
            <div class="message-content">
                <div class="message-text">${formattedText}</div>
                ${filesHTML}
                <div class="message-time">${timeString}</div>
            </div>`;
    if (chatMessages) {
      chatMessages.appendChild(messageElement);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    return messageElement;
  }

  function loadInitialChatHistory() {
    if (!chatMessages) return;
    const messages = chatMessages.querySelectorAll(".message");
    messages.forEach((msgElement) => {
      const fileElements = msgElement.querySelectorAll(".message-file");
      fileElements.forEach((fileDiv) => {
        const fileNameEl = fileDiv.querySelector(".file-name");
        const fileIconEl = fileDiv.querySelector(".file-icon");
        if (fileNameEl && fileIconEl) {
          const fileName = fileNameEl.textContent || fileNameEl.innerText;
          const ext = fileName.split(".").pop().toLowerCase();
          fileIconEl.innerHTML = getFileIcon({
            name: fileName,
            type: `application/${ext}`,
          });
        }
      });
    });
    if (chatMessages.children.length > 0) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }

  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener("click", function () {
      if (
        confirm(
          "Haqiqatan ham chat tarixini tozalamoqchimisiz? Barcha suhbatlar o'chib ketadi."
        )
      ) {
        fetch("/chat/tarixni_tozalash", { method: "POST" })
          .then((response) => {
            if (!response.ok)
              throw new Error(`Server xatoligi: ${response.status}`);
            return response.json();
          })
          .then((data) => {
            if (data.muvaffaqiyat) {
              if (chatMessages) chatMessages.innerHTML = "";
              displayMessage("Chat tarixi tozalandi.", [], "bot", new Date());
            } else {
              displayMessage(
                "Tarixni tozalashda xatolik: " +
                  (data.xato || data.error || "Noma'lum xato"),
                [],
                "bot",
                new Date()
              );
            }
          })
          .catch((error) => {
            displayMessage(
              "Tarixni tozalashda xatolik yuz berdi: " + error.message,
              [],
              "bot",
              new Date()
            );
          });
      }
    });
  }

  if (messageInput) {
    messageInput.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = this.scrollHeight + "px";
    });
    messageInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey) {
        e.preventDefault();
        if (chatForm)
          chatForm.dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
          );
      } else if (e.key === "Enter" && (e.ctrlKey || e.shiftKey)) {
        setTimeout(() => this.dispatchEvent(new Event("input")), 0);
      }
    });
  }

  if (emojiBtn && messageInput) {
    emojiBtn.addEventListener("click", (event) => {
      event.stopPropagation();

      if (!emojiPicker) {
        emojiPicker = document.createElement("emoji-picker");
        emojiPicker.classList.add("light");
        document.body.appendChild(emojiPicker);

        emojiPicker.addEventListener("emoji-click", (emojiEvent) => {
          const emoji = emojiEvent.detail.unicode;
          insertEmojiAtCursor(messageInput, emoji);
          if (emojiPicker) emojiPicker.style.display = "none";
        });

        document.addEventListener(
          "click",
          function closePickerOnClickOutside(e) {
            if (emojiPicker && emojiPicker.style.display !== "none") {
              const isEmojiButtonOrChild =
                emojiBtn.contains(e.target) || e.target === emojiBtn;
              if (!isEmojiButtonOrChild && !emojiPicker.contains(e.target)) {
                emojiPicker.style.display = "none";
              }
            }
          }
        );
      }

      if (emojiPicker.style.display === "none" || !emojiPicker.style.display) {
        const chatInputContainer = document.querySelector(
          ".chat-input-container"
        );
        if (chatInputContainer) {
          const containerRect = chatInputContainer.getBoundingClientRect();
          const btnRect = emojiBtn.getBoundingClientRect();

          emojiPicker.style.position = "absolute";

          emojiPicker.style.bottom =
            window.innerHeight - containerRect.top + 10 + "px";

          let pickerLeft = btnRect.left;

          const pickerWidth = emojiPicker.offsetWidth || 320;

          if (pickerLeft + pickerWidth > window.innerWidth - 10) {
            pickerLeft = window.innerWidth - pickerWidth - 10;
          }
          if (pickerLeft < 10) {
            pickerLeft = 10;
          }

          emojiPicker.style.left = pickerLeft + "px";
          emojiPicker.style.zIndex = "1050";
        }
        emojiPicker.style.display = "block";
      } else {
        emojiPicker.style.display = "none";
      }
    });
  }

  function insertEmojiAtCursor(textarea, emoji) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const before = text.substring(0, start);
    const after = text.substring(end, text.length);
    textarea.value = before + emoji + after;
    textarea.selectionStart = textarea.selectionEnd = start + emoji.length;
    textarea.focus();
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  }

  if (uploadedFilesContainer) {
    uploadedFilesContainer.style.display = "none";
  }

  if (chatMessages) {
    setTimeout(function () {
      loadInitialChatHistory();
    }, 100);
  }
});
