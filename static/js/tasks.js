document.addEventListener("DOMContentLoaded", function () {
  console.log("Tasks page JavaScript loaded successfully.");

  const taskItems = document.querySelectorAll(".task-item");

  taskItems.forEach((task) => {
    const deadlineElement = task.querySelector(".task-deadline");
    if (deadlineElement) {
      const deadlineText = deadlineElement.textContent
        .replace("Muddati:", "")
        .trim();
      try {
        const deadlineDate = new Date(deadlineText);
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const diffTime = deadlineDate - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays < 0) {
          deadlineElement.style.borderColor = "var(--danger)";
          deadlineElement.style.backgroundColor = "#dc35451a";
          deadlineElement.innerHTML +=
            ' <i class="fas fa-exclamation-triangle" title="Muddati o\'tib ketgan"></i>';
        } else if (diffDays <= 3) {
          deadlineElement.style.borderColor = "var(--warning-border, #ffeeba)";
          deadlineElement.style.color = "var(--warning-text, #856404)";
          deadlineElement.style.backgroundColor = "var(--warning-bg, #fff3cd)";
          deadlineElement.innerHTML +=
            ' <i class="fas fa-hourglass-half" title="Muddati yaqin"></i>';
        } else if (diffDays <= 7) {
          deadlineElement.style.borderColor = "var(--info-border, #bee5eb)";
          deadlineElement.style.color = "var(--info-text, #0c5460)";
          deadlineElement.style.backgroundColor = "var(--info-bg, #d1ecf1)";
        }
      } catch (e) {
        console.warn("Muddati sanasini o'qishda xatolik:", deadlineText, e);
      }
    }
  });

  const tasksList = document.querySelector(".tasks-list");
  const noTasksMessage = document.querySelector(".no-tasks-message");

  if (tasksList && tasksList.children.length === 0 && noTasksMessage) {
    tasksList.style.display = "none";
    noTasksMessage.style.display = "block";
  } else if (noTasksMessage) {
    noTasksMessage.style.display = "none";
  }
});
