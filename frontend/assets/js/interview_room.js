document.addEventListener("DOMContentLoaded", () => {
  // Get connection details from data attributes
  const roomId = document.body.dataset.roomId;
  const userName = document.body.dataset.userName;
  const userId = document.body.dataset.userId;
  const isInterviewer = document.body.dataset.isInterviewer === 'true';

  // Initialize socket connection
  if (window.socketHandler) {
    window.socketHandler.initialize({
      roomId,
      userName,
      userId,
      isInterviewer
    });
  }

  // Wait for socket to be initialized
  const waitForSocket = () => {
    const socket = window.socketHandler?.getSocket();
    if (!socket) {
      setTimeout(waitForSocket, 100);
      return;
    }

    // Socket is available, set up event handlers
    setupEventHandlers(socket);
    
    // Add question button for interviewer
    if (isInterviewer) {
      setupQuestionButtons(socket);
    }
  };

  // Start waiting for socket
  waitForSocket();
});

function setupEventHandlers(socket) {
  // Message form handling
  const messageForm = document.getElementById("messageForm");
  const messageInput = document.getElementById("messageInput");
  const messagesDiv = document.getElementById("chat-messages");

  messageForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (message) {
      socket.emit("send_message", {
        room: document.body.dataset.roomId,
        message: message,
        user_id: document.body.dataset.userId,
        user_name: document.body.dataset.userName
      });
      messageInput.value = "";
    }
  });

  // AI form handling
  const aiForm = document.getElementById("aiForm");
  const aiPrompt = document.getElementById("aiPrompt");

  aiForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const prompt = aiPrompt.value.trim();
    if (prompt) {
      socket.emit("request_ai_help", {
        roomId: document.body.dataset.roomId,
        prompt: prompt
      });
      aiPrompt.value = "";
    }
  });

  // Socket event listeners
  socket.on("receive_message", (data) => {
    addMessage(data.user_name, data.message);
  });

  socket.on("ai_response", (data) => {
    addMessage("AI Assistant", data.message, true);
  });
  
  // Add listener for AI questions
  socket.on("ai_question", (data) => {
    addQuestion(data.question);
  });
  
  // Add listener for voice analysis
  socket.on("voice_analysis", (data) => {
    if (data.questions && data.questions.length > 0) {
      showSuggestedQuestions(data.questions);
    }
  });

  // Message display helper
  function addMessage(userName, message, isAI = false) {
    const div = document.createElement("div");
    div.classList.add("mb-2");
    if (isAI) div.classList.add("text-green-600");
    div.innerHTML = `<strong>${userName}:</strong> ${message}`;
    messagesDiv?.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }
}

// Function to set up question buttons
function setupQuestionButtons(socket) {
  // Find or create the question button container
  let questionButtonContainer = document.getElementById("question-button-container");
  if (!questionButtonContainer) {
    questionButtonContainer = document.createElement("div");
    questionButtonContainer.id = "question-button-container";
    questionButtonContainer.className = "flex items-center mb-4";
    
    const chatInput = document.getElementById("chat-input");
    if (chatInput) {
      chatInput.parentNode.insertBefore(questionButtonContainer, chatInput);
    }
  }
  
  // Create get question button if it doesn't exist
  let getQuestionButton = document.getElementById("getNextQuestion");
  if (!getQuestionButton) {
    getQuestionButton = document.createElement("button");
    getQuestionButton.id = "getNextQuestion";
    getQuestionButton.className = "bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg flex items-center transition-colors duration-200";
    getQuestionButton.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      Get Interview Question
    `;
  }
  
  // Add event listener to the button
  getQuestionButton.addEventListener("click", () => {
    // Get the current conversation context
    const messagesDiv = document.getElementById("chat-messages");
    const messages = messagesDiv?.innerText || "";
    const context = messages.slice(-500); // Use last 500 chars as context
    
    // Get the selected role
    const roleSelect = document.getElementById("roleSelect");
    const role = roleSelect?.value || "Software Engineer"; // Default to first role in questions.json
    
    // Request a question from the server
    socket.emit("get_next_question", {
      roomId: document.body.dataset.roomId,
      currentContext: context,
      role: role
    });
    
    // Show loading state
    getQuestionButton.disabled = true;
    getQuestionButton.innerHTML = `
      <svg class="animate-spin h-5 w-5 mr-1 inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      Loading...
    `;
    
    // Reset button after 3 seconds
    setTimeout(() => {
      getQuestionButton.disabled = false;
      getQuestionButton.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Get Interview Question
      `;
    }, 3000);
  });
  
  // Add the button to the container
  questionButtonContainer.appendChild(getQuestionButton);
  
  // Create role select if it doesn't exist
  if (!document.getElementById("roleSelect")) {
    const roleSelect = document.createElement("select");
    roleSelect.id = "roleSelect";
    roleSelect.className = "ml-2 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500";
    
    // Add default option
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "Select a role";
    roleSelect.appendChild(defaultOption);
    
    // Load roles from questions.json
    fetch("../assets/questions.json")
      .then(response => response.json())
      .then(data => {
        data.job_roles.forEach(jobRole => {
          const option = document.createElement("option");
          option.value = jobRole.role;
          option.textContent = jobRole.role;
          roleSelect.appendChild(option);
        });
        
        // Set default to first role
        if (data.job_roles.length > 0) {
          roleSelect.value = data.job_roles[0].role;
        }
      })
      .catch(error => {
        console.error("Error loading roles:", error);
        roleSelect.innerHTML = '<option value="">Error loading roles</option>';
      });
    
    // Add the select to the container
    questionButtonContainer.appendChild(roleSelect);
  }
}

// Function to add a question to the chat
function addQuestion(question) {
  const messagesDiv = document.getElementById("chat-messages");
  if (messagesDiv) {
    const div = document.createElement("div");
    div.classList.add("mb-4", "p-3", "bg-purple-100", "dark:bg-purple-900", "rounded-lg", "border-l-4", "border-purple-500");
    div.innerHTML = `
      <div class="flex items-center mb-1">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-purple-600 dark:text-purple-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <strong class="text-purple-700 dark:text-purple-300">Interview Question:</strong>
      </div>
      <div class="ml-7">${question}</div>
    `;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    // Also add to the message input as a draft
    const messageInput = document.getElementById("messageInput");
    if (messageInput && document.body.dataset.isInterviewer === 'true') {
      messageInput.value = question;
    }
  }
}

// Function to show suggested questions
function showSuggestedQuestions(questions) {
  // Find or create the suggested questions container
  let suggestedQuestionsContainer = document.getElementById("suggested-questions-container");
  
  if (!suggestedQuestionsContainer) {
    const chatContainer = document.querySelector(".chat-container");
    if (chatContainer) {
      suggestedQuestionsContainer = document.createElement("div");
      suggestedQuestionsContainer.id = "suggested-questions-container";
      suggestedQuestionsContainer.className = "mt-4 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg";
      
      const heading = document.createElement("h3");
      heading.className = "text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300";
      heading.textContent = "Suggested Questions";
      suggestedQuestionsContainer.appendChild(heading);
      
      const questionsList = document.createElement("div");
      questionsList.id = "suggested-questions-list";
      questionsList.className = "space-y-2";
      suggestedQuestionsContainer.appendChild(questionsList);
      
      chatContainer.appendChild(suggestedQuestionsContainer);
    }
  }
  
  // Update the questions list
  const questionsList = document.getElementById("suggested-questions-list");
  if (questionsList) {
    questionsList.innerHTML = ""; // Clear existing questions
    
    questions.forEach(questionData => {
      const question = typeof questionData === 'string' ? questionData : questionData.question;
      
      const questionItem = document.createElement("div");
      questionItem.className = "p-2 bg-white dark:bg-gray-700 rounded border-l-4 border-blue-500 cursor-pointer hover:bg-blue-50 dark:hover:bg-gray-600 transition";
      questionItem.textContent = question;
      
      // Add click event to use this question
      questionItem.addEventListener("click", () => {
        addQuestion(question);
      });
      
      questionsList.appendChild(questionItem);
    });
  }
}
