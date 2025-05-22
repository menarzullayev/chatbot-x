document.addEventListener("DOMContentLoaded", function () {
  const attendancePageContainer = document.querySelector("body");

  const semesterFilterHemis = document.getElementById("semesterFilterHemis");

  if (semesterFilterHemis) {
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
        if (attendanceCardsContainerHemis)
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
