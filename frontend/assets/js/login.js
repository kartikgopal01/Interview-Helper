document.addEventListener("DOMContentLoaded", () => {
  let isLoginMode = true;
  const emailForm = document.getElementById("emailForm");
  const authForm = document.getElementById("authForm");
  const pageTitle = document.getElementById("pageTitle");
  const submitButton = document.getElementById("submitButton");
  const confirmPasswordSection = document.getElementById(
    "confirmPasswordSection"
  );
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const confirmPasswordInput = document.getElementById("confirmPassword");
  const togglePasswordBtn = document.getElementById("togglePassword");
  const logoElement = document.querySelector(".logo-pulse");

  // Add any additional initialization logic from the HTML script here
  togglePasswordBtn.addEventListener("click", () => {
    const type = passwordInput.type === "password" ? "text" : "password";
    passwordInput.type = type;

    // Also toggle confirm password if in signup mode
    if (!isLoginMode && confirmPasswordInput) {
      confirmPasswordInput.type = type;
    }
  });

  // Add a promise-based delay function
  const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  // Create an alert function
  function showAlert(message, type = "error") {
    // Remove any existing alerts
    const existingAlerts = document.querySelectorAll(".alert");
    existingAlerts.forEach((alert) => alert.remove());

    const alertDiv = document.createElement("div");

    // Use classList.add with individual classes
    alertDiv.classList.add(
      "alert",
      "fixed",
      "top-2",
      "left-1/2",
      "transform",
      "-translate-x-1/2",
      "px-4",
      "py-2",
      "rounded-lg",
      "z-[9999]"
    );

    // Conditionally add color classes
    if (type === "error") {
      alertDiv.classList.add("bg-red-500", "text-white");
    } else {
      alertDiv.classList.add("bg-green-500", "text-white");
    }

    alertDiv.textContent = message;

    // Insert the alert before the form
    const formContainer = document.querySelector(".glassmorphism");
    if (formContainer) {
      formContainer.insertAdjacentElement("beforebegin", alertDiv);
    } else {
      document.body.insertAdjacentElement("afterbegin", alertDiv);
    }

    // Remove alert after 3 seconds
    setTimeout(() => {
      alertDiv.remove();
    }, 3000);
  }

  // Create loading overlay
  function createLoadingOverlay() {
    const overlay = document.createElement("div");
    overlay.className = `
      fixed 
      inset-0 
      bg-white 
      dark:bg-gray-900 
      z-100 
      flex 
      items-center 
      justify-center 
      opacity-0 
      transition-opacity 
      duration-500
    `;

    const logoContainer = document.createElement("div");
    logoContainer.className = "text-center";

    const logo = document.createElement("img");
    logo.src = "../assets/logo.png"; // Ensure correct path
    logo.alt = "JobSaarathi";
    logo.className = "w-64 h-auto logo-pulse animate-pulse";

    logoContainer.appendChild(logo);
    overlay.appendChild(logoContainer);

    document.body.appendChild(overlay);

    // Trigger reflow
    overlay.offsetHeight;
    overlay.style.opacity = "1";

    return overlay;
  }

  // Email validation function
  function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  // Modify the email check route to handle signup scenario
  emailForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = emailInput.value.trim();

    // Comprehensive email validation
    if (!email) {
      showAlert("Email is required");
      return;
    }

    if (!validateEmail(email)) {
      showAlert("Please enter a valid email address");
      return;
    }

    try {
      // Check if the email exists
      const response = await fetch("/check-email", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      });

      const result = await response.json();
      console.log("Check Email Result:", result);

      if (result.exists) {
        // User exists, proceed to login
        isLoginMode = true;
        pageTitle.textContent = "Login";
        submitButton.textContent = "Login";
        confirmPasswordSection.classList.add("hidden");
      } else {
        // New user, proceed to signup
        isLoginMode = false;
        pageTitle.textContent = "Create Account";
        submitButton.textContent = "Create Account";
        confirmPasswordSection.classList.remove("hidden");
      }

      // Show the password form
      emailForm.classList.add("hidden");
      authForm.classList.remove("hidden");
    } catch (error) {
      console.error("Check Email Error:", error);
      showAlert("An error occurred while checking email");
    }
  });

  authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();
    const confirmPassword = confirmPasswordInput
      ? confirmPasswordInput.value.trim()
      : null;

    // Disable submit button during processing
    submitButton.disabled = true;
    submitButton.classList.add("opacity-50", "cursor-not-allowed");

    // Validate inputs
    if (!email) {
      showAlert("Email is required");
      submitButton.disabled = false;
      submitButton.classList.remove("opacity-50", "cursor-not-allowed");
      return;
    }

    if (!validateEmail(email)) {
      showAlert("Please enter a valid email address");
      submitButton.disabled = false;
      submitButton.classList.remove("opacity-50", "cursor-not-allowed");
      return;
    }

    if (!password) {
      showAlert("Password is required");
      submitButton.disabled = false;
      submitButton.classList.remove("opacity-50", "cursor-not-allowed");
      return;
    }

    // For signup mode, validate confirm password
    if (!isLoginMode) {
      if (!confirmPassword) {
        showAlert("Confirm password is required");
        submitButton.disabled = false;
        submitButton.classList.remove("opacity-50", "cursor-not-allowed");
        return;
      }

      if (password !== confirmPassword) {
        showAlert("Passwords do not match");
        submitButton.disabled = false;
        submitButton.classList.remove("opacity-50", "cursor-not-allowed");
        return;
      }

      // Additional password strength validation
      if (password.length < 8) {
        showAlert("Password must be at least 8 characters long");
        submitButton.disabled = false;
        submitButton.classList.remove("opacity-50", "cursor-not-allowed");
        return;
      }
    }

    // Modify payload based on login/signup mode
    const payload = {
      email: email,
      password: password,
      confirm_password: isLoginMode ? null : confirmPassword,
    };

    console.log("Payload:", payload);

    try {
      // Send authentication request to Flask backend
      const response = await fetch("/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      console.log("Server Response:", result);

      if (response.ok) {
        // Check response status
        if (result.success) {
          // Show success alert
          showAlert(result.message, "success");

          // Log redirect URL
          console.log("Redirect URL:", result.redirect);

          // Create loading overlay
          const loadingOverlay = createLoadingOverlay();

          // Redirect after a short delay
          setTimeout(() => {
            // Attempt multiple redirection methods
            if (result.redirect) {
              console.log("Attempting to redirect to:", result.redirect);
              window.location.href = result.redirect; // Use href instead of replace
            } else {
              console.log("Redirecting to default dashboard");
              window.location.href = "/dashboard";
            }
          }, 1500);
        } else {
          // Show error alert
          showAlert(result.message);

          // Re-enable submit button
          submitButton.disabled = false;
          submitButton.classList.remove("opacity-50", "cursor-not-allowed");
        }
      } else {
        // Handle error responses
        showAlert(result.message || "An error occurred");

        // Re-enable submit button
        submitButton.disabled = false;
        submitButton.classList.remove("opacity-50", "cursor-not-allowed");
      }
    } catch (error) {
      console.error("Fetch Error:", error);
      showAlert("An unexpected error occurred");

      // Re-enable submit button
      submitButton.disabled = false;
      submitButton.classList.remove("opacity-50", "cursor-not-allowed");
    }
  });

  // Logo pulse animation
  const pulseLogo = async () => {
    if (logoElement) {
      logoElement.classList.add("animate-pulse");
      await delay(2000);
      logoElement.classList.remove("animate-pulse");
    }
  };
});
