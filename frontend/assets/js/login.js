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
  const logoElement = document.querySelector('.logo-pulse');

  // Add any additional initialization logic from the HTML script here
  togglePasswordBtn.addEventListener('click', () => {
    passwordInput.type = passwordInput.type === 'password' ? 'text' : 'password';
  });

  // Add a promise-based delay function
  const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  // Loading screen
  const createLoadingOverlay = () => {
    const overlay = document.createElement('div');
    overlay.className = `
      fixed 
      inset-0 
      bg-white 
      dark:bg-gray-900 
      z-50 
      flex 
      items-center 
      justify-center 
      opacity-0 
      transition-opacity 
      duration-500
    `;
    
    const logoContainer = document.createElement('div');
    logoContainer.className = 'text-center';
    
    const logo = document.createElement('img');
    logo.src = 'assets/logo.png'; // Ensure this path is correct
    logo.alt = 'JobSaarathi';
    logo.className = 'w-64 h-auto logo-pulse animate-pulse';
    
    logoContainer.appendChild(logo);
    overlay.appendChild(logoContainer);
    
    document.body.appendChild(overlay);
    
    // Trigger reflow
    overlay.offsetHeight;
    overlay.style.opacity = '1';
    
    return overlay;
  };

  authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const password = passwordInput.value.trim();
    const confirmPassword = confirmPasswordInput.value.trim();

    // Disable submit button during processing
    submitButton.disabled = true;
    submitButton.classList.add('opacity-50', 'cursor-not-allowed');

    // Create loading overlay
    const loadingOverlay = createLoadingOverlay();

    if (!isLoginMode) {
      if (password !== confirmPassword) {
        loadingOverlay.remove();
        submitButton.disabled = false;
        submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
        return;
      }
    }

    try {
      // Send authentication request to Flask backend
      const response = await fetch('/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: emailInput.value.trim(),
          password: password,
          mode: isLoginMode ? 'login' : 'signup'
        })
      });

      const result = await response.json();

      if (result.success) {
        // Extend loading time
        await delay(3000);
        
        // Redirect to the specified URL
        if (result.redirect) {
          window.location.href = result.redirect;
        }
      } else {
        // Authentication failed
        loadingOverlay.style.opacity = '0';
        setTimeout(() => loadingOverlay.remove(), 500);
        submitButton.disabled = false;
        submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
      }
    } catch (error) {
      loadingOverlay.style.opacity = '0';
      setTimeout(() => loadingOverlay.remove(), 500);
      submitButton.disabled = false;
      submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
    }
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
      pageTitle.textContent = "";
      submitButton.textContent = "Login";
      confirmPasswordSection.classList.add("hidden");
    } else {
      // New user, proceed to signup
      isLoginMode = false;
      pageTitle.textContent = "";
      submitButton.textContent = "Create Account";
      confirmPasswordSection.classList.remove("hidden");
    }

    // Show the password form
    emailForm.classList.add("hidden");
    authForm.classList.remove("hidden");
  });

  // Logo pulse animation
  const pulseLogo = async () => {
    if (logoElement) {
      logoElement.classList.add('animate-pulse');
      await delay(2000);
      logoElement.classList.remove('animate-pulse');
    }
  };
});