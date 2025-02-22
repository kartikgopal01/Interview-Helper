document.addEventListener("DOMContentLoaded", () => {
  const navbarHTML = `
    <nav class="fixed w-full z-50 glassmorphism">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-20">
        <div class="flex items-center space-x-8">
          <a href="/" class="flex items-center space-x-2">
            <img src="../assets/logo.png" alt="Logo" class="h-10" />
          </a>
        </div>
        <div class="hidden md:flex space-x-6">
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
      </div>
    </nav>
  `;

  document.body.insertAdjacentHTML("afterbegin", navbarHTML);
});
