document.addEventListener("DOMContentLoaded", function () {
  const chatForm = document.getElementById("chat-form");
  const messageInput = document.getElementById("message-input");
  const chatMessages = document.getElementById("chat-messages");
  const fileInput = document.getElementById("file-input");
  const uploadedFilesContainer = document.getElementById("uploaded-files");
  const clearHistoryBtn = document.getElementById("clear-history");

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
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
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

  if (uploadedFilesContainer) {
    uploadedFilesContainer.style.display = "none";
  }

  if (chatMessages) {
    setTimeout(function () {
      loadInitialChatHistory();
    }, 100);
  }

  function updateSidebarDateTime() {
    const currentDateEl = document.getElementById("current-date");
    const currentTimeEl = document.getElementById("current-time");
    if (!currentDateEl || !currentTimeEl) return;
    const now = new Date();
    const dateOptions = {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    };
    try {
      currentDateEl.textContent = now.toLocaleDateString(
        "uz-UZ-Cyrl",
        dateOptions
      );
    } catch (e) {
      try {
        currentDateEl.textContent = now.toLocaleDateString(
          "uz-UZ",
          dateOptions
        );
      } catch (e2) {
        currentDateEl.textContent = now.toLocaleDateString(
          undefined,
          dateOptions
        );
      }
    }
    currentTimeEl.textContent = now.toLocaleTimeString("uz-UZ", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  if (
    document.getElementById("current-date") &&
    document.getElementById("current-time")
  ) {
    updateSidebarDateTime();
    setInterval(updateSidebarDateTime, 1000);
  }

  const attendancePageContainer = document.querySelector(
    ".container h1 i.fa-user-check"
  );
  const semesterFilterHemis = document.getElementById("semesterFilterHemis");

  if (attendancePageContainer && semesterFilterHemis) {
    const viewToggleHemis = document.getElementById("viewToggleHemis");
    const attendanceCardsContainerHemis = document.getElementById(
      "attendanceCardsContainerHemis"
    );
    const attendanceTableContainerHemis = document.getElementById(
      "attendanceTableContainerHemis"
    );
    const attendanceTableBodyHemis = document.getElementById(
      "attendanceTableBodyHemis"
    );
    const loadingMessageHemis = document.getElementById("loadingMessageHemis");
    const noDataMessageHemis = document.getElementById("noDataMessageHemis");
    const attendanceStatsHemisContainer = document.getElementById(
      "attendanceStatsHemisContainer"
    );

    function showLoadingHemis(show) {
      if (loadingMessageHemis)
        loadingMessageHemis.classList.toggle("hidden", !show);
    }

    function showNoDataHemis(
      show,
      message = "Tanlangan semestr uchun davomat ma'lumotlari mavjud emas yoki ma'lumotlarni yuklashda xatolik yuz berdi."
    ) {
      if (noDataMessageHemis) {
        noDataMessageHemis.classList.toggle("hidden", !show);
        if (show && noDataMessageHemis.querySelector("p")) {
          noDataMessageHemis.querySelector("p").textContent = message;
        }
      }
    }

    function displayAttendanceHemis(apiResponse) {
      if (
        !attendanceCardsContainerHemis ||
        !attendanceTableBodyHemis ||
        !attendanceStatsHemisContainer
      ) {
        console.error("Davomat uchun HTML elementlar topilmadi.");
        return;
      }

      attendanceCardsContainerHemis.innerHTML = "";
      attendanceTableBodyHemis.innerHTML = "";

      attendanceCardsContainerHemis.classList.add("hidden");
      attendanceTableContainerHemis.classList.add("hidden");
      showNoDataHemis(false);

      if (!apiResponse || !apiResponse.success || !apiResponse.data) {
        const errorMsg =
          apiResponse && apiResponse.error
            ? apiResponse.error
            : "Davomat ma'lumotlarini yuklab bo'lmadi.";
        showNoDataHemis(true, errorMsg);
        if (attendanceStatsHemisContainer)
          attendanceStatsHemisContainer.classList.add("hidden");
        return;
      }

      const attendanceSummary = apiResponse.data;

      if (
        !attendanceSummary.records ||
        attendanceSummary.records.length === 0
      ) {
        showNoDataHemis(
          true,
          "Tanlangan mezonlar uchun davomat qaydlari topilmadi."
        );
        renderAttendanceStats(attendanceSummary);
        return;
      }

      renderAttendanceStats(attendanceSummary);

      attendanceSummary.records.forEach((item) => {
        let tagClass = "";
        const currentDisplayStatusText = item.display_status_text || "Noma'lum";

        if (item.status_type === "excused") {
          tagClass = "tag-absent-excused";
        } else if (item.status_type === "unexcused") {
          tagClass = "tag-absent-unexcused";
        } else {
          tagClass = "tag-unknown";
        }

        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
                <h2>${item.fan_nomi || "N/A"}</h2>
                <p><span class="info-label">Sana:</span> ${
                  item.dars_sanasi || "N/A"
                }</p>
                <p><span class="info-label">Vaqti:</span> ${
                  item.dars_boshlanish_vaqti || "N/A"
                } - ${item.dars_tugash_vaqti || "N/A"}</p>
                <p><span class="info-label">O'qituvchi:</span> ${
                  item.oqituvchi_ismi || "N/A"
                }</p>
                <p><span class="info-label">Mashg'ulot:</span> ${
                  item.mashgulot_turi_nomi || "N/A"
                }</p>
                <p><span class="info-label">Semestr:</span> ${
                  item.semestr_nomi || "N/A"
                }</p>
                <div>
                    <span class="info-label">Holat:</span>
                    <span class="tag ${tagClass}">${currentDisplayStatusText}</span>
                </div>
            `;
        attendanceCardsContainerHemis.appendChild(card);

        const row = attendanceTableBodyHemis.insertRow();
        row.innerHTML = `
                <td>${item.fan_nomi || "N/A"}</td>
                <td>${item.semestr_nomi || "N/A"}</td>
                <td>${item.mashgulot_turi_nomi || "N/A"}</td>
                <td>${item.dars_boshlanish_vaqti || "N/A"} - ${
          item.dars_tugash_vaqti || "N/A"
        }</td>
                <td>${item.oqituvchi_ismi || "N/A"}</td>
                <td>${item.dars_sanasi || "N/A"}</td>
                <td><span class="tag ${tagClass}">${currentDisplayStatusText}</span></td>
            `;
      });
      toggleAttendanceViewHemis();
    }

    function renderAttendanceStats(summary) {
      if (!attendanceStatsHemisContainer) return;

      if (
        typeof summary.umumiy_darslar === "undefined" &&
        typeof summary.sababli === "undefined" &&
        typeof summary.sababsiz === "undefined"
      ) {
        attendanceStatsHemisContainer.classList.add("hidden");
        attendanceStatsHemisContainer.innerHTML = "";
        return;
      }
      attendanceStatsHemisContainer.classList.remove("hidden");
      attendanceStatsHemisContainer.innerHTML = `
            <div class="stat-item">
                <span class="stat-value">${summary.umumiy_darslar || 0}</span>
                <span class="stat-label">Qoldirilgan Darslar</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" style="color: var(--present-text);">${
                  summary.sababli || 0
                }</span>
                <span class="stat-label">Sababli</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" style="color: var(--danger);">${
                  summary.sababsiz || 0
                }</span>
                <span class="stat-label">Sababsiz</span>
            </div>
        `;
    }

    function toggleAttendanceViewHemis() {
      if (
        !viewToggleHemis ||
        !attendanceCardsContainerHemis ||
        !attendanceTableContainerHemis
      ) {
        return;
      }
      const noDataIsShown =
        noDataMessageHemis && !noDataMessageHemis.classList.contains("hidden");

      if (noDataIsShown) {
        attendanceCardsContainerHemis.classList.add("hidden");
        attendanceTableContainerHemis.classList.add("hidden");
        return;
      }

      if (viewToggleHemis.value === "cards") {
        attendanceCardsContainerHemis.classList.remove("hidden");
        attendanceTableContainerHemis.classList.add("hidden");
      } else {
        attendanceCardsContainerHemis.classList.add("hidden");
        attendanceTableContainerHemis.classList.remove("hidden");
      }
    }

    async function fetchSemestersHemis() {
      if (!semesterFilterHemis) return;
      showLoadingHemis(true);
      showNoDataHemis(false);
      if (attendanceStatsHemisContainer)
        attendanceStatsHemisContainer.classList.add("hidden");

      try {
        const response = await fetch("/api/hemis/semesters");
        if (!response.ok) {
          const errorData = await response
            .json()
            .catch(() => ({ error: `Server xatoligi: ${response.status}` }));
          throw new Error(
            errorData.error ||
              `Semestrlarni yuklashda xatolik: ${response.status}`
          );
        }
        const data = await response.json();
        if (data.success && data.semesters) {
          semesterFilterHemis.innerHTML =
            '<option value="all">Barcha Semestrlar</option>';
          data.semesters.forEach((semester) => {
            const option = document.createElement("option");
            option.value = semester.id;
            option.textContent = semester.name;
            semesterFilterHemis.appendChild(option);
          });
          await fetchAttendanceDataHemis();
        } else {
          throw new Error(data.error || "Semestrlar ro'yxatini olib bo'lmadi.");
        }
      } catch (error) {
        console.error("Semestrlarni olishda xatolik:", error);
        showNoDataHemis(
          true,
          `Semestrlarni yuklashda xatolik: ${error.message}.`
        );
        showLoadingHemis(false);
      }
    }

    async function fetchAttendanceDataHemis() {
      if (!semesterFilterHemis) return;
      const selectedSemesterId = semesterFilterHemis.value;
      let url = "/api/hemis/attendance";
      if (selectedSemesterId && selectedSemesterId !== "all") {
        url += `?semester_id=${selectedSemesterId}`;
      }

      showLoadingHemis(true);
      showNoDataHemis(false);
      if (attendanceCardsContainerHemis)
        attendanceCardsContainerHemis.classList.add("hidden");
      if (attendanceTableContainerHemis)
        attendanceTableContainerHemis.classList.add("hidden");
      if (attendanceStatsHemisContainer)
        attendanceStatsHemisContainer.classList.add("hidden");

      try {
        const response = await fetch(url);
        if (!response.ok) {
          const errorData = await response
            .json()
            .catch(() => ({ error: `Server xatoligi: ${response.status}` }));
          throw new Error(
            errorData.error || `Davomatni yuklashda xatolik: ${response.status}`
          );
        }
        const data = await response.json();
        displayAttendanceHemis(data);
      } catch (error) {
        console.error("Davomat ma'lumotlarini olishda xatolik:", error);
        showNoDataHemis(true, `Davomatni yuklashda xatolik: ${error.message}.`);
        if (attendanceStatsHemisContainer) {
          attendanceStatsHemisContainer.innerHTML = "";
          attendanceStatsHemisContainer.classList.add("hidden");
        }
      } finally {
        showLoadingHemis(false);
      }
    }

    if (viewToggleHemis)
      viewToggleHemis.addEventListener("change", toggleAttendanceViewHemis);
    if (semesterFilterHemis)
      semesterFilterHemis.addEventListener("change", fetchAttendanceDataHemis);

    fetchSemestersHemis();
  }
});
