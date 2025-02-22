// Wait for the DOM to be fully loaded
document.addEventListener("DOMContentLoaded", () => {
  // Initialize GSAP ScrollTrigger
  gsap.registerPlugin(ScrollTrigger);

  // Hero Section Animations - Add null checks
  const heroTitle = document.getElementById("heroTitle");
  const heroSubtitle = document.getElementById("heroSubtitle");
  const heroCTA = document.getElementById("heroCTA");

  if (heroTitle) {
    gsap.from(heroTitle, {
      duration: 1,
      y: 30,
      opacity: 0,
      ease: "power3.out",
    });
  }

  if (heroSubtitle) {
    gsap.from(heroSubtitle, {
      duration: 1,
      y: 30,
      opacity: 0,
      ease: "power3.out",
      delay: 0.2,
    });
  }

  if (heroCTA) {
    gsap.from(heroCTA, {
      duration: 1,
      y: 30,
      opacity: 0,
      ease: "power3.out",
      delay: 0.4,
    });
  }

  // Stats Counter Animation
  const stats = ["stat1", "stat2", "stat3"];
  stats.forEach((stat) => {
    const statElement = document.getElementById(stat);
    if (statElement) {
      ScrollTrigger.create({
        trigger: `#${stat}`,
        onEnter: () => animateValue(stat),
        once: true,
      });
    }
  });

  function animateValue(elementId) {
    const obj = document.getElementById(elementId);
    if (obj) {
      const value = parseInt(obj.innerText);
      let current = 0;
      const duration = 2000;
      const step = value / (duration / 16);

      const timer = setInterval(() => {
        current += step;
        if (current >= value) {
          clearInterval(timer);
          current = value;
        }
        obj.textContent =
          Math.round(current) + (elementId === "stat3" ? "%" : "K+");
      }, 16);
    }
  }

  // Scroll Progress Bar
  const scrollProgress = document.getElementById("scrollProgress");
  if (scrollProgress) {
    window.addEventListener("scroll", () => {
      const winScroll =
        document.body.scrollTop || document.documentElement.scrollTop;
      const height =
        document.documentElement.scrollHeight -
        document.documentElement.clientHeight;
      const scrolled = (winScroll / height) * 100;
      scrollProgress.style.width = scrolled + "%";
    });
  }

  // Dark Mode Toggle
  const darkModeToggle = document.getElementById("darkModeToggle");
  if (darkModeToggle) {
    darkModeToggle.addEventListener("click", () => {
      document.documentElement.classList.toggle("dark");
    });
  }

  // Intersection Observer for fade-in animations
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          // Add opacity to all child elements
          const childElements = entry.target.querySelectorAll(
            ".text-center.mb-16, .text-center.mb-16 *"
          );

          childElements.forEach((child) => {
            child.classList.add("opacity-100");
            child.classList.remove("opacity-0");
          });

          entry.target.classList.add("opacity-100");
          entry.target.classList.remove("opacity-0");

          // Optional: Unobserve after first intersection
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.01, // Trigger even with minimal visibility
      rootMargin: "0px 0px -50px 0px", // Adjust trigger point
    }
  );

  // Observe all sections with fade-in effect
  const fadeElements = document.querySelectorAll("section, .fade-in");
  fadeElements.forEach((element) => {
    // Ensure initial visibility
    element.style.opacity = "1";
    element.classList.remove("opacity-0");

    // Ensure child elements are visible
    const childElements = element.querySelectorAll(
      ".text-center.mb-16, .text-center.mb-16 *"
    );
    childElements.forEach((child) => {
      child.style.opacity = "1";
      child.classList.remove("opacity-0");
    });

    // Add observer
    observer.observe(element);
  });

  // Force first section to be visible
  const firstSection = document.querySelector("section");
  if (firstSection) {
    firstSection.style.opacity = "1";
    firstSection.classList.remove("opacity-0");

    // Ensure child elements are visible
    const childElements = firstSection.querySelectorAll(
      ".text-center.mb-16, .text-center.mb-16 *"
    );
    childElements.forEach((child) => {
      child.style.opacity = "1";
      child.classList.remove("opacity-0");
    });
  }
});
