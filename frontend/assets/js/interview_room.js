document.addEventListener("DOMContentLoaded", () => {
  // Get interview details from the page
  const interviewId = document.getElementById("interview-id").value;
  const userName = document.getElementById("user-name").value;
  const userId = document.getElementById("user-id").value;
  const isInterviewer =
    document.getElementById("is-interviewer").value === "True";

  // Dynamic socket connection
  const socket = io({
    query: {
      interview_id: interviewId,
      user_id: userId,
      user_name: userName,
      is_interviewer: isInterviewer,
    },
  });

  // Join room function
  function join_room(room) {
    console.log(`Attempting to join room: ${room}`);
    socket.emit("join_room", {
      room: room,
      user_id: userId,
      user_name: userName,
      is_interviewer: isInterviewer,
    });
  }

  // Call join_room when the page loads
  join_room(interviewId);

  // Socket event listeners
  socket.on("connect", () => {
    console.log("Connected to WebSocket server");
    // Confirm room join
    socket.emit("join_room", {
      room: interviewId,
      user_id: userId,
      user_name: userName,
      is_interviewer: isInterviewer,
    });
  });

  socket.on("room_joined", (data) => {
    console.log("Successfully joined room:", data);
    // Update UI to show user has joined
    const statusElement = document.getElementById("room-status");
    if (statusElement) {
      statusElement.textContent = `${userName} has joined the interview room`;
      statusElement.classList.remove("hidden");
    }
  });

  socket.on("user_joined", (data) => {
    console.log("Another user joined:", data);
    // Notify when another user joins
    const notificationElement = document.getElementById("notifications");
    if (notificationElement) {
      const notification = document.createElement("div");
      notification.textContent = `${data.user_name} has joined the interview room`;
      notification.classList.add("text-green-500", "mb-2");
      notificationElement.appendChild(notification);
    }
  });

  // Message sending functionality
  const messageInput = document.getElementById("message-input");
  const sendMessageBtn = document.getElementById("send-message-btn");
  const messagesContainer = document.getElementById("messages-container");

  sendMessageBtn.addEventListener("click", sendMessage);
  messageInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      sendMessage();
    }
  });

  function sendMessage() {
    const message = messageInput.value.trim();
    if (message) {
      socket.emit("send_message", {
        room: interviewId,
        message: message,
        user_id: userId,
        user_name: userName,
      });
      messageInput.value = "";
    }
  }

  // Receive messages
  socket.on("receive_message", (data) => {
    const messageElement = document.createElement("div");
    messageElement.classList.add("mb-2", "p-2", "rounded");

    if (data.user_id === userId) {
      // Own message
      messageElement.classList.add("bg-blue-100", "text-right");
      messageElement.innerHTML = `
        <span class="font-bold">${data.user_name} (You):</span>
        <p>${data.message}</p>
      `;
    } else {
      // Other user's message
      messageElement.classList.add("bg-gray-100");
      messageElement.innerHTML = `
        <span class="font-bold">${data.user_name}:</span>
        <p>${data.message}</p>
      `;
    }

    messagesContainer.appendChild(messageElement);
    // Auto-scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  });

  // Handle disconnection
  socket.on("disconnect", () => {
    console.log("Disconnected from WebSocket server");
    const statusElement = document.getElementById("room-status");
    if (statusElement) {
      statusElement.textContent = "Connection lost. Reconnecting...";
      statusElement.classList.add("text-red-500");
    }
  });

  // Reconnection handling
  socket.on("reconnect", () => {
    console.log("Reconnected to WebSocket server");
    join_room(interviewId);
  });
});
