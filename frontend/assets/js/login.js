document.addEventListener('DOMContentLoaded', () => {
  // Dark Mode Toggle
  const darkModeToggle = document.getElementById('darkModeToggle');
  if (darkModeToggle) {
    darkModeToggle.addEventListener('click', () => {
      document.documentElement.classList.toggle('dark');
    });
  }

  const authForm = document.getElementById('authForm');
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const confirmPasswordInput = document.getElementById('confirmPassword');
  const togglePasswordBtn = document.getElementById('togglePassword');
  const confirmPasswordSection = document.getElementById('confirmPasswordSection');

  let isLoginMode = true;

  // Password visibility toggle
  togglePasswordBtn.addEventListener('click', () => {
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;
  });

  // Password validation function
  function validatePassword(password) {
    // At least 8 characters long
    if (password.length < 8) {
      return 'Password must be at least 8 characters long';
    }

    // At least one uppercase letter
    if (!/[A-Z]/.test(password)) {
      return 'Password must contain at least one uppercase letter';
    }

    // At least one lowercase letter
    if (!/[a-z]/.test(password)) {
      return 'Password must contain at least one lowercase letter';
    }

    // At least one number
    if (!/[0-9]/.test(password)) {
      return 'Password must contain at least one number';
    }

    // At least one special character
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
      return 'Password must contain at least one special character';
    }

    return null;
  }

  // Authentication form submission
  authForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      alert('Please enter a valid email address');
      return;
    }

    // Password validation
    const passwordError = validatePassword(password);
    if (passwordError) {
      alert(passwordError);
      return;
    }

    // If in signup mode, validate confirm password
    if (!isLoginMode) {
      const confirmPassword = confirmPasswordInput.value;
      
      if (password !== confirmPassword) {
        alert('Passwords do not match');
        return;
      }
    }

    try {
      // Prepare authentication data
      const authData = {
        email: email,
        password: password,
        mode: isLoginMode ? 'login' : 'signup'
      };

      // Send authentication request to Flask backend
      const response = await fetch('/auth', {
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
    } catch (error) {
      console.error('Authentication error:', error);
      alert('An error occurred. Please try again.');
    }
  });

  // Toggle between login and signup modes
  const switchAuthLink = document.getElementById('switchAuth');
  switchAuthLink.addEventListener('click', (e) => {
    e.preventDefault();
    isLoginMode = !isLoginMode;

    if (isLoginMode) {
      confirmPasswordSection.classList.add('hidden');
    } else {
      confirmPasswordSection.classList.remove('hidden');
    }
  });
}); 