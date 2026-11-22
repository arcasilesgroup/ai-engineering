/* scroll-spy: mark the nav link for the section in view.
   Lead matches scroll-margin-top (88px): the highlight flips when the
   heading clears the sticky nav. */
(function () {
  const lead = 88;
  const links = document.querySelectorAll('nav a[href^="#"]');
  function updateNav() {
    let current = "";
    for (const link of links) {
      const href = link.getAttribute("href");
      if (!href) continue;
      const section = document.getElementById(href.slice(1));
      if (!section) continue;
      if (section.getBoundingClientRect().top <= lead) current = href.slice(1);
    }
    for (const link of links) {
      const on = link.getAttribute("href") === "#" + current;
      link.classList.toggle("active", on);
      if (on) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
  }
  window.addEventListener("scroll", updateNav, { passive: true });
  updateNav();
})();
