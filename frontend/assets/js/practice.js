document.addEventListener("DOMContentLoaded", function () {
  // Initialize variables
  let currentQuestion = "";
  let previousQuestions = []; // Track previously shown questions
  let isAIReady = false;
  const questionArea = document.getElementById("questionArea");
  const currentQuestionElement = document.getElementById("currentQuestion");
  const answerInput = document.getElementById("answerInput");
  const assessmentModal = document.getElementById("assessmentModal");
  const submitButton = document.getElementById("submitAnswer");
  const spinner = document.getElementById("submitSpinner");
  const submitAnswerText = document.getElementById("submitAnswerText");

  function updateAIStatus(status, message) {
    const indicator = document.getElementById('aiStatusIndicator');
    const messageEl = document.getElementById('aiStatusMessage');
    
    if (status === 'ready') {
      indicator.className = 'w-3 h-3 rounded-full bg-green-500 mr-2';
      isAIReady = true;
    } else if (status === 'error') {
      indicator.className = 'w-3 h-3 rounded-full bg-red-500 mr-2';
      isAIReady = false;
    } else {
      indicator.className = 'w-3 h-3 rounded-full bg-yellow-500 mr-2';
      isAIReady = false;
    }
    
    messageEl.textContent = message || 'AI Service Status: ' + status;
  }

  async function checkAIStatus() {
    try {
      const response = await fetch('/ai-status');
      const data = await response.json();
      
      if (data.success) {
        updateAIStatus('ready', 'AI Service Status: Ready');
      } else {
        updateAIStatus('error', data.ai_services?.message || 'AI Service Error');
      }
    } catch (error) {
      console.error('Error checking AI status:', error);
      updateAIStatus('error', 'Failed to check AI status');
    }
  }

  async function reinitializeAI() {
    try {
      updateAIStatus('initializing', 'Reinitializing AI Services...');
      
      const response = await fetch('/reinitialize-ai', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      
      if (data.success) {
        updateAIStatus('ready', 'AI Services Reinitialized Successfully');
      } else {
        updateAIStatus('error', data.message || 'Failed to reinitialize AI');
      }
    } catch (error) {
      console.error('Error reinitializing AI:', error);
      updateAIStatus('error', 'Failed to reinitialize AI');
    }
  }

  async function submitAnswer() {
    if (!isAIReady) {
      alert('Please wait for AI services to be ready before submitting.');
      return;
    }
    
    const answer = document.getElementById('answerInput').value.trim();
    const question = document.getElementById('currentQuestion').textContent.trim();
    const role = document.getElementById('roleSelect').value;
    
    if (!question || !answer) {
      alert('Please make sure you have a question and answer before submitting.');
      return;
    }

    if (!role) {
      alert('Please select a role before submitting.');
      return;
    }

    // Show loading state
    submitButton.disabled = true;
    submitAnswerText.textContent = 'Submitting...';
    spinner.classList.remove('hidden');
    
    try {
      const response = await fetch('/submit-answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          role: role,
          question: question,
          answer: answer
        })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || data.details || 'Failed to submit answer');
      }
      
      // If we got here, the assessment was successful
      displayAssessment(data);
      
    } catch (error) {
      console.error('Error submitting answer:', error);
      alert(error.message || 'Failed to submit answer. Please try again.');
      
      // If AI service error, update status
      if (error.message.includes('AI') || error.message.includes('model')) {
        updateAIStatus('error', error.message);
      }
    } finally {
      // Reset button state
      submitButton.disabled = false;
      submitAnswerText.textContent = 'Submit Answer';
      spinner.classList.add('hidden');
    }
  }

  function displayAssessment(assessment) {
    const modal = document.getElementById('assessmentModal');
    const resultsDiv = document.getElementById('assessmentResults');
    
    // Clear previous results
    resultsDiv.innerHTML = '';
    
    // Create and append score element
    const scoreDiv = document.createElement('div');
    scoreDiv.className = 'mb-4';
    scoreDiv.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="text-lg font-semibold">Score:</span>
        <span class="text-2xl font-bold ${assessment.score >= 70 ? 'text-green-500' : 'text-yellow-500'}">${assessment.score}/100</span>
      </div>
    `;
    resultsDiv.appendChild(scoreDiv);
    
    // Create and append strengths section
    if (assessment.strengths && assessment.strengths.length > 0) {
      const strengthsDiv = document.createElement('div');
      strengthsDiv.className = 'mb-4';
      strengthsDiv.innerHTML = `
        <h4 class="text-lg font-semibold text-green-500 mb-2">Strengths:</h4>
        <ul class="list-disc list-inside space-y-1">
          ${assessment.strengths.map(strength => `<li>${strength}</li>`).join('')}
        </ul>
      `;
      resultsDiv.appendChild(strengthsDiv);
    }
    
    // Create and append improvements section
    if (assessment.improvements && assessment.improvements.length > 0) {
      const improvementsDiv = document.createElement('div');
      improvementsDiv.className = 'mb-4';
      improvementsDiv.innerHTML = `
        <h4 class="text-lg font-semibold text-yellow-500 mb-2">Areas for Improvement:</h4>
        <ul class="list-disc list-inside space-y-1">
          ${assessment.improvements.map(improvement => `<li>${improvement}</li>`).join('')}
        </ul>
      `;
      resultsDiv.appendChild(improvementsDiv);
    }
    
    // Create and append feedback section
    if (assessment.feedback) {
      const feedbackDiv = document.createElement('div');
      feedbackDiv.className = 'mt-4 p-4 bg-gray-800 rounded-lg';
      feedbackDiv.innerHTML = `
        <h4 class="text-lg font-semibold text-blue-400 mb-2">Detailed Feedback:</h4>
        <p class="text-gray-300">${assessment.feedback}</p>
      `;
      resultsDiv.appendChild(feedbackDiv);
    }
    
    // Show the modal
    modal.classList.remove('hidden');
    
    // Update the chart if it exists
    updateChart(assessment.score);
  }

  // Function to update the chart with new score
  function updateChart(newScore) {
    const chart = Chart.getChart("scoreChart");
    if (chart) {
      if (!chart.data.datasets[0].data) {
        chart.data.datasets[0].data = [];
      }
      chart.data.datasets[0].data.push(newScore);
      if (!chart.data.labels) {
        chart.data.labels = [];
      }
      chart.data.labels.push(`Q${chart.data.labels.length + 1}`);
      chart.update();
    }
  }

  // Load roles from questions.json
  async function loadRoles() {
    try {
      const response = await fetch('/assets/questions.json');
      const data = await response.json();
      
      const roleSelect = document.getElementById('roleSelect');
      roleSelect.innerHTML = '<option value="">Choose a role...</option>'; // Add default option
      
      data.job_roles.forEach((role) => {
        const option = document.createElement('option');
        option.value = role.role; // Use role.role instead of role.role_name
        option.textContent = role.role;
        roleSelect.appendChild(option);
      });

      // Don't set initial question here - wait for user to select a role
      questionArea.classList.add('hidden');
    } catch (error) {
      console.error('Error loading roles:', error);
      const roleSelect = document.getElementById('roleSelect');
      roleSelect.innerHTML = '<option value="">Error loading roles</option>';
    }
  }

  function loadNewQuestion() {
    const role = document.getElementById("roleSelect").value;
    if (!role) {
      questionArea.classList.add("hidden");
      return;
    }

    // Show loading state
    questionArea.classList.add("opacity-50");
    currentQuestionElement.textContent = "Loading question...";
    
    // Fetch questions from the JSON file
    fetch("/assets/questions.json")
      .then((response) => response.json())
      .then((data) => {
        // Find the selected role
        const roleData = data.job_roles.find(r => r.role === role);
        
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
          questionArea.classList.add("hidden");
          currentQuestionElement.textContent = "No questions available for this role.";
        }
      })
      .catch((error) => {
        console.error("Error loading questions:", error);
        questionArea.classList.add("hidden");
        currentQuestionElement.textContent = "Error loading questions. Please try again.";
      })
      .finally(() => {
        questionArea.classList.remove("opacity-50");
      });
  }

  // Initialize everything
  checkAIStatus();
  setInterval(checkAIStatus, 30000);
  loadRoles();

  // Event Listeners
  document.getElementById('roleSelect').addEventListener('change', function() {
    previousQuestions = [];
    loadNewQuestion();
  });

  document.getElementById('submitAnswer').addEventListener('click', submitAnswer);
  
  document.getElementById('nextQuestion').addEventListener('click', function() {
    const nextButton = document.getElementById('nextQuestion');
    nextButton.disabled = true;
    nextButton.classList.add('opacity-50');
    loadNewQuestion();
    setTimeout(() => {
      nextButton.disabled = false;
      nextButton.classList.remove('opacity-50');
    }, 1000);
  });

  document.getElementById('closeModal').addEventListener('click', () => {
    assessmentModal.classList.add('hidden');
  });

  document.getElementById('assessmentModal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
      e.target.classList.add('hidden');
    }
  });

  // Load initial analytics
  loadAnalytics();

  // Add retry utility function at the top level
  async function retryFetch(url, options, maxRetries = 2) {
    for (let i = 0; i < maxRetries; i++) {
      try {
        const response = await fetch(url, options);
        const data = await response.json();
        return { response, data };
      } catch (error) {
        if (i === maxRetries - 1) throw error;
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2s between retries
      }
    }
  }

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
    document.getElementById("reinitializeAi").addEventListener("click", reinitializeAI);
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
});
