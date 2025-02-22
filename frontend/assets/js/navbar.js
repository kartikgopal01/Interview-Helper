document.addEventListener("DOMContentLoaded", () => {
  const navbarHTML = `
    <nav class="fixed right-0 left-0 z-50 m-5 glassmorphism">
    <div class="scroll-progress" id="scrollProgress"></div>
      <div class="max-w-[90%] mx-auto grid grid-cols-3 items-center justify-center h-20">
        <div class="flex items-center space-x-8">
          <a href="/" class="flex items-center justify-start space-x-2">
            <img src="../assets/logo.png" alt="Logo" class="h-10" />
          </a>
        </div>
        <div class="flex items-center justify-center md:flex space-x-6">
          <a href="/dashboard" class="nav-link text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 relative">
            Dashboard
            <span class="absolute bottom-0 left-0 w-full h-0.5 bg-blue-600 transform scale-x-0 transition-transform origin-left hover:scale-x-100"></span>
          </a>
          <a href="/practice" class="nav-link text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 relative">
            Practice
            <span class="absolute bottom-0 left-0 w-full h-0.5 bg-blue-600 transform scale-x-0 transition-transform origin-left hover:scale-x-100"></span>
          </a>
          <a href="/resources" class="nav-link text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 relative">
            Resources
            <span class="absolute bottom-0 left-0 w-full h-0.5 bg-blue-600 transform scale-x-0 transition-transform origin-left hover:scale-x-100"></span>
          </a>
        </div>
        <button id="theme-toggle" class="p-2 flex items-center justify-end rounded-full">
          <svg id="sun-icon" class="w-6 h-6 text-gray-700 hidden" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="5"></circle>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"></path>
          </svg>
          <svg id="moon-icon" class="w-6 h-6 text-gray-300 hidden" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M21 12.79A9 9 0 0111.21 3 7.5 7.5 0 1012 21a9 9 0 009-8.21z"></path>
          </svg>
        </button>
      </div>
    </nav>
  `;

  // Insert Navbar into Body
  document.body.insertAdjacentHTML("afterbegin", navbarHTML);

  setTimeout(() => {
    const themeToggleBtn = document.getElementById("theme-toggle");
    const htmlElement = document.documentElement;
    const sunIcon = document.getElementById("sun-icon");
    const moonIcon = document.getElementById("moon-icon");

    function applyTheme(theme) {
      if (theme === "dark") {
        htmlElement.classList.add("dark");
        sunIcon.classList.add("hidden");
        moonIcon.classList.remove("hidden");
      } else {
        htmlElement.classList.remove("dark");
        sunIcon.classList.remove("hidden");
        moonIcon.classList.add("hidden");
      }
    }

    // Force override system preference & apply stored theme
    const savedTheme = localStorage.getItem("theme") || "light";
    applyTheme(savedTheme);

    // Toggle theme on button click
    themeToggleBtn.addEventListener("click", () => {
      const newTheme = htmlElement.classList.contains("dark")
        ? "light"
        : "dark";
      localStorage.setItem("theme", newTheme);
      applyTheme(newTheme);
    });
  }, 10);
});
