function handleSemesterChange() {
  const semesterIdEl = document.getElementById("semester_id");
  if (!semesterIdEl) return;
  const semesterId = semesterIdEl.value;

  const baseUrl =
    window.scheduleUrls && window.scheduleUrls.scheduleRoute
      ? window.scheduleUrls.scheduleRoute
      : "/dars_jadvali";
  let url = baseUrl;
  if (semesterId) {
    url += `?semester_id=${semesterId}`;
  }
  window.location.href = url;
}

function handleWeekChange() {
  const semesterIdEl = document.getElementById("semester_id");
  const weekIdEl = document.getElementById("week_id");
  if (!semesterIdEl || !weekIdEl) return;

  const semesterId = semesterIdEl.value;
  const weekId = weekIdEl.value;

  const baseUrl =
    window.scheduleUrls && window.scheduleUrls.scheduleRoute
      ? window.scheduleUrls.scheduleRoute
      : "/dars_jadvali";
  let url = baseUrl;

  const params = new URLSearchParams();
  if (semesterId) {
    params.append("semester_id", semesterId);
  }
  if (weekId) {
    params.append("week_id", weekId);
  }

  if (params.toString()) {
    url += `?${params.toString()}`;
  }
  window.location.href = url;
}

document.addEventListener("DOMContentLoaded", function () {
  const semesterSelect = document.getElementById("semester_id");
  const weekSelect = document.getElementById("week_id");

  if (semesterSelect) {
    semesterSelect.addEventListener("change", handleSemesterChange);
  }
  if (weekSelect) {
    weekSelect.addEventListener("change", handleWeekChange);
  }
});
