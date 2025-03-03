document.addEventListener("DOMContentLoaded", function () {
  // Initialize variables
  let currentQuestion = "";
  let previousQuestions = []; // Track previously shown questions
  let aiServiceStatus = {
    available: true,
    message: ""
  };
  const questionArea = document.getElementById("questionArea");
  const currentQuestionElement = document.getElementById("currentQuestion");
  const answerInput = document.getElementById("answerInput");
  const assessmentModal = document.getElementById("assessmentModal");
  const submitButton = document.getElementById("submitAnswer");
  const spinner = document.getElementById("submitSpinner");
  const submitAnswerText = document.getElementById("submitAnswerText");

  // Create AI service status UI
  createAiStatusUI();

  // Check AI service status on load
  checkAiStatus();

  // Load roles into select from questions.json
  const roleSelect = document.getElementById("roleSelect");
  roleSelect.innerHTML = '<option value="">Select a role</option>'; // Clear any existing options
  
  fetch("../assets/questions.json")
    .then((response) => response.json())
    .then((data) => {
      data.job_roles.forEach((jobRole) => {
        const option = document.createElement("option");
        option.value = jobRole.role_name;
        option.textContent = jobRole.role_name;
        roleSelect.appendChild(option);
      });
    })
    .catch((error) => {
      console.error("Error loading roles:", error);
      roleSelect.innerHTML = '<option value="">Error loading roles</option>';
    });

  // Event Listeners
  roleSelect.addEventListener("change", function() {
    previousQuestions = [];
    loadNewQuestion();
  });
  
  submitButton.addEventListener("click", handleSubmit);
  
  document.getElementById("nextQuestion").addEventListener("click", function() {
    const nextButton = this;
    nextButton.disabled = true;
    nextButton.classList.add("opacity-50");
    loadNewQuestion();
    setTimeout(() => {
      nextButton.disabled = false;
      nextButton.classList.remove("opacity-50");
    }, 1000);
  });

  document.getElementById("closeModal").addEventListener("click", () => {
    assessmentModal.classList.add("hidden");
  });

  // Load initial analytics
  loadAnalytics();

  function createAiStatusUI() {
    // Create AI service status container
    const aiStatusContainer = document.createElement("div");
    aiStatusContainer.id = "aiStatusContainer";
    aiStatusContainer.className = "mb-6 p-4 rounded-lg border border-gray-700 mt-4";
    
    // Create status indicator
    const statusContent = `
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-semibold text-gray-300">AI Service Status</h3>
          <p id="aiStatusMessage" class="text-gray-400 text-sm mt-1">Checking status...</p>
        </div>
        <div class="flex items-center">
          <div id="aiStatusIndicator" class="w-3 h-3 rounded-full bg-yellow-500 mr-2"></div>
          <button id="reinitializeAi" class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1 rounded transition duration-300">
            Reinitialize
          </button>
        </div>
      </div>
    `;
    
    aiStatusContainer.innerHTML = statusContent;
    
    // Insert after role selection
    const roleSelect = document.getElementById("roleSelect").parentNode;
    roleSelect.parentNode.insertBefore(aiStatusContainer, roleSelect.nextSibling);
    
    // Add event listener for reinitialize button
    document.getElementById("reinitializeAi").addEventListener("click", reinitializeAi);
  }

  function checkAiStatus() {
    fetch("/ai-status")
      .then(response => response.json())
      .then(data => {
        const statusIndicator = document.getElementById("aiStatusIndicator");
        const statusMessage = document.getElementById("aiStatusMessage");
        
        if (data.success && data.ai_services) {
          const services = data.ai_services;
          
          if (services.llm && services.assessment_chain && services.question_chain && services.llm_responsive) {
            // All services are available
            statusIndicator.className = "w-3 h-3 rounded-full bg-green-500 mr-2";
            statusMessage.textContent = "AI services are available";
            statusMessage.className = "text-gray-400 text-sm mt-1";
            aiServiceStatus.available = true;
          } else {
            // Some services are unavailable
            statusIndicator.className = "w-3 h-3 rounded-full bg-red-500 mr-2";
            statusMessage.textContent = "Some AI services are unavailable. Using fallback mode.";
            statusMessage.className = "text-yellow-400 text-sm mt-1";
            aiServiceStatus.available = false;
            aiServiceStatus.message = "AI services unavailable";
          }
        } else {
          // Error checking status
          statusIndicator.className = "w-3 h-3 rounded-full bg-red-500 mr-2";
          statusMessage.textContent = "Error checking AI status. Using fallback mode.";
          statusMessage.className = "text-yellow-400 text-sm mt-1";
          aiServiceStatus.available = false;
          aiServiceStatus.message = data.message || "Error checking AI status";
        }
      })
      .catch(error => {
        console.error("Error checking AI status:", error);
        const statusIndicator = document.getElementById("aiStatusIndicator");
        const statusMessage = document.getElementById("aiStatusMessage");
        
        statusIndicator.className = "w-3 h-3 rounded-full bg-red-500 mr-2";
        statusMessage.textContent = "Error connecting to server. Using fallback mode.";
        statusMessage.className = "text-yellow-400 text-sm mt-1";
        aiServiceStatus.available = false;
        aiServiceStatus.message = "Connection error";
      });
  }

  function reinitializeAi() {
    const statusIndicator = document.getElementById("aiStatusIndicator");
    const statusMessage = document.getElementById("aiStatusMessage");
    const reinitializeButton = document.getElementById("reinitializeAi");
    
    // Show loading state
    statusIndicator.className = "w-3 h-3 rounded-full bg-yellow-500 mr-2";
    statusMessage.textContent = "Reinitializing AI services...";
    statusMessage.className = "text-gray-400 text-sm mt-1";
    reinitializeButton.disabled = true;
    reinitializeButton.classList.add("opacity-50");
    
    fetch("/reinitialize-ai", {
      method: "POST"
    })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          statusIndicator.className = "w-3 h-3 rounded-full bg-green-500 mr-2";
          statusMessage.textContent = "AI services reinitialized successfully";
          statusMessage.className = "text-green-400 text-sm mt-1";
          aiServiceStatus.available = true;
        } else {
          statusIndicator.className = "w-3 h-3 rounded-full bg-red-500 mr-2";
          statusMessage.textContent = data.message || "Failed to reinitialize AI services";
          statusMessage.className = "text-red-400 text-sm mt-1";
          aiServiceStatus.available = false;
          aiServiceStatus.message = data.message || "Reinitialization failed";
        }
      })
      .catch(error => {
        console.error("Error reinitializing AI:", error);
        statusIndicator.className = "w-3 h-3 rounded-full bg-red-500 mr-2";
        statusMessage.textContent = "Error connecting to server";
        statusMessage.className = "text-red-400 text-sm mt-1";
      })
      .finally(() => {
        reinitializeButton.disabled = false;
        reinitializeButton.classList.remove("opacity-50");
        
        // Check status again after a short delay
        setTimeout(checkAiStatus, 2000);
      });
  }

  function loadNewQuestion() {
    const role = document.getElementById("roleSelect").value;
    if (!role) {
      currentQuestionElement.textContent = "Please select a role first";
      questionArea.classList.add("hidden");
      return;
    }

    // Show loading state
    questionArea.classList.add("opacity-50");
    currentQuestionElement.textContent = "Loading question...";
    
    // Fetch questions from the JSON file
    fetch("../assets/questions.json")
      .then((response) => response.json())
      .then((data) => {
        // Find the selected role in job_roles array
        const roleData = data.job_roles.find(r => r.role_name === role);
        
        if (roleData && roleData.questions && roleData.questions.length > 0) {
          // Get available questions (excluding previously shown ones)
          let availableQuestions = roleData.questions.filter(q => !previousQuestions.includes(q));
          
          // If we've shown all questions, reset the history but avoid the last shown question
          if (availableQuestions.length === 0) {
            previousQuestions = currentQuestion ? [currentQuestion] : [];
            availableQuestions = roleData.questions.filter(q => q !== currentQuestion);
          }
          
          // Get a random question from available ones
          const randomIndex = Math.floor(Math.random() * availableQuestions.length);
          const randomQuestion = availableQuestions[randomIndex];
          
          // Add to previous questions (keep only the last 5)
          previousQuestions.push(randomQuestion);
          if (previousQuestions.length > 5) {
            previousQuestions.shift();
          }
          
          // Update UI
          questionArea.classList.remove("hidden", "opacity-50");
          currentQuestion = randomQuestion;
          currentQuestionElement.textContent = randomQuestion;
          answerInput.value = "";
        } else {
          console.error("No questions found for the selected role");
          currentQuestionElement.textContent = "No questions found for the selected role. Please try another role.";
          questionArea.classList.remove("opacity-50");
          questionArea.classList.add("hidden");
        }
      })
      .catch((error) => {
        console.error("Error loading questions:", error);
        currentQuestionElement.textContent = "Failed to load questions. Please try again.";
        questionArea.classList.remove("opacity-50");
        questionArea.classList.add("hidden");
      });
  }

  function handleSubmit() {
    if (!currentQuestion || !answerInput.value.trim()) {
      return;
    }

    // Show loading state
    submitButton.disabled = true;
    spinner.classList.remove("hidden");
    submitAnswerText.textContent = "Submitting...";

    const role = document.getElementById("roleSelect").value;
    
    fetch("/submit-answer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        role: role,
        question: currentQuestion,
        answer: answerInput.value.trim(),
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.error) {
          throw new Error(data.error);
        }
        
        // Update modal content
        document.getElementById("score").textContent = data.score;
        document.getElementById("feedback").textContent = data.feedback;
        
        // Update strengths list
        const strengthsList = document.getElementById("strengths");
        strengthsList.innerHTML = "";
        data.strengths.forEach((strength) => {
          const li = document.createElement("li");
          li.textContent = strength;
          strengthsList.appendChild(li);
        });
        
        // Update improvements list
        const improvementsList = document.getElementById("improvements");
        improvementsList.innerHTML = "";
        data.improvements.forEach((improvement) => {
          const li = document.createElement("li");
          li.textContent = improvement;
          improvementsList.appendChild(li);
        });
        
        // Show modal
        assessmentModal.classList.remove("hidden");
      })
      .catch((error) => {
        console.error("Error submitting answer:", error);
        alert("Failed to submit answer. Please try again.");
      })
      .finally(() => {
        // Reset button state
        submitButton.disabled = false;
        spinner.classList.add("hidden");
        submitAnswerText.textContent = "Submit Answer";
      });
  }

  function displayAssessment(assessment) {
    try {
      const resultsDiv = document.getElementById("assessmentResults");
      
      // Format strengths and improvements as bullet points
      const strengthsList = Array.isArray(assessment.strengths) 
        ? assessment.strengths.map(s => `<li class="mb-1">• ${s}</li>`).join('')
        : assessment.strengths.split(',').map(s => `<li class="mb-1">• ${s.trim()}</li>`).join('');
        
      const improvementsList = Array.isArray(assessment.improvements)
        ? assessment.improvements.map(i => `<li class="mb-1">• ${i}</li>`).join('')
        : assessment.improvements.split(',').map(i => `<li class="mb-1">• ${i.trim()}</li>`).join('');

      resultsDiv.innerHTML = `
        <div class="text-left space-y-4">
          <div class="bg-gray-800 p-4 rounded-lg">
            <p class="text-xl font-bold text-blue-400">Score: ${assessment.score}/100</p>
          </div>
          <div class="bg-gray-800 p-4 rounded-lg">
            <p class="font-semibold text-blue-400 mb-2">Strengths:</p>
            <ul class="text-gray-300">${strengthsList}</ul>
          </div>
          <div class="bg-gray-800 p-4 rounded-lg">
            <p class="font-semibold text-blue-400 mb-2">Areas for Improvement:</p>
            <ul class="text-gray-300">${improvementsList}</ul>
          </div>
          <div class="bg-gray-800 p-4 rounded-lg">
            <p class="font-semibold text-blue-400 mb-2">Overall Feedback:</p>
            <p class="text-gray-300">${assessment.feedback}</p>
          </div>
        </div>
      `;
      
      // Show the modal
      document.getElementById("assessmentModal").classList.remove("hidden");
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
