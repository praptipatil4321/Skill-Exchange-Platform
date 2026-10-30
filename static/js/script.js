// Theme (light/dark) with persistence, mobile nav, auto-dismiss flashes
(function () {
  const saved = localStorage.getItem("theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = saved || (prefersDark ? "dark" : "light");
})();
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("theme-toggle");
  const paint = () => { if (btn) btn.textContent = document.documentElement.dataset.theme === "dark" ? "☀️" : "🌙"; };
  paint();
  if (btn) btn.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("theme", next);
    paint();
  });
  const nav = document.getElementById("nav-toggle"), links = document.getElementById("nav-links");
  if (nav) nav.addEventListener("click", () => links.classList.toggle("open"));
  document.querySelectorAll(".flash").forEach((f) => setTimeout(() => {
    f.style.transition = "opacity .5s"; f.style.opacity = "0"; setTimeout(() => f.remove(), 500);
  }, 4000));
});
