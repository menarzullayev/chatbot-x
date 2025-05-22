document.addEventListener("DOMContentLoaded", function () {
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
});
