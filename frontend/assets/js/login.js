document.addEventListener('DOMContentLoaded', () => {
  let isLoginMode = true;
  const emailForm = document.getElementById("emailForm");
  const authForm = document.getElementById("authForm");
  const pageTitle = document.getElementById("pageTitle");
  const submitButton = document.getElementById("submitButton");
  const confirmPasswordSection = document.getElementById("confirmPasswordSection");
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const confirmPasswordInput = document.getElementById('confirmPassword');
  const togglePasswordBtn = document.getElementById('togglePassword');

  // Password visibility toggle
  togglePasswordBtn.addEventListener('click', () => {
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;
  });

  emailForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = emailInput.value.trim();

    // Check if the email exists
    const response = await fetch('/check-email', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email })
    });

    const result = await response.json();

    if (result.exists) {
      // User exists, proceed to login
      isLoginMode = true;
      pageTitle.textContent = "Login";
      submitButton.textContent = "Login";
      confirmPasswordSection.classList.add("hidden");
    } else {
      // New user, proceed to signup
      isLoginMode = false;
      pageTitle.textContent = "Sign Up";
      submitButton.textContent = "Create Account";
      confirmPasswordSection.classList.remove("hidden");
    }

    // Show the password form
    emailForm.classList.add("hidden");
    authForm.classList.remove("hidden");
  });

  authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const password = passwordInput.value.trim();
    const confirmPassword = confirmPasswordInput.value.trim();

    if (!isLoginMode) {
      // Debugging: Log passwords to console
      console.log("Password:", password);
      console.log("Confirm Password:", confirmPassword);

      if (password !== confirmPassword) {
        alert("Passwords do not match");
        return;
      }
    }

    // Prepare authentication data
    const authData = {
      email: emailInput.value.trim(),
      password: password,
      mode: isLoginMode ? 'login' : 'signup'
    };

    // Send authentication request to Flask backend
    const response = await fetch('/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(authData)
    });

    const result = await response.json();

    if (result.success) {
      // Successful authentication
      alert(result.message);
      
      // Redirect to the specified URL
      if (result.redirect) {
        window.location.href = result.redirect;
      }
    } else {
      // Authentication failed
      alert(result.message || 'Authentication failed');
    }
  });
});