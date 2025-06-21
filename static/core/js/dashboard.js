// core/static/core/js/dashboard.js

// Initialize particles.js
particlesJS("particles-js", {
  particles: {
    number: { value: 20, density: { enable: true, value_area: 1000 } },
    color: { value: "#004c99" },
    shape: { type: "circle" },
    opacity: { value: 0.4 },
    size: { value: 2.5, random: true },
    line_linked: {
      enable: true,
      distance: 130,
      color: "#004c99",
      opacity: 0.25,
      width: 1
    },
    move: { enable: true, speed: 0.6 }
  },
  interactivity: {
    detect_on: "canvas",
    events: {
      onhover: { enable: true, mode: "grab" },
      onclick: { enable: true, mode: "push" }
    },
    modes: {
      grab: { distance: 150, line_linked: { opacity: 0.4 } },
      push: { particles_nb: 2 }
    }
  },
  retina_detect: true
});

// Toggle mobile nav (optional)
document.getElementById('hamburger').addEventListener('click', () => {
  document.getElementById('navbarUser').classList.toggle('open');
});
