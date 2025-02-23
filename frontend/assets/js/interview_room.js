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
