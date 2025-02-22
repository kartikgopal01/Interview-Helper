document.addEventListener("DOMContentLoaded", function () {
  // Load roles into select
  fetch("/assets/questions.json")
    .then((response) => response.json())
    .then((data) => {
      const roleSelect = document.getElementById("roleSelect");
      data.job_roles.forEach((role) => {
        const option = document.createElement("option");
        option.value = role.role;
        option.textContent = role.role;
        roleSelect.appendChild(option);
      });
    });

  // Initialize variables
  let currentQuestion = "";
  const questionArea = document.getElementById("questionArea");
  const currentQuestionElement = document.getElementById("currentQuestion");
  const answerInput = document.getElementById("answerInput");
  const assessmentModal = document.getElementById("assessmentModal");
  const submitButton = document.getElementById("submitAnswer");
  const spinner = document.getElementById("submitSpinner");

  // Event Listeners
  document
    .getElementById("roleSelect")
    .addEventListener("change", loadNewQuestion);
  submitButton.addEventListener("click", handleSubmit);
  document
    .getElementById("nextQuestion")
    .addEventListener("click", loadNewQuestion);
  document.getElementById("closeModal").addEventListener("click", () => {
    assessmentModal.classList.add("hidden");
  });

  // Load initial analytics
  loadAnalytics();

  function loadNewQuestion() {
    const role = document.getElementById("roleSelect").value;
    if (!role) return;

    fetch(`/get-random-question?role=${encodeURIComponent(role)}`)
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          questionArea.classList.remove("hidden");
          currentQuestion = data.question;
          currentQuestionElement.textContent = data.question;
          answerInput.value = "";
        }
      })
      .catch((error) => {
        console.error("Error loading question:", error);
        alert("Failed to load question. Please try again.");
      });
  }

  function handleSubmit() {
    const role = document.getElementById("roleSelect").value;
    const answer = answerInput.value;

    if (!role) {
      alert("Please select a role first");
      return;
    }

    if (!answer.trim()) {
      alert("Please provide an answer");
      return;
    }

    // Show loading state
    submitButton.disabled = true;
    spinner.classList.remove("hidden");

    fetch("/submit-answer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        role: role,
        question: currentQuestion,
        answer: answer,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success && data.assessment) {
          displayAssessment(data.assessment);
          loadAnalytics();
        } else {
          throw new Error(data.message || "Failed to get assessment");
        }
      })
      .catch((error) => {
        console.error("Error submitting answer:", error);
        alert("Failed to submit answer. Please try again.");
      })
      .finally(() => {
        // Hide loading state
        submitButton.disabled = false;
        spinner.classList.add("hidden");
      });
  }

  function displayAssessment(assessment) {
    try {
      const resultsDiv = document.getElementById("assessmentResults");
      resultsDiv.innerHTML = `
                <div class="text-left space-y-4">
                    <div class="bg-gray-800 p-4 rounded-lg">
                        <p class="text-xl font-bold text-blue-400">Score: ${assessment.score}/100</p>
                    </div>
                    <div class="bg-gray-800 p-4 rounded-lg">
                        <p class="font-semibold text-blue-400">Strengths:</p>
                        <p class="text-gray-300">${assessment.strengths}</p>
                    </div>
                    <div class="bg-gray-800 p-4 rounded-lg">
                        <p class="font-semibold text-blue-400">Areas for Improvement:</p>
                        <p class="text-gray-300">${assessment.improvements}</p>
                    </div>
                    <div class="bg-gray-800 p-4 rounded-lg">
                        <p class="font-semibold text-blue-400">Overall Feedback:</p>
                        <p class="text-gray-300">${assessment.feedback}</p>
                    </div>
                </div>
            `;
      assessmentModal.classList.remove("hidden");
    } catch (error) {
      console.error("Error displaying assessment:", error);
      alert("Error displaying assessment results");
    }
  }

  function loadAnalytics() {
    fetch("/practice-analytics")
      .then((response) => response.json())
      .then((data) => {
        updateAnalyticsDisplay(data);
        updateChart(data);
      })
      .catch((error) => {
        console.error("Error loading analytics:", error);
      });
  }

  function updateAnalyticsDisplay(data) {
    const analyticsDiv = document.getElementById("analytics");
    if (!data.total_practices) {
      analyticsDiv.innerHTML = `
                <div class="bg-gray-800 p-4 rounded-lg">
                    <p class="text-gray-300">No practice attempts yet.</p>
                </div>
            `;
      return;
    }

    analyticsDiv.innerHTML = `
            <div class="space-y-4">
                <div class="bg-gray-800 p-4 rounded-lg">
                    <p class="text-blue-400 font-bold">Total Practices: 
                        <span class="text-gray-300">${
                          data.total_practices
                        }</span>
                    </p>
                    <p class="text-blue-400 font-bold">Average Score: 
                        <span class="text-gray-300">${data.average_score.toFixed(
                          2
                        )}%</span>
                    </p>
                </div>
                <div class="bg-gray-800 p-4 rounded-lg">
                    <h3 class="text-blue-400 font-bold mb-3">Performance by Role:</h3>
                    ${Object.entries(data.by_role)
                      .map(
                        ([role, stats]) => `
                        <div class="mb-2 pb-2 border-b border-gray-700">
                            <p class="text-gray-300">${role}: 
                                <span class="font-semibold">${stats.average_score.toFixed(
                                  2
                                )}%</span> 
                                <span class="text-gray-500">(${
                                  stats.count
                                } attempts)</span>
                            </p>
                        </div>
                    `
                      )
                      .join("")}
                </div>
            </div>
        `;
  }

  function updateChart(data) {
    const ctx = document.getElementById("scoreChart").getContext("2d");

    // Destroy existing chart if it exists
    if (window.practiceChart) {
      window.practiceChart.destroy();
    }

    // Create new chart
    window.practiceChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: Object.keys(data.by_role),
        datasets: [
          {
            label: "Average Score by Role",
            data: Object.values(data.by_role).map((role) => role.average_score),
            backgroundColor: "rgba(96, 165, 250, 0.5)",
            borderColor: "rgba(96, 165, 250, 1)",
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            labels: { color: "#9CA3AF" },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            grid: { color: "rgba(75, 85, 99, 0.2)" },
            ticks: {
              color: "#9CA3AF",
              callback: function (value) {
                return value + "%";
              },
            },
          },
          x: {
            grid: { color: "rgba(75, 85, 99, 0.2)" },
            ticks: { color: "#9CA3AF" },
          },
        },
      },
    });
  }
});
