const header = document.querySelector("[data-header]");
const nav = document.querySelector("#site-nav");
const navToggle = document.querySelector(".nav-toggle");

function setMenu(open) {
  nav?.classList.toggle("is-open", open);
  header?.classList.toggle("is-open", open);
  navToggle?.setAttribute("aria-expanded", String(open));
}

function updateHeader() {
  header?.classList.toggle("is-scrolled", window.scrollY > 12);
}

updateHeader();
window.addEventListener("scroll", updateHeader, { passive: true });

navToggle?.addEventListener("click", () => {
  setMenu(navToggle.getAttribute("aria-expanded") !== "true");
});

nav?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => setMenu(false));
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    setMenu(false);
    navToggle?.focus();
  }
});

window.matchMedia("(min-width: 681px)").addEventListener("change", (event) => {
  if (event.matches) {
    setMenu(false);
  }
});

document.querySelectorAll("[data-copy-target]").forEach((button) => {
  const originalLabel = button.textContent.trim();

  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copyTarget);
    if (!target) return;

    const text = target.textContent.replace(/^\$\s*/, "").trim();

    try {
      await navigator.clipboard.writeText(text);
      button.textContent = "Copied";
    } catch {
      button.textContent = "Select to copy";
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(target);
      selection.removeAllRanges();
      selection.addRange(range);
    }

    window.setTimeout(() => {
      button.textContent = originalLabel;
    }, 1800);
  });
});
